from __future__ import annotations

from typing import Dict, Optional, Tuple

import discord

from .abc import CacheBase


class LavalinkJarMetaManager(CacheBase):
    __slots__ = (
        "_config",
        "bot",
        "enable_cache",
        "config_cache",
        "_cached_global",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cached_build: Dict[None, int] = {}
        self._cache_url: Dict[None, str] = {}
        self._cache_stable: Dict[None, str] = {}

    async def get_global_stable(self) -> bool:
        ret: bool
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global[None]
        else:
            ret = await self._config.lavalink.jar.stable()
            self._cached_global[None] = ret
        return ret

    async def set_global_stable(self, set_to: Optional[bool]) -> None:
        if set_to is not None:
            await self._config.lavalink.jar.stable.set(set_to)
            self._cached_global[None] = set_to
        else:
            await self._config.lavalink.jar.stable.clear()
            self._cached_global[None] = self._config.defaults["GLOBAL"]["lavalink"]["jar"][
                "stable"
            ]

    async def get_global_build(self) -> Optional[int]:
        ret: int
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global[None]
        else:
            ret = await self._config.lavalink.jar.build()
            self._cached_global[None] = ret
        return ret

    async def set_global_build(self, set_to: Optional[int]) -> None:
        if set_to is not None:
            await self._config.lavalink.jar.build.set(set_to)
            self._cached_global[None] = set_to
        else:
            await self._config.lavalink.jar.build.clear()
            self._cached_global[None] = self._config.defaults["GLOBAL"]["lavalink"]["jar"]["build"]

    async def get_global_url(self) -> Optional[str]:
        ret: str
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global[None]
        else:
            ret = await self._config.lavalink.jar.url()
            self._cached_global[None] = ret
        return ret

    async def set_global_url(self, set_to: Optional[str]) -> None:
        if set_to is not None:
            await self._config.lavalink.jar.url.set(set_to)
            self._cached_global[None] = set_to
        else:
            await self._config.lavalink.jar.url.clear()
            self._cached_global[None] = self._config.defaults["GLOBAL"]["lavalink"]["jar"]["url"]

    async def get_context_value(self) -> Tuple[Optional[int], Optional[str], bool]:
        return (
            await self.get_global_build(),
            await self.get_global_url(),
            await self.get_global_stable(),
        )

    def reset_globals(self) -> None:
        if self._cache_url:
            del self._cache_url[None]
        if self._cached_build:
            del self._cached_build[None]
