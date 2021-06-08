# Future Imports
from __future__ import annotations

# Standard Library Imports
from abc import ABC
from base64 import b64decode
from io import BytesIO
from typing import Final
import struct

# Dependency Imports
from redbot.core import commands
from redbot.core.i18n import Translator

# Audio Imports
from ..__version__ import __version__  # noqa: F401
from ..converters import get_lazy_converter, get_lazy_multiline_converter, get_playlist_converter

__author__ = ["aikaterna", "Draper"]

_SCHEMA_VERSION: Final[int] = 7
_OWNER_NOTIFICATION: Final[int] = 1

LazyGreedyConverter = get_lazy_converter("--")
LazyMultilineConverter = get_lazy_multiline_converter("--")
PlaylistConverter = get_playlist_converter()
T_ = Translator("Audio", __file__)

HUMANIZED_PERM = {
    "create_instant_invite": "Create Instant Invite",
    "kick_members": "Kick Members",
    "ban_members": "Ban Members",
    "administrator": "Administrator",
    "manage_channels": "Manage Channels",
    "manage_guild": "Manage Server",
    "add_reactions": "Add Reactions",
    "view_audit_log": "View Audit Log",
    "priority_speaker": "Priority Speaker",
    "stream": "Go Live",
    "read_messages": "Read Text Channels & See Voice Channels",
    "send_messages": "Send Messages",
    "send_tts_messages": "Send TTS Messages",
    "manage_messages": "Manage Messages",
    "embed_links": "Embed Links",
    "attach_files": "Attach Files",
    "read_message_history": "Read Message History",
    "mention_everyone": "Mention @everyone, @here, and All Roles",
    "external_emojis": "Use External Emojis",
    "view_guild_insights": "View Server Insights",
    "connect": "Connect",
    "speak": "Speak",
    "mute_members": "Mute Members",
    "deafen_members": "Deafen Members",
    "move_members": "Move Members",
    "use_voice_activation": "Use Voice Activity",
    "change_nickname": "Change Nickname",
    "manage_nicknames": "Manage Nicknames",
    "manage_roles": "Manage Roles",
    "manage_webhooks": "Manage Webhooks",
    "manage_emojis": "Manage Emojis",
    "use_slash_commands": "Use Slash Commands",
    "request_to_speak": "Request To Speak",
}
ENABLED = "enabled"
DISABLED = "disabled"
ENABLED_TITLE = "Enabled"
DISABLED_TITLE = "Disabled"

_ = T_


class CompositeMetaClass(type(commands.Cog), type(ABC)):
    """
    This allows the metaclass used for proper type detection to
    coexist with discord.py's metaclass
    """


# Both DataReader and DataWriter are taken from
# https://github.com/Devoxin/Lavalink.py/blob/master/lavalink/datarw.py
# These are licenced under MIT, Thanks Devoxin for putting these together!
# The license can be found in https://github.com/Devoxin/Lavalink.py/blob/master/LICENSE


class DataReader:
    def __init__(self, ts):
        self._buf = BytesIO(b64decode(ts))

    def _read(self, n):
        return self._buf.read(n)

    def read_byte(self):
        return self._read(1)

    def read_boolean(self):
        (result,) = struct.unpack("B", self.read_byte())
        return result != 0

    def read_unsigned_short(self):
        (result,) = struct.unpack(">H", self._read(2))
        return result

    def read_int(self):
        (result,) = struct.unpack(">i", self._read(4))
        return result

    def read_long(self):
        (result,) = struct.unpack(">Q", self._read(8))
        return result

    def read_utf(self):
        text_length = self.read_unsigned_short()
        return self._read(text_length)


class DataWriter:
    def __init__(self):
        self._buf = BytesIO()

    def _write(self, data):
        self._buf.write(data)

    def write_byte(self, byte):
        self._buf.write(byte)

    def write_boolean(self, boolean):
        enc = struct.pack("B", 1 if boolean else 0)
        self.write_byte(enc)

    def write_unsigned_short(self, short):
        enc = struct.pack(">H", short)
        self._write(enc)

    def write_int(self, integer):
        enc = struct.pack(">i", integer)
        self._write(enc)

    def write_long(self, long):
        enc = struct.pack(">Q", long)
        self._write(enc)

    def write_utf(self, string):
        utf = string.encode("utf8")
        byte_len = len(utf)

        if byte_len > 65535:
            raise OverflowError("UTF string may not exceed 65535 bytes!")

        self.write_unsigned_short(byte_len)
        self._write(utf)

    def finish(self):
        with BytesIO() as track_buf:
            byte_len = self._buf.getbuffer().nbytes
            flags = byte_len | (1 << 30)
            enc_flags = struct.pack(">i", flags)
            track_buf.write(enc_flags)

            self._buf.seek(0)
            track_buf.write(self._buf.read())
            self._buf.close()

            track_buf.seek(0)
            return track_buf.read()
