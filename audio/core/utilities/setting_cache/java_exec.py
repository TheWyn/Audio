# Future Imports
from __future__ import annotations

# Standard Library Imports
from pathlib import Path
from typing import Dict, Optional

# Dependency Imports
import discord

# Audio Imports
# Music  Imports
from .abc import CacheBase


class JavaExecPathManager(CacheBase):
    __slots__ = (
        "_config",
        "bot",
        "enable_cache",
        "config_cache",
        "_cached_global",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cached_global: Dict[None, str] = {}

    async def get_global(self) -> str:
        ret: str
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global[None]
        else:
            ret = await self._config.java_exc_path()
            self._cached_global[None] = ret
        return ret

    async def set_global(self, set_to: Optional[Path]) -> None:
        gid = None
        if set_to is not None:
            set_to = str(set_to.absolute())
            await self._config.java_exc_path.set(set_to)
            self._cached_global[gid] = set_to
        else:
            await self._config.java_exc_path.clear()
            self._cached_global[gid] = self._config.defaults["GLOBAL"]["java_exc_path"]

    async def get_context_value(self, guild: discord.Guild = None) -> str:
        return await self.get_global()

    def reset_globals(self) -> None:
        if None in self._cached_global:
            del self._cached_global[None]
