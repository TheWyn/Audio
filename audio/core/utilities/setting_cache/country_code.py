# Future Imports
from __future__ import annotations

# Standard Library Imports
from typing import Dict, Optional

# Dependency Imports
import discord

# Audio Imports
from .abc import CacheBase


class CountryCodeManager(CacheBase):
    __slots__ = (
        "_config",
        "bot",
        "enable_cache",
        "config_cache",
        "_cached_guild",
        "_cached_user",
        "_cached_global",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cached_global: Dict[None, str] = {}
        self._cached_user: Dict[int, Optional[str]] = {}
        self._cached_guild: Dict[int, str] = {}

    async def get_global(self) -> Optional[str]:
        ret: Optional[str]
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global[None]
        else:
            ret = await self._config.country_code()
            self._cached_global[None] = ret
        return ret

    async def set_global(self, set_to: str) -> None:
        if set_to is not None:
            await self._config.country_code.set(set_to)
            self._cached_global[None] = set_to
        else:
            await self._config.country_code.clear()
            self._cached_global[None] = self._config.defaults["GLOBAL"]["country_code"]

    async def get_user(self, user: discord.Member) -> Optional[str]:
        ret: Optional[str]
        uid: int = user.id
        if self.enable_cache and uid in self._cached_user:
            ret = self._cached_user[uid]
        else:
            ret = await self._config.user_from_id(uid).country_code()
            self._cached_user[uid] = ret
        return ret

    async def set_user(self, user: discord.Member, set_to: Optional[str]) -> None:
        uid: int = user.id
        if set_to is not None:
            await self._config.user_from_id(uid).country_code.set(set_to)
            self._cached_user[uid] = set_to
        else:
            await self._config.user_from_id(uid).country_code.clear()
            self._cached_user[uid] = self._config.defaults["USER"]["country_code"]

    async def get_guild(self, guild: discord.Guild) -> str:
        ret: str
        gid: int = guild.id
        if self.enable_cache and gid in self._cached_guild:
            ret = self._cached_guild[gid]
        else:
            ret = await self._config.guild_from_id(gid).country_code()
            self._cached_guild[gid] = ret
        return ret

    async def set_guild(self, guild: discord.Guild, set_to: Optional[str]) -> None:
        gid: int = guild.id
        if set_to:
            await self._config.guild_from_id(gid).country_code.set(set_to)
            self._cached_guild[gid] = set_to
        else:
            await self._config.guild_from_id(gid).ignored.clear()
            self._cached_guild[gid] = self._config.defaults["GUILD"]["country_code"]

    async def get_context_value(
        self,
        guild: discord.Guild,
        user: discord.Member,
    ) -> str:
        return await self.get_user(user) or await self.get_guild(guild) or await self.get_global()

    def reset_globals(self) -> None:
        self._cached_user = {}
        if None in self._cached_global:
            del self._cached_global[None]
