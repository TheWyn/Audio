import asyncio
import datetime
from collections import Counter, defaultdict
from typing import Mapping

import aiohttp
import discord

try:
    from redbot import json
except ImportError:
    import json

from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.commands import Cog
from redbot.core.data_manager import cog_data_path

from ..utils import PlaylistScope
from . import commands, events, tasks, utilities
from .cog_utils import CompositeMetaClass

_ = lambda s: s


class Audio(
    commands.Commands,
    events.Events,
    tasks.Tasks,
    utilities.Utilities,
    Cog,
    metaclass=CompositeMetaClass,
):
    """Play audio through voice channels."""

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, 2711759130, force_registration=True)
        self.config_cache = utilities.setting_cache.SettingCacheManager(
            self.bot, self.config, True
        )

        self.api_interface = None
        self.player_manager = None
        self.playlist_api = None
        self.local_folder_current_path = None
        self.db_conn = None

        self._error_counter = Counter()
        self._error_timer = {}
        self._disconnected_players = {}
        self.skip_votes = {}
        self.play_lock = {}

        self.lavalink_connect_task = None
        self._restore_task = None
        self.player_automated_timer_task = None
        self.cog_cleaned_up = False
        self.lavalink_connection_aborted = False
        self.permission_cache = discord.Permissions(
            embed_links=True,
            read_messages=True,
            send_messages=True,
            read_message_history=True,
            add_reactions=True,
        )

        self.session = aiohttp.ClientSession(json_serialize=json.dumps)
        self.cog_ready_event = asyncio.Event()
        self._ws_resume = defaultdict(asyncio.Event)
        self._ws_op_codes = defaultdict(asyncio.LifoQueue)

        self.cog_init_task = None
        self.global_api_user = {
            "fetched": False,
            "can_read": False,
            "can_post": False,
            "can_delete": False,
        }
        self._ll_guild_updates = set()
        self._diconnected_shard = set()
        self._last_ll_update = datetime.datetime.now(datetime.timezone.utc)

        default_cog_lavalink_settings = {
            "primary": {
                "host": "http://localhost",
                "port": 2333,
                "rest_uri": "http://localhost:2333",
                "password": "youshallnotpass",
                "identifier": "primary",
                "region": "",
                "shard_id": -1,
                "search_only": False,
            }
        }
        lavalink_yaml = dict(lavalink={"server": {"sources": {}}}, server={})
        lavalink_yaml["lavalink"]["server"]["jdanas"] = True
        lavalink_yaml["lavalink"]["server"]["sources"]["http"] = True
        lavalink_yaml["lavalink"]["server"]["sources"]["local"] = True
        lavalink_yaml["lavalink"]["server"]["sources"]["bandcamp"] = True
        lavalink_yaml["lavalink"]["server"]["sources"]["soundcloud"] = True
        lavalink_yaml["lavalink"]["server"]["sources"]["twitch"] = True
        lavalink_yaml["lavalink"]["server"]["sources"]["youtube"] = True
        lavalink_yaml["lavalink"]["server"]["bufferDurationMs"] = 300
        lavalink_yaml["lavalink"]["server"]["playerUpdateInterval"] = 1
        lavalink_yaml["lavalink"]["server"]["youtubeSearchEnabled"] = True
        lavalink_yaml["lavalink"]["server"]["soundcloudSearchEnabled"] = True
        lavalink_yaml["lavalink"]["server"]["password"] = default_cog_lavalink_settings["primary"][
            "password"
        ]
        lavalink_yaml["server"]["address"] = default_cog_lavalink_settings["primary"]["host"]
        lavalink_yaml["server"]["port"] = default_cog_lavalink_settings["primary"]["port"]

        default_global = dict(
            schema_version=1,
            bundled_playlist_version=0,
            owner_notification=0,
            cache_level=0,
            cache_age=365,
            auto_deafen=True,
            daily_playlists=False,
            daily_playlists_override=False,
            global_db_enabled=True,
            global_db_get_timeout=5,
            status=False,
            restrict=True,
            localpath=str(cog_data_path(raw_name="Audio")),
            url_keyword_blacklist=[],
            url_keyword_whitelist=[],
            java_exc_path="java",
            volume=499,
            disconnect=False,
            persist_queue=None,
            emptydc_enabled=False,
            emptydc_timer=0,
            emptypause_enabled=False,
            emptypause_timer=0,
            thumbnail=None,
            maxlength=0,
            vc_restricted=False,
            jukebox=False,
            jukebox_price=0,
            country_code="US",
            prefer_lyrics=False,
            max_queue_size=10_000,
            notify=True,
            lavalink__jar__url=None,
            lavalink__jar__build=None,
            lavalink__managed=True,
            lavalink__autoupdate=False,
            lavalink__jar__stable=True,
            lavalink__nodes=default_cog_lavalink_settings,
            lavalink__managed_yaml=lavalink_yaml,
        )

        default_guild = dict(
            auto_play=False,
            currently_auto_playing_in=[],
            auto_deafen=True,
            autoplaylist=dict(
                enabled=True,
                id=42069,
                name="Aikaterna's curated tracks",
                scope=PlaylistScope.GLOBAL.value,
            ),
            persist_queue=True,
            disconnect=False,
            dj_enabled=False,
            dj_roles=[],
            daily_playlists=False,
            emptydc_enabled=False,
            emptydc_timer=0,
            emptypause_enabled=False,
            emptypause_timer=0,
            jukebox=False,
            restrict=True,
            jukebox_price=0,
            maxlength=0,
            notify=False,
            prefer_lyrics=False,
            repeat=False,
            shuffle=False,
            shuffle_bumped=True,
            thumbnail=False,
            volume=100,
            vote_enabled=False,
            vote_percent=51,
            max_queue_size=20_000,
            room_lock=None,
            url_keyword_blacklist=[],
            url_keyword_whitelist=[],
            country_code=None,
            vc_restricted=False,
            whitelisted_text=[],
            whitelisted_vc=[],
        )
        default_channel = dict(
            volume=100,
        )
        _playlist: Mapping = dict(id=None, author=None, name=None, playlist_url=None, tracks=[])

        self.config.init_custom("EQUALIZER", 1)
        self.config.register_custom("EQUALIZER", name="Default", eq_bands=[], eq_presets={})
        self.config.init_custom(PlaylistScope.GLOBAL.value, 1)
        self.config.register_custom(PlaylistScope.GLOBAL.value, **_playlist)
        self.config.init_custom(PlaylistScope.GUILD.value, 2)
        self.config.register_custom(PlaylistScope.GUILD.value, **_playlist)
        self.config.init_custom(PlaylistScope.USER.value, 2)
        self.config.register_custom(PlaylistScope.USER.value, **_playlist)
        self.config.register_guild(**default_guild)
        self.config.register_global(**default_global)
        self.config.register_channel(**default_channel)
        self.config.register_user(country_code=None)
