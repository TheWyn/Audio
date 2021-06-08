# Future Imports
from __future__ import annotations

# Standard Library Imports
from typing import Dict, Optional

# Dependency Imports
import discord

# Audio Imports
from .abc import CacheBase


class URLRestrictManager(CacheBase):
    __slots__ = (
        "_config",
        "bot",
        "enable_cache",
        "config_cache",
        "_cached_guild",
        "_cached_global",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cached_global: Dict[None, bool] = {}
        self._cached_guild: Dict[int, bool] = {}

    async def get_guild(self, guild: discord.Guild) -> bool:
        ret: bool
        gid: int = guild.id
        if self.enable_cache and gid in self._cached_guild:
            ret = self._cached_guild[gid]
        else:
            ret = await self._config.guild_from_id(gid).restrict()
            self._cached_guild[gid] = ret
        return ret

    async def set_guild(self, guild: discord.Guild, set_to: Optional[bool]) -> None:
        gid: int = guild.id
        if set_to is not None:
            await self._config.guild_from_id(gid).restrict.set(set_to)
            self._cached_guild[gid] = set_to
        else:
            await self._config.guild_from_id(gid).restrict.clear()
            self._cached_guild[gid] = self._config.defaults["GUILD"]["restrict"]

    async def get_global(self) -> bool:
        ret: bool
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global[None]
        else:
            ret = await self._config.restrict()
            self._cached_global[None] = ret
        return ret

    async def set_global(self, set_to: Optional[bool]) -> None:
        if set_to is not None:
            await self._config.restrict.set(set_to)
            self._cached_global[None] = set_to
        else:
            await self._config.restrict.clear()
            self._cached_global[None] = self._config.defaults["GLOBAL"]["restrict"]

    async def get_context_value(self, guild: discord.Guild = None) -> bool:
        if (value := await self.get_global()) is True:
            return value
        return await self.get_guild(guild)

    def reset_globals(self) -> None:
        if None in self._cached_global:
            del self._cached_global[None]
