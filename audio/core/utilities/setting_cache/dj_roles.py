# Future Imports
from __future__ import annotations

# Standard Library Imports
from collections import defaultdict
from typing import Dict, Optional, Set

# Dependency Imports
import discord

# Audio Imports
from .abc import CacheBase


class DJRoleManager(CacheBase):
    __slots__ = (
        "_config",
        "bot",
        "enable_cache",
        "config_cache",
        "_cached_guild",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cached_guild: Dict[Optional[int], Set[int]] = defaultdict(set)

    async def get_guild(self, guild: discord.Guild) -> Set[discord.Role]:
        ret: Set[int]
        gid: int = guild.id
        if self.enable_cache and gid in self._cached_guild:
            ret = self._cached_guild[gid].copy()
        else:
            ret = await self._config.guild_from_id(gid).dj_roles()
            self._cached_guild[gid] = ret.copy()
        return {y for r in ret if (y := guild.get_role(r)) in guild.roles}

    async def get_allowed_members(self, guild: discord.Guild) -> Set[discord.Member]:
        members = {member for m in self.bot.owner_ids if (member := guild.get_member(m))}
        if await self.config_cache.dj_status.get_context_value(guild):
            members |= {member for role in await self.get_guild(guild) for member in role.members}
        return members

    async def get_allowed_member_ids(self, guild: discord.Guild) -> Set[int]:
        member_ids = {*self.bot.owner_ids}
        if await self.config_cache.dj_status.get_context_value(guild):
            member_ids |= {
                member.id for role in await self.get_guild(guild) for member in role.members
            }
        return member_ids

    async def member_is_dj(self, guild: discord.Guild, member: discord.Member) -> bool:
        return member in await self.get_allowed_members(guild)

    async def set_guild(
        self, guild: discord.Guild, roles: Optional[Set[discord.Role]] = None
    ) -> None:
        gid: int = guild.id
        roles = roles or set()
        assert isinstance(roles, set)
        if not isinstance(roles, set) and any(not isinstance(r, discord.Role) for r in roles):
            raise TypeError("Roles must be a set of discord.Role objects")
        roles_ids = {y.id for r in roles if (y := guild.get_role(r.id)) in guild.roles}
        self._cached_guild[gid] = roles_ids
        await self._config.guild_from_id(gid).dj_roles.set(list(roles_ids))

    async def add_guild(self, guild: discord.Guild, roles: Set[discord.Role]) -> None:
        gid: int = guild.id
        assert isinstance(roles, set)
        if not isinstance(roles, set) and any(not isinstance(r, discord.Role) for r in roles):
            raise TypeError("Roles must be a set of discord.Role objects")
        roles = set(sorted(roles, reverse=True))
        roles = {y.id for r in roles if (y := guild.get_role(r.id)) in guild.roles}
        roles.update(self._cached_guild[gid])
        self._cached_guild[gid] = roles
        await self._config.guild_from_id(gid).dj_roles.set(list(roles))

    async def clear_guild(self, guild: discord.Guild) -> None:
        gid: int = guild.id
        self._cached_guild[gid] = set()
        await self._config.guild_from_id(gid).dj_roles.clear()

    async def remove_guild(self, guild: discord.Guild, roles: Set[discord.Role]) -> None:
        gid: int = guild.id
        if not isinstance(roles, set) or any(not isinstance(r, discord.Role) for r in roles):
            raise TypeError("Roles must be a set of discord.Role objects")
        if gid not in self._cached_guild:
            self._cached_guild[gid] = await self._config.guild_from_id(gid).dj_roles()
        for role in roles:
            role = role.id
            if role in self._cached_guild[gid]:
                self._cached_guild[gid].remove(role)
                async with self._config.guild_from_id(gid).dj_roles() as curr_list:
                    curr_list.remove(role)

    async def get_context_value(self, guild: discord.Guild) -> Set[discord.Role]:
        return await self.get_guild(guild)

    def reset_globals(self) -> None:
        pass
