from redbot import VersionInfo

from .hash import version

COMMIT = version

VERSION = VersionInfo.from_json(
    {"major": 3, "minor": 0, "micro": 0, "releaselevel": "alpha", "serial": 2}
)


__version__ = f"{VERSION}-{COMMIT}"
