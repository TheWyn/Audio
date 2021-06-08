# Future Imports
from __future__ import annotations

# Standard Library Imports
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

# Dependency Imports
from redbot.core import Config
from redbot.core.bot import Red

if TYPE_CHECKING:

    # Music Imports
    from . import SettingCacheManager


class CacheBase(ABC):
    _config: Config
    bot: Red
    enable_cache: bool
    config_cache: SettingCacheManager

    def __init__(self, bot: Red, config: Config, enable_cache: bool, cache: SettingCacheManager):
        self._config = config
        self.bot = bot
        self.enable_cache = enable_cache
        self.config_cache = cache

    @abstractmethod
    async def get_context_value(self, *args, **kwargs):
        raise NotImplementedError()

    def reset_globals(self) -> None:
        pass
