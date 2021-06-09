# Future Imports
from __future__ import annotations

# Standard Library Imports
from abc import ABC
from typing import Tuple

# Dependency Imports
from bs4 import BeautifulSoup
from requests_futures.sessions import FuturesSession

try:
    # Dependency Imports
    from redbot import json
except ImportError:
    import json

# Music Imports
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass


class LyricUtilities(MixinMeta, ABC, metaclass=CompositeMetaClass):
    """Base class to hold all Lyric utility methods"""

    @staticmethod
    async def get_lyrics_string(artist_song: str) -> Tuple[str, str, str, str]:
        percents = {
            " ": "+",
            "!": "%21",
            '"': "%22",
            "#": "%23",
            "$": "%24",
            "%": "%25",
            "&": "%26",
            "'": "%27",
            "(": "%28",
            ")": "%29",
            "*": "%2A",
            "+": "%2B",
            "`": "%60",
            ",": "%2C",
            "-": "%2D",
            ".": "%2E",
            "/": "%2F",
        }
        searchquery = ""
        for char in artist_song:
            if char in percents:
                char = percents[char]
            searchquery += char
        session = FuturesSession()
        future = session.get("https://google.com/search?q=" + searchquery + "+lyrics")
        response_one = future.result()
        soup = BeautifulSoup(response_one.text, "html.parser")
        bouncer = "Our systems have detected unusual traffic from your computer network"
        if bouncer in soup.get_text():
            title_ = ""
            artist_ = ""
            lyrics_ = "Unable to get lyrics right now. Try again later."
            source_ = ""
        else:
            try:
                title_ = soup.find("span", class_="BNeawe tAd8D AP7Wnd").get_text()
                artist_ = soup.find_all("span", class_="BNeawe s3v9rd AP7Wnd")[-1].get_text()
                lyrics_ = soup.find_all("div", class_="BNeawe tAd8D AP7Wnd")[-1].get_text()
                source_ = soup.find_all("span", class_="uEec3 AP7Wnd")[-1].get_text()
            except AttributeError:
                title_, artist_, lyrics_, source_ = (
                    "",
                    "",
                    f"Not able to find the lyrics for {artist_song}.",
                    "",
                )
        return title_, artist_, lyrics_, source_
