import logging
from pathlib import Path

import lavalink
from lavalink import filters
from lavalink.filters import Equalizer
from redbot.core import commands
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import box
from tabulate import tabulate

from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = logging.getLogger("red.cogs.Audio.cog.Commands.Effects")
_ = Translator("Audio", Path(__file__))


class EffectsCommands(MixinMeta, metaclass=CompositeMetaClass):
    @commands.group(name="effects", invoke_without_command=True)
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def command_effects(self, ctx: commands.Context):
        """Control all affects that can be applied to tracks."""
        if not self._player_check(ctx):
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))

        player = lavalink.get_player(ctx.guild.id)
        equalizer = player.equalizer
        karaoke = player.karaoke
        timescale = player.timescale
        tremolo = player.tremolo
        vibrato = player.vibrato
        rotation = player.rotation
        distortion = player.distortion
        low_pass = player.low_pass
        channel_mix = player.channel_mix
        t_effect = _("Effect")
        t_activated = _("State")
        t_yes = _("Activated")
        t_no = _("Deactivated")

        data = [
            {
                t_effect: equalizer.__class__.__name__,
                t_activated: _("Active: {name}").format(name=equalizer.name)
                if equalizer.changed
                else t_no,
            }
        ]

        for effect in (
            karaoke,
            timescale,
            tremolo,
            vibrato,
            rotation,
            distortion,
            low_pass,
            channel_mix,
        ):
            data.append(
                {
                    t_effect: effect.__class__.__name__,
                    t_activated: t_yes if effect.changed else t_no,
                }
            )

        await self.send_embed_msg(
            ctx,
            title=_("Here is the music effects status:"),
            description=box(tabulate(data)),
        )

    @command_effects.command(name="karaoke")
    async def command_effects_karaoke(
        self, ctx: commands.Context, level: float, mono: float, band: float, width: float
    ):
        """
        Eliminate part of a band, usually targeting vocals.

        Defaults:
        level: 1.0
        mono = 1.0
        band = 220.0
        width = 100.0
        """
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))

        player = lavalink.get_player(ctx.guild.id)
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You must be in the voice channel to change effects."),
            )
        if dj_enabled and not can_skip and not await self.is_requester_alone(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You need the DJ role to change effects."),
            )

        karaoke = player.karaoke
        karaoke.level = level
        karaoke.mono_level = mono
        karaoke.filter_band = band
        karaoke.filter_width = width
        await player.set_karaoke(karaoke)
        await ctx.invoke(self.command_effects)

    @command_effects.command(name="timescale")
    async def command_effects_timescale(
        self, ctx: commands.Context, speed: float, pitch: float, rate: float
    ):
        """
        Changes the speed, pitch, and rate for tracks.

        Defaults:
        speed: 1.0
        pitch = 1.0
        rate = 1.0
        """
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))

        player = lavalink.get_player(ctx.guild.id)
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You must be in the voice channel to change effects."),
            )
        if dj_enabled and not can_skip and not await self.is_requester_alone(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You need the DJ role to change effects."),
            )

        timescale = player.timescale
        timescale.speed = speed
        timescale.pitch = pitch
        timescale.rate = rate
        await player.set_timescale(timescale)
        await ctx.invoke(self.command_effects)

    @command_effects.command(name="tremolo")
    async def command_effects_tremolo(self, ctx: commands.Context, frequency: float, depth: float):
        """
        Uses amplification to create a shuddering effect, where the volume quickly oscillates.

        Defaults:
        frequency: 2.0
        depth = 0.5

        Constraints:
        frequency > 0
        depth >0 and <=1
        """
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))

        player = lavalink.get_player(ctx.guild.id)
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You must be in the voice channel to change effects."),
            )
        if dj_enabled and not can_skip and not await self.is_requester_alone(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You need the DJ role to change effects."),
            )

        tremolo = player.tremolo
        try:
            tremolo.frequency = frequency
        except ValueError:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Set Effect"),
                description=_("Tremolo frequency must be greater than 0."),
            )
        try:
            tremolo.depth = depth
        except ValueError:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Set Effect"),
                description=_(
                    "Tremolo depth must be greater than 0 and less than or equals to 1."
                ),
            )
        await player.set_tremolo(tremolo)
        await ctx.invoke(self.command_effects)

    @command_effects.command(name="vibrato")
    async def command_effects_vibrato(self, ctx: commands.Context, frequency: float, depth: float):
        """
        Uses amplification to create a shuddering effect, where the pitch quickly oscillates.

        Defaults:
        frequency: 2.0
        depth = 0.5

        Constraints:
        frequency > 0 and <= 14
        depth >0 and <=1
        """
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))

        player = lavalink.get_player(ctx.guild.id)
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You must be in the voice channel to change effects."),
            )
        if dj_enabled and not can_skip and not await self.is_requester_alone(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You need the DJ role to change effects."),
            )

        vibrato = player.vibrato
        try:
            vibrato.frequency = frequency
        except ValueError:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Set Effect"),
                description=_(
                    "Vibrato frequency must be greater than 0 and less than or equals to 14."
                ),
            )
        try:
            vibrato.depth = depth
        except ValueError:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Set Effect"),
                description=_(
                    "Vibrato depth must be greater than 0 and less than or equals to 1."
                ),
            )
        await player.set_vibrato(vibrato)
        await ctx.invoke(self.command_effects)

    @command_effects.command(name="rotation")
    async def command_effects_rotation(self, ctx: commands.Context, frequency: float):
        """
        Rotates the sound around the stereo channels/user headphone

        Default:
        frequency: 0
        """
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))

        player = lavalink.get_player(ctx.guild.id)
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You must be in the voice channel to change effects."),
            )
        if dj_enabled and not can_skip and not await self.is_requester_alone(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You need the DJ role to change effects."),
            )

        rotation = player.rotation
        rotation.hertz = frequency
        await player.set_rotation(rotation)
        await ctx.invoke(self.command_effects)

    @command_effects.command(name="distortion")
    async def command_effects_distortion(
        self,
        ctx: commands.Context,
        soffset: float,
        sscale: float,
        coffset: float,
        cscale: float,
        toffset: float,
        tscale: float,
        offset: float,
        scale: float,
    ):
        """Distortion effect. It can generate some pretty unique audio effects.

        Default:
        soffset: 0
        sscale: 1
        coffset: 0
        cscale: 1
        toffset: 0
        tscale: 1
        offset: 0
        scale: 1
        """
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))

        player = lavalink.get_player(ctx.guild.id)
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You must be in the voice channel to change effects."),
            )
        if dj_enabled and not can_skip and not await self.is_requester_alone(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You need the DJ role to change effects."),
            )

        distortion = player.distortion
        distortion.scale = scale
        distortion.offset = offset
        distortion.sin_offset = soffset
        distortion.sin_scale = sscale
        distortion.cos_scale = cscale
        distortion.cos_offset = coffset
        distortion.tan_offset = toffset
        distortion.tan_scale = tscale
        await player.set_distortion(distortion)
        await ctx.invoke(self.command_effects)

    @command_effects.command(name="reset", aliases=["clear"])
    async def command_effects_reset(self, ctx: commands.Context):
        """Reset all effects."""
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))

        player = lavalink.get_player(ctx.guild.id)
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You must be in the voice channel to change effects."),
            )
        if dj_enabled and not can_skip and not await self.is_requester_alone(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You need the DJ role to change effects."),
            )

        player.equalizer.reset()
        player.karaoke.reset()
        player.timescale.reset()
        player.tremolo.reset()
        player.vibrato.reset()
        player.rotation.reset()
        player.distortion.reset()
        player.low_pass.reset()
        player.channel_mix.reset()

        await player.set_filters()
        await ctx.invoke(self.command_effects)

    @command_effects.command(name="bassboost", aliases=["baseboost"])
    async def command_effects_bassboost(self, ctx: commands.Context):
        """This effect emphasizes Punchy Bass and Crisp Mid-High tones.

        Not suitable for tracks with Deep/Low Bass."""
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))

        player = lavalink.get_player(ctx.guild.id)
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You must be in the voice channel to apply effects."),
            )
        if dj_enabled and not can_skip and not await self.is_requester_alone(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You need the DJ role to apply effects."),
            )

        eq = Equalizer.boost()
        await player.set_equalizer(equalizer=eq)
        async with self.config.custom("EQUALIZER", ctx.guild.id).all() as eq_data:
            eq_data["eq_bands"] = player.equalizer.get()
            eq_data["name"] = player.equalizer.name
        await ctx.invoke(self.command_effects)

    @command_effects.command(name="piano")
    async def command_effects_piano(self, ctx: commands.Context):
        """This effect is suitable for Piano tracks, or tacks with an emphasis on Female Vocals.

        Could also be used as a Bass Cutoff."""
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))

        player = lavalink.get_player(ctx.guild.id)
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You must be in the voice channel to apply effects."),
            )
        if dj_enabled and not can_skip and not await self.is_requester_alone(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You need the DJ role to apply effectss."),
            )

        eq = Equalizer.piano()
        await player.set_equalizer(equalizer=eq)
        async with self.config.custom("EQUALIZER", ctx.guild.id).all() as eq_data:
            eq_data["eq_bands"] = player.equalizer.get()
            eq_data["name"] = player.equalizer.name
        await ctx.invoke(self.command_effects)

    @command_effects.command(name="metal")
    async def command_effects_metal(self, ctx: commands.Context):
        """Experimental Metal/Rock Equalizer.

        Expect clipping on Bassy songs."""
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))

        player = lavalink.get_player(ctx.guild.id)
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You must be in the voice channel to apply effects."),
            )
        if dj_enabled and not can_skip and not await self.is_requester_alone(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You need the DJ role to apply effects."),
            )

        eq = Equalizer.metal()
        await player.set_equalizer(equalizer=eq)
        async with self.config.custom("EQUALIZER", ctx.guild.id).all() as eq_data:
            eq_data["eq_bands"] = player.equalizer.get()
            eq_data["name"] = player.equalizer.name
        await ctx.invoke(self.command_effects)

    @command_effects.command(name="nightcore")
    async def command_effects_nightcore(self, ctx: commands.Context):
        """Apply the nightcore effect."""
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))

        player = lavalink.get_player(ctx.guild.id)
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You must be in the voice channel to apply effects."),
            )
        if dj_enabled and not can_skip and not await self.is_requester_alone(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You need the DJ role to apply effects."),
            )

        eq = filters.Equalizer(
            levels=[
                {"band": 0, "gain": -0.075},
                {"band": 1, "gain": 0.125},
                {"band": 2, "gain": 0.125},
            ],
            name="Nightcore",
        )
        ts = filters.Timescale(speed=1.17, pitch=1.2, rate=1)
        await player.set_filters(equalizer=eq, timescale=ts)
        async with self.config.custom("EQUALIZER", ctx.guild.id).all() as eq_data:
            eq_data["eq_bands"] = player.equalizer.get()
            eq_data["name"] = player.equalizer.name
        await ctx.invoke(self.command_effects)

    @command_effects.command(name="vaporwave")
    async def command_effects_vaporwave(self, ctx: commands.Context):
        """Apply the vaporwave effect."""
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))

        player = lavalink.get_player(ctx.guild.id)
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You must be in the voice channel to apply effects."),
            )
        if dj_enabled and not can_skip and not await self.is_requester_alone(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You need the DJ role to apply effects."),
            )

        eq = filters.Equalizer(
            levels=[
                {"band": 0, "gain": -0.075},
                {"band": 1, "gain": 0.125},
                {"band": 2, "gain": 0.125},
            ],
            name="Vaporwave",
        )
        ts = filters.Timescale(speed=0.70, pitch=0.75, rate=1)
        tm = filters.Tremolo(frequency=14, depth=0.25)
        await player.set_filters(equalizer=eq, timescale=ts, tremolo=tm)
        async with self.config.custom("EQUALIZER", ctx.guild.id).all() as eq_data:
            eq_data["eq_bands"] = player.equalizer.get()
            eq_data["name"] = player.equalizer.name
        await ctx.invoke(self.command_effects)

    @command_effects.command(name="synth")
    async def command_effects_synth(self, ctx: commands.Context):
        """Apply the synth effect."""
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))

        player = lavalink.get_player(ctx.guild.id)
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You must be in the voice channel to apply effects."),
            )
        if dj_enabled and not can_skip and not await self.is_requester_alone(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You need the DJ role to apply effects."),
            )

        eq = filters.Equalizer(
            levels=[
                {"band": 0, "gain": -0.075},
                {"band": 1, "gain": 0.325},
                {"band": 2, "gain": 0.325},
                {"band": 4, "gain": 0.25},
                {"band": 5, "gain": 0.25},
                {"band": 7, "gain": -0.35},
                {"band": 8, "gain": -0.35},
                {"band": 11, "gain": 0.8},
                {"band": 12, "gain": 0.45},
                {"band": 13, "gain": -0.025},
            ],
            name="Synth",
        )
        ts = filters.Timescale(speed=1.0, pitch=1.1, rate=1.00)
        tm = filters.Tremolo(frequency=4, depth=0.25)
        vb = filters.Vibrato(frequency=11, depth=0.3)
        dt = filters.Distortion(
            sin_offset=0,
            sin_scale=-0.25,
            cos_offset=0,
            cos_scale=-0.5,
            tan_offset=-2.75,
            tan_scale=-0.7,
            offset=-0.27,
            scale=-1.2,
        )
        await player.set_filters(equalizer=eq, timescale=ts, tremolo=tm, vibrato=vb, distortion=dt)
        async with self.config.custom("EQUALIZER", ctx.guild.id).all() as eq_data:
            eq_data["eq_bands"] = player.equalizer.get()
            eq_data["name"] = player.equalizer.name
        await ctx.invoke(self.command_effects)

    @command_effects.command(name="channelmix")
    async def command_effects_channelmix(
        self,
        ctx: commands.Context,
        left_to_left: float,
        left_to_right: float,
        right_to_left: float,
        right_to_right: float,
    ):
        """
        Mixes both channels (left and right), with a configurable factor on how much each channel affects the other.

        Defaults:
        left_to_right: 1.0
        left_to_right = 0.0
        right_to_left = 0.0
        right_to_right = 1.0
        """
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))

        player = lavalink.get_player(ctx.guild.id)
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You must be in the voice channel to change effects."),
            )
        if dj_enabled and not can_skip and not await self.is_requester_alone(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You need the DJ role to change effects."),
            )

        channel_mix = player.channel_mix
        channel_mix.left_to_left = left_to_left
        channel_mix.left_to_right = left_to_right
        channel_mix.right_to_left = right_to_left
        channel_mix.right_to_right = right_to_right
        await player.set_channel_mix(channel_mix)
        await ctx.invoke(self.command_effects)

    @command_effects.command(name="lowpass")
    async def command_effects_lowpass(self, ctx: commands.Context, smoothing: float):
        """
        Higher frequencies get suppressed, while lower frequencies pass through this filter

        Default:
        smoothing: 20.0
        """
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))

        player = lavalink.get_player(ctx.guild.id)
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You must be in the voice channel to change effects."),
            )
        if dj_enabled and not can_skip and not await self.is_requester_alone(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You need the DJ role to change effects."),
            )

        low_pass = player.low_pass
        low_pass.smoothing = smoothing
        await player.set_low_pass(low_pass)
        await ctx.invoke(self.command_effects)
