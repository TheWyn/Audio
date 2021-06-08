# Future Imports
from __future__ import annotations

# Standard Library Imports
from typing import Dict, Optional, Tuple

# Dependency Imports
import discord

# Audio Imports
from .abc import CacheBase


class VolumeManager(CacheBase):
    __slots__ = (
        "_config",
        "bot",
        "enable_cache",
        "config_cache",
        "_cached_guild",
        "_cached_channel",
        "_cached_global",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cached_guild: Dict[int, int] = {}
        self._cached_channel: Dict[int, int] = {}
        self._cached_global: Dict[None, int] = {}

    async def get_guild(self, guild: discord.Guild) -> int:
        ret: int
        gid: int = guild.id
        if self.enable_cache and gid in self._cached_guild:
            ret = self._cached_guild[gid]
        else:
            ret = await self._config.guild_from_id(gid).volume()
            self._cached_guild[gid] = ret
        return ret

    async def set_guild(self, guild: discord.Guild, set_to: Optional[int]) -> None:
        gid: int = guild.id
        if set_to is not None:
            await self._config.guild_from_id(gid).volume.set(set_to)
            self._cached_guild[gid] = set_to
        else:
            await self._config.guild_from_id(gid).volume.clear()
            self._cached_guild[gid] = self._config.defaults["GUILD"]["volume"]

    async def get_global(self) -> int:
        ret: int
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global[None]
        else:
            ret = await self._config.volume()
            self._cached_global[None] = ret
        return ret

    async def set_global(self, set_to: Optional[int]) -> None:
        if set_to is not None:
            await self._config.volume.set(set_to)
            self._cached_global[None] = set_to
        else:
            await self._config.volume.clear()
            self._cached_global[None] = self._config.defaults["GLOBAL"]["volume"]

    async def get_channel(self, channel: discord.VoiceChannel) -> int:
        ret: int
        vid: int = channel.id
        if self.enable_cache and vid in self._cached_channel:
            ret = self._cached_channel[vid]
        else:
            ret = await self._config.channel_from_id(vid).volume()
            self._cached_channel[vid] = ret
        return ret

    async def set_channel(self, channel: discord.VoiceChannel, set_to: Optional[int]) -> None:
        vid: int = channel.id
        if set_to is not None:
            await self._config.channel_from_id(vid).volume.set(set_to)
            self._cached_channel[vid] = set_to
        else:
            await self._config.channel_from_id(vid).volume.clear()
            self._cached_channel[vid] = self._config.defaults["TEXTCHANNEL"]["volume"]

    async def get_context_value(
        self, guild: discord.Guild, channel: discord.VoiceChannel = None
    ) -> int:
        global_value = await self.get_global()
        guild_value = await self.get_guild(guild)
        if channel:
            channel_value = await self.get_channel(channel)
        else:
            channel_value = 1000000
        return min(global_value, guild_value, channel_value)

    async def get_context_max(
        self, guild: discord.Guild, channel: discord.VoiceChannel = None
    ) -> Tuple[int, int, Optional[int]]:
        global_value = await self.get_global()
        guild_value = await self.get_guild(guild)
        if channel:
            channel_value = await self.get_channel(channel)
        else:
            channel_value = -1
        return global_value, guild_value, channel_value

    async def get_max_and_source(
        self, guild: discord.Guild, channel: discord.VoiceChannel = None
    ) -> Tuple[int, str]:
        global_value = await self.get_global()
        guild_value = await self.get_guild(guild)
        if channel:
            channel_value = await self.get_channel(channel)
        else:
            channel_value = -1

        mininum = min(global_value, guild_value, channel_value)
        restrictor = (
            "server"
            if mininum == guild_value
            else "channel"
            if mininum == channel_value
            else "global"
        )
        return mininum, restrictor

    def reset_globals(self) -> None:
        if None in self._cached_global:
            del self._cached_global[None]
