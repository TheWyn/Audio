# Future Imports
from __future__ import annotations

# Standard Library Imports
from abc import ABC
from typing import Optional, Union
import asyncio
import contextlib
import logging
import time

# Dependency Imports
from redbot.core import commands
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import humanize_number
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate
import discord

# My Modded Imports
from lavalink.filters import Volume
import lavalink

# Music Imports
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = logging.getLogger("red.cogs.Music.cog.Commands.player_controller")


class PlayerControllerCommands(MixinMeta, ABC, metaclass=CompositeMetaClass):
    @commands.command(name="disconnect")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def command_disconnect(self, ctx: commands.Context):
        """Disconnect from the voice channel."""
        if not self._player_check(ctx):
            return await self.send_embed_msg(ctx, title="Nothing playing.")
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        vote_enabled = await self.config_cache.votes.get_context_value(ctx.guild)
        player = lavalink.get_player(ctx.guild.id)
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (
            (vote_enabled or (vote_enabled and dj_enabled))
            and not can_skip
            and not await self.is_requester_alone(ctx)
        ):
            return await self.send_embed_msg(
                ctx,
                title="Unable To Disconnect",
                description="There are other people listening - vote to skip instead.",
            )
        if dj_enabled and not vote_enabled and not can_skip:
            return await self.send_embed_msg(
                ctx,
                title="Unable To Disconnect",
                description="You need the DJ role to disconnect.",
            )
        if dj_enabled and not can_skip:
            return await self.send_embed_msg(
                ctx,
                title="Unable to Disconnect",
                description="You need the DJ role to disconnect.",
            )

        await self.send_embed_msg(ctx, title="Disconnecting...")
        self.bot.dispatch("red_audio_audio_disconnect", ctx.guild)
        self.update_player_lock(ctx, False)
        player.queue = []
        player.store("playing_song", None)
        player.store("autoplay_notified", False)
        async with self.config.custom("EQUALIZER", ctx.guild.id).all() as eq_data:
            eq_data["eq_bands"] = player.equalizer.get()
            eq_data["name"] = player.equalizer.name
        await player.stop()
        await player.disconnect()
        await self.config_cache.autoplay.set_currently_in_guild(ctx.guild)
        self._ll_guild_updates.discard(ctx.guild.id)
        await self.api_interface.persistent_queue_api.drop(ctx.guild.id)

    @commands.command(name="now")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    async def command_now(self, ctx: commands.Context):
        """Now playing."""
        if not self._player_check(ctx):
            return await self.send_embed_msg(ctx, title="Nothing playing.")
        emoji = {
            "prev": "\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\N{VARIATION SELECTOR-16}",
            "stop": "\N{BLACK SQUARE FOR STOP}\N{VARIATION SELECTOR-16}",
            "pause": "\N{BLACK RIGHT-POINTING TRIANGLE WITH DOUBLE VERTICAL BAR}\N{VARIATION SELECTOR-16}",
            "next": "\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\N{VARIATION SELECTOR-16}",
            "close": "\N{CROSS MARK}",
        }
        expected = tuple(emoji.values())
        player = lavalink.get_player(ctx.guild.id)
        player.store("notify_channel", ctx.channel.id)
        if player.current:
            arrow = await self.draw_time(ctx)
            pos = self.format_time(player.position)
            if player.current.is_stream:
                dur = "LIVE"
            else:
                dur = self.format_time(player.current.length)
            song = (
                await self.get_track_description(player.current, self.local_folder_current_path)
                or ""
            )
            song += "\n Requested by: **{track.requester.mention}**".format(track=player.current)
            song += "\n\n{arrow}`{pos}`/`{dur}`".format(arrow=arrow, pos=pos, dur=dur)
        else:
            song = "Nothing."

        if player.fetch("np_message") is not None:
            with contextlib.suppress(discord.HTTPException):
                await player.fetch("np_message").delete()
        embed = discord.Embed(title="Now Playing", description=song)
        shuffle = await self.config_cache.shuffle.get_context_value(ctx.guild)
        repeat = await self.config_cache.repeat.get_context_value(ctx.guild)
        autoplay = await self.config_cache.autoplay.get_context_value(ctx.guild)
        thumbnail = await self.config_cache.thumbnail.get_context_value(ctx.guild)
        if thumbnail and player.current and player.current.thumbnail:
            embed.set_thumbnail(url=player.current.thumbnail)
        text = ""
        text += (
            "Auto-Play" + ": " + ("\N{WHITE HEAVY CHECK MARK}" if autoplay else "\N{CROSS MARK}")
        )
        text += (
            (" | " if text else "")
            + "Shuffle"
            + ": "
            + ("\N{WHITE HEAVY CHECK MARK}" if shuffle else "\N{CROSS MARK}")
        )
        text += (
            (" | " if text else "")
            + "Repeat"
            + ": "
            + ("\N{WHITE HEAVY CHECK MARK}" if repeat else "\N{CROSS MARK}")
        )

        message = await self.send_embed_msg(ctx, embed=embed, footer=text)

        player.store("np_message", message)

        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        vote_enabled = await self.config_cache.votes.get_context_value(ctx.guild)
        if (
            (dj_enabled or vote_enabled)
            and not await self._can_instaskip(ctx, ctx.author)
            and not await self.is_requester_alone(ctx)
        ):
            return

        if not player.queue and not autoplay:
            expected = (emoji["stop"], emoji["pause"], emoji["close"])
        task: Optional[asyncio.Task]
        if player.current:
            task = start_adding_reactions(message, expected[:5])
        else:
            task = None

        try:
            (r, u) = await self.bot.wait_for(
                "reaction_add",
                check=ReactionPredicate.with_emojis(expected, message, ctx.author),
                timeout=30.0,
            )
        except asyncio.TimeoutError:
            return await self._clear_react(message, emoji)
        else:
            if task is not None:
                task.cancel()
        reacts = {v: k for k, v in emoji.items()}
        react = reacts[r.emoji]
        if react == "prev":
            await self._clear_react(message, emoji)
            await ctx.invoke(self.command_prev)
        elif react == "stop":
            await self._clear_react(message, emoji)
            await ctx.invoke(self.command_stop)
        elif react == "pause":
            await self._clear_react(message, emoji)
            await ctx.invoke(self.command_pause)
        elif react == "next":
            await self._clear_react(message, emoji)
            await ctx.invoke(self.command_skip)
        elif react == "close":
            await message.delete()

    @commands.command(name="pause")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def command_pause(self, ctx: commands.Context):
        """Pause or resume a playing track."""
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        if not self._player_check(ctx):
            return await self.send_embed_msg(ctx, title="Nothing playing.")
        player = lavalink.get_player(ctx.guild.id)
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            return await self.send_embed_msg(
                ctx,
                title="Unable To Manage Tracks",
                description="You must be in the voice channel to pause or resume.",
            )
        if dj_enabled and not can_skip and not await self.is_requester_alone(ctx):
            return await self.send_embed_msg(
                ctx,
                title="Unable To Manage Tracks",
                description="You need the DJ role to pause or resume tracks.",
            )
        player.store("notify_channel", ctx.channel.id)
        if not player.current:
            return await self.send_embed_msg(ctx, title="Nothing playing.")
        description = await self.get_track_description(
            player.current, self.local_folder_current_path
        )

        if player.current and not player.paused:
            await player.pause()
            return await self.send_embed_msg(ctx, title="Track Paused", description=description)
        if player.current and player.paused:
            await player.pause(False)
            return await self.send_embed_msg(ctx, title="Track Resumed", description=description)

        await self.send_embed_msg(ctx, title="Nothing playing.")

    @commands.command(name="prev")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def command_prev(self, ctx: commands.Context):
        """Skip to the start of the previously played track."""
        if not self._player_check(ctx):
            return await self.send_embed_msg(ctx, title="Nothing playing.")
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        vote_enabled = await self.config_cache.votes.get_context_value(ctx.guild)
        is_alone = await self.is_requester_alone(ctx)
        is_requester = await self.is_requester(ctx, ctx.author)
        can_skip = await self._can_instaskip(ctx, ctx.author)
        player = lavalink.get_player(ctx.guild.id)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            return await self.send_embed_msg(
                ctx,
                title="Unable To Skip Tracks",
                description="You must be in the voice channel to skip the track.",
            )
        if vote_enabled and not can_skip and not is_alone:
            return await self.send_embed_msg(
                ctx,
                title="Unable To Skip Tracks",
                description="There are other people listening - vote to skip instead.",
            )
        if dj_enabled and not vote_enabled and not can_skip and not is_requester and not is_alone:
            return await self.send_embed_msg(
                ctx,
                title="Unable To Skip Tracks",
                description=(
                    "You need the DJ role or be the track requester "
                    "to enqueue the previous song tracks."
                ),
            )
        player.store("notify_channel", ctx.channel.id)
        if player.fetch("prev_song") is None:
            return await self.send_embed_msg(
                ctx, title="Unable To Play Tracks", description="No previous track."
            )
        track = player.fetch("prev_song")
        track.extras.update(
            {
                "enqueue_time": int(time.time()),
                "vc": player.channel.id,
                "requester": ctx.author.id,
            }
        )
        player.add(player.fetch("prev_requester"), track)
        self.bot.dispatch("red_audio_track_enqueue", player.guild, track, ctx.author)
        queue_len = len(player.queue)
        bump_song = player.queue[-1]
        player.queue.insert(0, bump_song)
        player.queue.pop(queue_len)
        await player.skip()
        description = await self.get_track_description(
            player.current, self.local_folder_current_path
        )
        embed = discord.Embed(title="Replaying Track", description=description)
        await self.send_embed_msg(ctx, embed=embed)

    @commands.command(name="seek")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def command_seek(self, ctx: commands.Context, seconds: Union[int, str]):
        """Seek ahead or behind on a track by seconds or a to a specific time.

        Accepts seconds or a value formatted like 00:00:00 (`hh:mm:ss`) or 00:00 (`mm:ss`).
        """
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        vote_enabled = await self.config_cache.votes.get_context_value(ctx.guild)
        is_alone = await self.is_requester_alone(ctx)
        is_requester = await self.is_requester(ctx, ctx.author)
        can_skip = await self._can_instaskip(ctx, ctx.author)

        if not self._player_check(ctx):
            return await self.send_embed_msg(ctx, title="Nothing playing.")
        player = lavalink.get_player(ctx.guild.id)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            return await self.send_embed_msg(
                ctx,
                title="Unable To Seek Tracks",
                description="You must be in the voice channel to use seek.",
            )

        if vote_enabled and not can_skip and not is_alone:
            return await self.send_embed_msg(
                ctx,
                title="Unable To Seek Tracks",
                description="There are other people listening - vote to skip instead.",
            )

        if dj_enabled and not can_skip and not is_requester and not is_alone:
            return await self.send_embed_msg(
                ctx,
                title="Unable To Seek Tracks",
                description="You need the DJ role or be the track requester to use seek.",
            )
        player.store("notify_channel", ctx.channel.id)
        if player.current:
            if player.current.is_stream:
                return await self.send_embed_msg(
                    ctx, title="Unable To Seek Tracks", description="Can't seek on a stream."
                )
            try:
                int(seconds)
                abs_position = False
            except ValueError:
                abs_position = True
                seconds = self.time_convert(seconds)
            if seconds == 0:
                return await self.send_embed_msg(
                    ctx,
                    title="Unable To Seek Tracks",
                    description="Invalid input for the time to seek.",
                )
            if not abs_position:
                time_sec = int(seconds) * 1000
                seek = player.position + time_sec
                if seek <= 0:
                    await self.send_embed_msg(
                        ctx,
                        title="Moved {num_seconds}s to 00:00:00".format(num_seconds=seconds),
                    )
                else:
                    await self.send_embed_msg(
                        ctx,
                        title="Moved {num_seconds}s to {time}".format(
                            num_seconds=seconds, time=self.format_time(seek)
                        ),
                    )
                await player.seek(seek)
            else:
                await self.send_embed_msg(
                    ctx,
                    title="Moved to {time}".format(time=self.format_time(seconds * 1000)),
                )
                await player.seek(seconds * 1000)
        else:
            await self.send_embed_msg(ctx, title="Nothing playing.")

    @commands.group(name="shuffle", autohelp=False)
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def command_shuffle(self, ctx: commands.Context):
        """Toggle shuffle."""
        if ctx.invoked_subcommand is not None:
            return
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if dj_enabled and not can_skip:
            return await self.send_embed_msg(
                ctx,
                title="Unable To Toggle Shuffle",
                description="You need the DJ role to toggle shuffle.",
            )
        if self._player_check(ctx):
            await self.set_player_settings(ctx)
            player = lavalink.get_player(ctx.guild.id)
            if (
                not ctx.author.voice or ctx.author.voice.channel != player.channel
            ) and not can_skip:
                return await self.send_embed_msg(
                    ctx,
                    title="Unable To Toggle Shuffle",
                    description="You must be in the voice channel to toggle shuffle.",
                )
            player.store("notify_channel", ctx.channel.id)

        shuffle = await self.config_cache.shuffle.get_context_value(ctx.guild)
        await self.config_cache.shuffle.set_guild(ctx.guild, not shuffle)
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="Shuffle tracks: {true_or_false}.".format(
                true_or_false="Enabled" if not shuffle else "Disabled"
            ),
        )
        if self._player_check(ctx):
            await self.set_player_settings(ctx)

    @command_shuffle.command(name="bumped")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def command_shuffle_bumpped(self, ctx: commands.Context):
        """Toggle bumped track shuffle.

        Set this to disabled if you wish to avoid bumped songs being shuffled. This takes priority
        over `[p]shuffle`.
        """
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if dj_enabled and not can_skip:
            return await self.send_embed_msg(
                ctx,
                title="Unable To Toggle Shuffle",
                description="You need the DJ role to toggle shuffle.",
            )
        if self._player_check(ctx):
            await self.set_player_settings(ctx)
            player = lavalink.get_player(ctx.guild.id)
            if (
                not ctx.author.voice or ctx.author.voice.channel != player.channel
            ) and not can_skip:
                return await self.send_embed_msg(
                    ctx,
                    title="Unable To Toggle Shuffle",
                    description="You must be in the voice channel to toggle shuffle.",
                )
            player.store("notify_channel", ctx.channel.id)

        bumped = await self.config_cache.shuffle_bumped.get_context_value(ctx.guild)
        await self.config_cache.shuffle_bumped.set_guild(ctx.guild, not bumped)
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="Shuffle bumped tracks: {true_or_false}.".format(
                true_or_false="Enabled" if not bumped else "Disabled"
            ),
        )
        if self._player_check(ctx):
            await self.set_player_settings(ctx)

    @commands.command(name="skip")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def command_skip(self, ctx: commands.Context, skip_to_track: int = None):
        """Skip to the next track, or to a given track number."""
        if not self._player_check(ctx):
            return await self.send_embed_msg(ctx, title="Nothing playing.")
        player = lavalink.get_player(ctx.guild.id)
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            return await self.send_embed_msg(
                ctx,
                title="Unable To Skip Tracks",
                description="You must be in the voice channel to skip the music.",
            )
        if not player.current:
            return await self.send_embed_msg(ctx, title="Nothing playing.")
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        vote_enabled = await self.config_cache.votes.get_context_value(ctx.guild)
        is_alone = await self.is_requester_alone(ctx)
        is_requester = await self.is_requester(ctx, ctx.author)
        if dj_enabled and not vote_enabled:
            if not can_skip and not is_requester and not is_alone:
                return await self.send_embed_msg(
                    ctx,
                    title="Unable To Skip Tracks",
                    description="You need the DJ role or be the track requester to skip tracks.",
                )
            if (
                is_requester
                and not can_skip
                and isinstance(skip_to_track, int)
                and skip_to_track > 1
            ):
                return await self.send_embed_msg(
                    ctx,
                    title="Unable To Skip Tracks",
                    description="You can only skip the current track.",
                )
        player.store("notify_channel", ctx.channel.id)
        if not vote_enabled or can_skip:
            return await self._skip_action(ctx, skip_to_track)
        if skip_to_track is not None:
            return await self.send_embed_msg(
                ctx,
                title="Unable To Skip Tracks",
                description="Can't skip to a specific track in vote mode without the DJ role.",
            )
        if ctx.author.id in self.skip_votes[ctx.guild.id]:
            self.skip_votes[ctx.guild.id].discard(ctx.author.id)
            reply = "I removed your vote to skip."
        else:
            self.skip_votes[ctx.guild.id].add(ctx.author.id)
            reply = "You voted to skip."

        num_votes = len(self.skip_votes[ctx.guild.id])
        vote_mods = []
        for member in player.channel.members:
            can_skip = await self._can_instaskip(ctx, member)
            if can_skip:
                vote_mods.append(member)
        num_members = len(player.channel.members) - len(vote_mods)
        vote = int(100 * num_votes / num_members)
        percent = await self.config_cache.votes_percentage.get_context_value(ctx.guild)
        if vote >= percent:
            self.skip_votes[ctx.guild.id] = set()
            await self.send_embed_msg(ctx, title="Vote threshold met.")
            return await self._skip_action(ctx)
        else:
            reply += (
                " Votes: {num_votes}/{num_members}"
                " ({cur_percent}% out of {required_percent}% needed)"
            ).format(
                num_votes=humanize_number(num_votes),
                num_members=humanize_number(num_members),
                cur_percent=vote,
                required_percent=percent,
            )
            return await self.send_embed_msg(ctx, title=reply)

    @commands.command(name="stop")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def command_stop(self, ctx: commands.Context):
        """Stop playback and clear the queue."""
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        vote_enabled = await self.config_cache.votes.get_context_value(ctx.guild)
        if not self._player_check(ctx):
            return await self.send_embed_msg(ctx, title="Nothing playing.")
        player = lavalink.get_player(ctx.guild.id)
        can_skip = await self._can_instaskip(ctx, ctx.author)
        is_alone = await self.is_requester_alone(ctx)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            return await self.send_embed_msg(
                ctx,
                title="Unable To Stop Player",
                description="You must be in the voice channel to stop the music.",
            )
        if vote_enabled and not can_skip and not is_alone:
            return await self.send_embed_msg(
                ctx,
                title="Unable To Stop Player",
                description="There are other people listening - vote to skip instead.",
            )
        if dj_enabled and not vote_enabled and not can_skip:
            return await self.send_embed_msg(
                ctx,
                title="Unable To Stop Player",
                description="You need the DJ role to stop the music.",
            )
        player.store("notify_channel", ctx.channel.id)
        if (
            player.is_playing
            or (not player.is_playing and player.paused)
            or player.queue
            or getattr(player.current, "extras", {}).get("autoplay")
        ):
            async with self.config.custom("EQUALIZER", ctx.guild.id).all() as eq_data:
                eq_data["eq_bands"] = player.equalizer.get()
                eq_data["name"] = player.equalizer.name
            player.queue = []
            player.store("playing_song", None)
            player.store("prev_requester", None)
            player.store("prev_song", None)
            player.store("requester", None)
            player.store("autoplay_notified", False)
            await player.stop()
            await self.config_cache.autoplay.set_currently_in_guild(ctx.guild)
            await self.send_embed_msg(ctx, title="Stopping...")
            await self.api_interface.persistent_queue_api.drop(ctx.guild.id)

    @commands.command(name="summon")
    @commands.guild_only()
    @commands.cooldown(1, 15, commands.BucketType.guild)
    @commands.bot_has_permissions(embed_links=True)
    async def command_summon(self, ctx: commands.Context):
        """Summon the bot to a voice channel."""
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        vote_enabled = await self.config_cache.votes.get_context_value(ctx.guild)
        is_alone = await self.is_requester_alone(ctx)
        is_requester = await self.is_requester(ctx, ctx.author)
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if vote_enabled and not can_skip and not is_alone:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title="Unable To Join Voice Channel",
                description="There are other people listening.",
            )
        if dj_enabled and not vote_enabled and not can_skip and not is_requester and not is_alone:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title="Unable To Join Voice Channel",
                description="You need the DJ role to summon the bot.",
            )

        try:
            if (
                not self.can_join_and_speak(ctx.author.voice.channel)
                or not ctx.author.voice.channel.permissions_for(ctx.me).move_members
                and self.is_vc_full(ctx.author.voice.channel)
            ):
                ctx.command.reset_cooldown(ctx)
                return await self.send_embed_msg(
                    ctx,
                    title="Unable To Join Voice Channel",
                    description="I don't have permission to connect and speak in your channel.",
                )
            if not self._player_check(ctx):
                player = await lavalink.connect(
                    ctx.author.voice.channel,
                    deafen=await self.config_cache.auto_deafen.get_context_value(ctx.guild),
                )
                player.store("notify_channel", ctx.channel.id)
            else:
                player = lavalink.get_player(ctx.guild.id)
                player.store("notify_channel", ctx.channel.id)
                if (
                    ctx.author.voice.channel == player.channel
                    and ctx.guild.me in ctx.author.voice.channel.members
                ):
                    ctx.command.reset_cooldown(ctx)
                    return
                await player.move_to(
                    ctx.author.voice.channel,
                    deafen=await self.config_cache.auto_deafen.get_context_value(ctx.guild),
                )
        except AttributeError:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title="Unable To Join Voice Channel",
                description="Connect to a voice channel first.",
            )
        except IndexError:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title="Unable To Join Voice Channel",
                description="Connection to Lavalink has not yet been established.",
            )

    @commands.command(name="volume")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def command_volume(self, ctx: commands.Context, vol: int = None):
        """Set the volume in percentages greater or equal to 0%."""
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if self._player_check(ctx):
            player = lavalink.get_player(ctx.guild.id)
            if (
                not ctx.author.voice or ctx.author.voice.channel != player.channel
            ) and not can_skip:
                return await self.send_embed_msg(
                    ctx,
                    title="Unable To Change Volume",
                    description="You must be in the voice channel to change the volume.",
                )
            player.store("notify_channel", ctx.channel.id)
        if dj_enabled and not can_skip and not await self._has_dj_role(ctx, ctx.author):
            return await self.send_embed_msg(
                ctx,
                title="Unable To Change Volume",
                description="You need the DJ role to change the volume.",
            )
        if not self._player_check(ctx):
            return await self.send_embed_msg(ctx, title="Nothing playing.")

        player = lavalink.get_player(ctx.guild.id)
        max_volume, max_source = await self.config_cache.volume.get_max_and_source(
            ctx.guild, player.channel
        )

        volume = (
            (
                min(
                    max(vol, 0),
                    max_volume,
                )
                / 100
            )
            if vol
            else None
        )
        if volume:
            vol = Volume(value=volume)
            if player.volume != vol:
                await player.set_volume(vol)
            player.store("notify_channel", ctx.channel.id)
            description = (
                "Currently set to **{volume}%**\n\n"
                "Maximum allowed volume here is **{max_volume}%** "
                "due to {restrictor} restrictions."
            ).format(volume=int(volume * 100), max_volume=max_volume, restrictor=max_source)
        else:
            description = (
                "Maximum allowed volume here is **{max_volume}%** "
                "due to {restrictor} restrictions."
            ).format(max_volume=max_volume, restrictor=max_source)

        embed = discord.Embed(
            title="Volume",
            description=description,
        )
        await self.send_embed_msg(ctx, embed=embed)

    @commands.command(name="repeat")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def command_repeat(self, ctx: commands.Context):
        """Toggle repeat."""
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if dj_enabled and not can_skip and not await self._has_dj_role(ctx, ctx.author):
            return await self.send_embed_msg(
                ctx,
                title="Unable To Toggle Repeat",
                description="You need the DJ role to toggle repeat.",
            )
        if self._player_check(ctx):
            await self.set_player_settings(ctx)
            player = lavalink.get_player(ctx.guild.id)
            if (
                not ctx.author.voice or ctx.author.voice.channel != player.channel
            ) and not can_skip:
                return await self.send_embed_msg(
                    ctx,
                    title="Unable To Toggle Repeat",
                    description="You must be in the voice channel to toggle repeat.",
                )
            player.store("notify_channel", ctx.channel.id)

        autoplay = await self.config_cache.autoplay.get_context_value(ctx.guild)
        repeat = await self.config_cache.repeat.get_context_value(ctx.guild)
        msg = ""
        msg += "Repeat tracks: {true_or_false}.".format(
            true_or_false="Enabled" if not repeat else "Disabled"
        )
        await self.config_cache.repeat.set_guild(ctx.guild, not repeat)
        if repeat is not True and autoplay is True:
            msg += "\nAuto-play has been disabled."
            await self.config_cache.autoplay.set_guild(ctx.guild, False)

        embed = discord.Embed(title="Setting Changed", description=msg)
        await self.send_embed_msg(ctx, embed=embed)
        if self._player_check(ctx):
            await self.set_player_settings(ctx)

    @commands.command(name="remove")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def command_remove(self, ctx: commands.Context, index_or_url: Union[int, str]):
        """Remove a specific track number from the queue."""
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        if not self._player_check(ctx):
            return await self.send_embed_msg(ctx, title="Nothing playing.")
        player = lavalink.get_player(ctx.guild.id)
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if not player.queue:
            return await self.send_embed_msg(ctx, title="Nothing queued.")
        if dj_enabled and not can_skip:
            return await self.send_embed_msg(
                ctx,
                title="Unable To Modify Queue",
                description="You need the DJ role to remove tracks.",
            )
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            return await self.send_embed_msg(
                ctx,
                title="Unable To Modify Queue",
                description="You must be in the voice channel to manage the queue.",
            )
        player.store("notify_channel", ctx.channel.id)
        if isinstance(index_or_url, int):
            if index_or_url > len(player.queue) or index_or_url < 1:
                return await self.send_embed_msg(
                    ctx,
                    title="Unable To Modify Queue",
                    description="Song number must be greater than 1 and within the queue limit.",
                )
            index_or_url -= 1
            removed = player.queue.pop(index_or_url)
            await self.api_interface.persistent_queue_api.played(
                ctx.guild.id, removed.extras.get("enqueue_time")
            )
            removed_title = await self.get_track_description(
                removed, self.local_folder_current_path
            )
            await self.send_embed_msg(
                ctx,
                title="Removed track from queue",
                description="Removed {track} from the queue.".format(track=removed_title),
            )
        else:
            clean_tracks = []
            removed_tracks = 0
            async for track in AsyncIter(player.queue):
                if track.uri != index_or_url:
                    clean_tracks.append(track)
                else:
                    await self.api_interface.persistent_queue_api.played(
                        ctx.guild.id, track.extras.get("enqueue_time")
                    )
                    removed_tracks += 1
            player.queue = clean_tracks
            if removed_tracks == 0:
                await self.send_embed_msg(
                    ctx,
                    title="Unable To Modify Queue",
                    description="Removed 0 tracks, nothing matches the URL provided.",
                )
            else:
                await self.send_embed_msg(
                    ctx,
                    title="Removed track from queue",
                    description=(
                        "Removed {removed_tracks} tracks from queue "
                        "which matched the URL provided."
                    ).format(removed_tracks=removed_tracks),
                )

    @commands.command(name="bump")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def command_bump(self, ctx: commands.Context, index: int):
        """Bump a track number to the top of the queue."""
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        if not self._player_check(ctx):
            return await self.send_embed_msg(ctx, title="Nothing playing.")
        player = lavalink.get_player(ctx.guild.id)
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            return await self.send_embed_msg(
                ctx,
                title="Unable To Bump Track",
                description="You must be in the voice channel to bump a track.",
            )
        if dj_enabled and not can_skip:
            return await self.send_embed_msg(
                ctx,
                title="Unable To Bump Track",
                description="You need the DJ role to bump tracks.",
            )
        if index > len(player.queue) or index < 1:
            return await self.send_embed_msg(
                ctx,
                title="Unable To Bump Track",
                description="Song number must be greater than 1 and within the queue limit.",
            )
        player.store("notify_channel", ctx.channel.id)
        bump_index = index - 1
        bump_song = player.queue[bump_index]
        bump_song.extras["bumped"] = True
        player.queue.insert(0, bump_song)
        removed = player.queue.pop(index)
        description = await self.get_track_description(removed, self.local_folder_current_path)
        await self.send_embed_msg(
            ctx, title="Moved track to the top of the queue.", description=description
        )
