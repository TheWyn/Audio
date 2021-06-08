# Future Imports
from __future__ import annotations

# Standard Library Imports
from collections import OrderedDict
from typing import Final, Pattern
import asyncio
import contextlib
import logging
import re

# Dependency Imports
from aiohttp import ClientConnectorError
from discord.ext.commands import CheckFailure
from redbot.core import commands
from redbot.core.utils.chat_formatting import box, humanize_list
import discord

# My Modded Imports
import lavalink

# Audio Imports
# Music  Imports
from ...audio_logging import debug_exc_log
from ...errors import CommandRejected, TrackEnqueueError
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass, HUMANIZED_PERM

log = logging.getLogger("red.cogs.Music.cog.Events.dpy")

RE_CONVERSION: Final[Pattern] = re.compile('Converting to "(.*)" failed for parameter "(.*)".')


class DpyEvents(MixinMeta, metaclass=CompositeMetaClass):
    async def cog_before_invoke(self, ctx: commands.Context) -> None:
        await self.cog_ready_event.wait()
        # check for unsupported arch
        # Check on this needs refactoring at a later date
        # so that we have a better way to handle the tasks
        is_owner = await ctx.bot.is_owner(ctx.author)
        if self.command_audioset_lavalink in [ctx.command, ctx.command.root_parent]:
            pass
        elif self.lavalink_connect_task and self.lavalink_connect_task.cancelled():
            # This message does not need to be shown to non Owners,
            if is_owner:
                await ctx.send(
                    (
                        "You have attempted to run our Lavalink node on an unsupported"
                        " architecture. Only settings related commands will be available."
                    )
                )
            raise RuntimeError(
                "Not running Audio command due to invalid machine architecture for Lavalink."
            )
        not_deafened_commands = [  # TODO: Add the missing ones to the ABC
            self.command_play,
            self.command_prev,
            self.command_playlist,
            self.command_autoplay,
            self.command_bump,
            self.command_bumpplay,
            self.command_disconnect,
            self.command_effects,
            self.command_equalizer,
            self.command_genre,
            self.command_local,
            self.command_pause,
            self.command_playmix,
            self.command_search,
            self.command_seek,
            self.command_sing,
            self.command_skip,
            self.command_stop,
            self.command_summon,
            self.command_volume,
        ]
        if not is_owner and ctx.guild:
            dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)

            if not (
                ctx.author.id == ctx.guild.owner_id
                or (dj_enabled and await self._has_dj_role(ctx, ctx.author))
                or await self.bot.is_mod(ctx.author)
            ) and any(
                command in not_deafened_commands
                for command in [ctx.command, ctx.command.root_parent]
            ):
                voice: discord.VoiceState = ctx.author.voice
                if ctx.author.voice:
                    if voice.self_deaf or voice.deaf:
                        msg = "You are unable to run this command while deafened."
                        raise CommandRejected(message=msg, reason="deafened")

        current_perms = ctx.channel.permissions_for(ctx.me)
        surpass_ignore = (
            isinstance(ctx.channel, discord.abc.PrivateChannel)
            or await ctx.bot.is_owner(ctx.author)
            or await ctx.bot.is_admin(ctx.author)
        )
        guild = ctx.guild
        if guild and not current_perms.is_superset(self.permission_cache):
            current_perms_set = set(iter(current_perms))
            expected_perms_set = set(iter(self.permission_cache))
            diff = expected_perms_set - current_perms_set
            missing_perms = dict((i for i in diff if i[-1] is not False))
            missing_perms = OrderedDict(sorted(missing_perms.items()))
            missing_permissions = missing_perms.keys()
            log.debug(
                "Missing the following perms in %d, Owner ID: %d: %s",
                ctx.guild.id,
                ctx.guild.owner.id,
                humanize_list(list(missing_permissions)),
            )
            if not surpass_ignore:
                text = (
                    "I'm missing permissions in this server, "
                    "Please address this as soon as possible.\n\n"
                    "Expected Permissions:\n"
                )
                for perm, value in missing_perms.items():
                    text += "{perm}: [{status}]\n".format(
                        status="Enabled" if value else "Disabled",
                        perm=HUMANIZED_PERM.get(perm),
                    )
                text = text.strip()
                if current_perms.send_messages and current_perms.read_messages:
                    await ctx.send(box(text=text, lang="ini"))
                else:
                    log.info(
                        "Missing write permission in %d, Owner ID: %d",
                        ctx.guild.id,
                        ctx.guild.owner.id,
                    )
                raise CheckFailure(message=text)

        with contextlib.suppress(Exception):
            player = lavalink.get_player(ctx.guild.id)
            notify_channel = player.fetch("notify_channel")
            if not notify_channel:
                player.store("notify_channel", ctx.channel.id)

        if self.local_folder_current_path is None:
            self.local_folder_current_path = await self.config_cache.localpath.get_context_value(
                ctx.guild
            )
        if not ctx.guild:
            return
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        if dj_enabled:
            dj_roles = await self.config_cache.dj_roles.get_context_value(ctx.guild)
            if not dj_roles:
                await self.config_cache.dj_status.set_guild(ctx.guild, None)
                await self.config_cache.dj_roles.set_guild(ctx.guild, None)
                await self.send_embed_msg(ctx, title="No DJ role found. Disabling DJ mode.")

    async def cog_after_invoke(self, ctx: commands.Context) -> None:
        await self.maybe_run_pending_db_tasks(ctx)

    async def cog_command_error(self, ctx: commands.Context, error: Exception) -> None:
        error = getattr(error, "original", error)
        handled = False
        if isinstance(error, CommandRejected):
            handled = True
            await self.send_embed_msg(
                ctx,
                title="Unable To Run Command",
                description=error.message,
                error=True,
            )
        elif isinstance(error, commands.ArgParserFailure):
            handled = True
            msg = "`{user_input}` is not a valid value for `{command}`".format(
                user_input=error.user_input,
                command=error.cmd,
            )
            if error.custom_help_msg:
                msg += f"\n{error.custom_help_msg}"
            await self.send_embed_msg(
                ctx,
                title="Unable To Parse Argument",
                description=msg,
                error=True,
            )
            if error.send_cmd_help:
                await ctx.send_help()
        elif isinstance(error, commands.ConversionFailure):
            handled = True
            if error.args:
                if match := RE_CONVERSION.search(error.args[0]):
                    await self.send_embed_msg(
                        ctx,
                        title="Invalid Argument",
                        description=(
                            "The argument you gave for `{}` is not valid: I was expecting a `{}`."
                        ).format(match.group(2), match.group(1)),
                        error=True,
                    )
                else:
                    await self.send_embed_msg(
                        ctx,
                        title="Invalid Argument",
                        description=error.args[0],
                        error=True,
                    )
            else:
                await ctx.send_help()
        elif isinstance(error, (IndexError, ClientConnectorError)) and any(
            e in str(error).lower() for e in ["no nodes found.", "cannot connect to host"]
        ):
            handled = True
            await self.send_embed_msg(
                ctx,
                title="Invalid Environment",
                description="Connection to Lavalink has been lost.",
                error=True,
            )
            debug_exc_log(log, error, "This is a handled error")
        elif isinstance(error, KeyError) and "such player for that guild" in str(error):
            handled = True
            await self.send_embed_msg(
                ctx,
                title="No Player Available",
                description="The bot is not connected to a voice channel.",
                error=True,
            )
            debug_exc_log(log, error, "This is a handled error")
        elif isinstance(error, (TrackEnqueueError, asyncio.exceptions.TimeoutError)):
            handled = True
            await self.send_embed_msg(
                ctx,
                title="Unable to Get Track",
                description=(
                    "I'm unable to get a track from Lavalink at the moment, "
                    "try again in a few minutes."
                ),
                error=True,
            )
            debug_exc_log(log, error, "This is a handled error")
        elif isinstance(error, discord.errors.HTTPException):
            handled = True
            await self.send_embed_msg(
                ctx,
                title="There was an issue communicating with Discord.",
                description="This error has been reported to the bot owner.",
                error=True,
            )
            log.exception(
                "This is not handled in the core Audio cog, please report it.", exc_info=error
            )
        if not isinstance(
            error,
            (
                commands.CheckFailure,
                commands.UserInputError,
                commands.DisabledCommand,
                commands.CommandOnCooldown,
                commands.MaxConcurrencyReached,
            ),
        ):
            self.update_player_lock(ctx, False)
            if self.api_interface is not None:
                await self.api_interface.run_tasks(ctx)
        if not handled:
            await self.bot.on_command_error(ctx, error, unhandled_by_cog=True)

    def cog_unload(self) -> None:
        if not self.cog_cleaned_up:
            self.bot.dispatch("red_audio_unload", self)
            self.session.detach()
            self.bot.loop.create_task(self._close_database())
            if self.player_automated_timer_task:
                self.player_automated_timer_task.cancel()

            if self.lavalink_connect_task:
                self.lavalink_connect_task.cancel()

            if self.cog_init_task:
                self.cog_init_task.cancel()

            if self._restore_task:
                self._restore_task.cancel()

            lavalink.unregister_event_listener(self.lavalink_event_handler)
            lavalink.unregister_update_listener(self.lavalink_update_handler)
            self.bot.loop.create_task(lavalink.close(self.bot))
            if self.player_manager is not None:
                self.bot.loop.create_task(self.player_manager.shutdown())

            self.cog_cleaned_up = True

    @commands.Cog.listener()
    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ) -> None:
        if await self.bot.cog_disabled_in_guild(self, member.guild):
            return
        await self.cog_ready_event.wait()
        if after.channel != before.channel:
            try:
                self.skip_votes[before.channel.guild.id].discard(member.id)
            except (ValueError, KeyError, AttributeError):
                pass

        channel = self.rgetattr(member, "voice.channel", None)
        bot_voice_state = self.rgetattr(member, "guild.me.voice.self_deaf", None)
        if (
            channel
            and bot_voice_state is False
            and await self.config_cache.auto_deafen.get_context_value(channel.guild)
        ):
            try:
                player = lavalink.get_player(channel.guild.id)
            except (KeyError, AttributeError):
                pass
            else:
                if player.channel.id == channel.id:
                    await self.self_deafen(player)

    @commands.Cog.listener()
    async def on_shard_disconnect(self, shard_id):
        self._diconnected_shard.add(shard_id)

    @commands.Cog.listener()
    async def on_shard_ready(self, shard_id):
        self._diconnected_shard.discard(shard_id)

    @commands.Cog.listener()
    async def on_shard_resumed(self, shard_id):
        self._diconnected_shard.discard(shard_id)
