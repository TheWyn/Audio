# Future Imports
from __future__ import annotations

# Standard Library Imports
import logging

# Music Imports
from ..cog_utils import CompositeMetaClass
from .cog import AudioEvents
from .dpy import DpyEvents
from .lavalink import LavalinkEvents
from .red import RedEvents

log = logging.getLogger("red.cogs.Music.cog.Events")


class Events(AudioEvents, DpyEvents, LavalinkEvents, RedEvents, metaclass=CompositeMetaClass):
    """Class joining all event subclasses"""
