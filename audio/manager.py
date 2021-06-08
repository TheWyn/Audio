# Future Imports
from __future__ import annotations

# Standard Library Imports
from typing import ClassVar, Final, List, Optional, Pattern, Tuple
import asyncio
import asyncio.subprocess  # disables for # https://github.com/PyCQA/pylint/issues/1469
import contextlib
import datetime
import itertools
import logging
import pathlib
import platform
import re
import shutil
import sys
import tempfile

# Dependency Imports
from tqdm import tqdm
import aiohttp
import yaml

try:
    # Dependency Imports
    from redbot import json
except ImportError:
    import json

# Dependency Imports
from redbot.core import data_manager

# Audio Imports
# Music  Imports
from .core.utilities import SettingCacheManager
from .errors import LavalinkDownloadFailed, ShouldAutoRecover
from .utils import task_callback

log = logging.getLogger("red.Music.manager")
JAR_VERSION: Final[str] = "3.3.2.5"
JAR_BUILD: Final[int] = 1250
LAVALINK_DOWNLOAD_URL: Final[str] = (
    "https://github.com/Drapersniper/Lavalink-Jars/releases/download/"
    f"{JAR_VERSION}_{JAR_BUILD}/"
    "Lavalink.jar"
)
LAVALINK_DOWNLOAD_DIR: Final[pathlib.Path] = data_manager.cog_data_path(raw_name="Music")
LAVALINK_JAR_FILE: Final[pathlib.Path] = LAVALINK_DOWNLOAD_DIR / "Lavalink.jar"
BUNDLED_APP_YML: Final[pathlib.Path] = pathlib.Path(__file__).parent / "data" / "application.yml"
LAVALINK_APP_YML: Final[pathlib.Path] = LAVALINK_DOWNLOAD_DIR / "application.yml"

_RE_READY_LINE: Final[Pattern] = re.compile(rb"Started Launcher in \S+ seconds")
_FAILED_TO_START: Final[Pattern] = re.compile(rb"Web server failed to start\. (.*)")
_RE_BUILD_LINE: Final[Pattern] = re.compile(rb"Build:\s+(?P<build>\d+)")

# Version regexes
#
# We expect the output to look something like:
#     $ java -version
#     ...
#     ... version "VERSION STRING HERE" ...
#     ...
#
# There are two version formats that we might get here:
#
# - Version scheme pre JEP 223 - used by Java 8 and older
#
# examples:
# 1.8.0
# 1.8.0_275
# 1.8.0_272-b10
# 1.8.0_202-internal-201903130451-b08
# 1.8.0_272-ea-202010231715-b10
# 1.8.0_272-ea-b10
#
# Implementation based on J2SE SDK/JRE Version String Naming Convention document:
# https://www.oracle.com/java/technologies/javase/versioning-naming.html
_RE_JAVA_VERSION_LINE_PRE223: Final[Pattern] = re.compile(
    r'version "1\.(?P<major>[0-8])\.(?P<minor>0)(?:_(?:\d+))?(?:-.*)?"'
)
# - Version scheme introduced by JEP 223 - used by Java 9 and newer
#
# examples:
# 11
# 11.0.9
# 11.0.9.1
# 11.0.9-ea
# 11.0.9-202011050024
#
# Implementation based on JEP 223 document:
# https://openjdk.java.net/jeps/223
_RE_JAVA_VERSION_LINE_223: Final[Pattern] = re.compile(
    r'version "(?P<major>\d+)(?:\.(?P<minor>\d+))?(?:\.\d+)*(\-[a-zA-Z0-9]+)?"'
)

LAVALINK_BRANCH_LINE: Final[Pattern] = re.compile(rb"Branch\s+(?P<branch>[\w\-\d_.]+)")
LAVALINK_JAVA_LINE: Final[Pattern] = re.compile(rb"JVM:\s+(?P<jvm>\d+[.\d+]*)")
LAVALINK_LAVAPLAYER_LINE: Final[Pattern] = re.compile(rb"Lavaplayer\s+(?P<lavaplayer>\d+[.\d+]*)")
LAVALINK_BUILD_TIME_LINE: Final[Pattern] = re.compile(rb"Build time:\s+(?P<build_time>\d+[.\d+]*)")
LAVALINK_JAR_ENDPOINT: Final[
    str
] = "https://api.github.com/repos/Drapersniper/Lavalink-Jars/releases"


async def get_latest_lavalink_release(stable=True, date=False):
    async with aiohttp.ClientSession(json_serialize=json.dumps) as session:
        async with session.get(LAVALINK_JAR_ENDPOINT) as resp:
            if resp.status != 200:
                return "", "0_0", "0", None
            data = await resp.json(loads=json.loads)
            if stable:
                data = list(
                    filter(lambda d: d["prerelease"] is False and d["draft"] is False, data)
                )
            data = sorted(data, key=lambda k: k["published_at"], reverse=True)[0] or {}
            output = (
                data.get("name"),
                data.get("tag_name"),
                next(
                    (
                        i.get("browser_download_url")
                        for i in data.get("assets", [])
                        if i.get("name") == "Lavalink.jar"
                    ),
                    None,
                ),
                None,
            )
            if not date:
                return output
            else:
                return (
                    output[0],
                    output[1],
                    output[2],
                    data.get("published_at", datetime.datetime.now()),
                )


class ServerManager:

    _java_available: ClassVar[Optional[bool]] = None
    _java_version: ClassVar[Optional[Tuple[int, int]]] = None
    _up_to_date: ClassVar[Optional[bool]] = None
    _blacklisted_archs: List[str] = []
    _jar_build: ClassVar[int] = JAR_BUILD
    _jar_version: ClassVar[str] = JAR_VERSION
    _jar_name: ClassVar[str] = f"{JAR_VERSION}_{JAR_BUILD}"
    _jar_download_url: ClassVar[str] = LAVALINK_DOWNLOAD_URL

    _lavaplayer: ClassVar[str] = "Unknown"
    _lavalink_build: ClassVar[int] = "Unknown"
    _jvm: ClassVar[str] = "Unknown"
    _lavalink_branch: ClassVar[str] = "Unknown"
    _buildtime: ClassVar[str] = "Unknown"
    _java_exc: ClassVar[str] = "java"

    def __init__(self, host: str, password: str, port: int, cache: SettingCacheManager) -> None:
        self.ready: asyncio.Event = asyncio.Event()
        self._port = port
        self._host = host
        self._password = password
        self.config_cache = cache
        self._proc: Optional[asyncio.subprocess.Process] = None  # pylint:disable=no-member
        self._monitor_task: Optional[asyncio.Task] = None
        self._shutdown: bool = False

    @property
    def path(self) -> Optional[str]:
        return self._java_exc

    @property
    def jvm(self) -> Optional[str]:
        return self._jvm

    @property
    def lavaplayer(self) -> Optional[str]:
        return self._lavaplayer

    @property
    def ll_build(self) -> Optional[int]:
        return self._lavalink_build

    @property
    def ll_branch(self) -> Optional[str]:
        return self._lavalink_branch

    @property
    def build_time(self) -> Optional[str]:
        return self._buildtime

    async def start(self, java_path: str) -> None:
        arch_name = platform.machine()
        self._java_exc = java_path
        if arch_name in self._blacklisted_archs:
            raise asyncio.CancelledError(
                "You are attempting to run a Lavalink node on an unsupported machine architecture."
            )

        if (jar_url := await self.config_cache.managed_lavalink_meta.get_global_url()) is not None:
            self._jar_name = jar_url
            self._jar_download_url = jar_url
            self._jar_build = (
                await self.config_cache.managed_lavalink_meta.get_global_build() or self._jar_build
            )
        else:
            if await self.config_cache.managed_lavalink_server_auto_update.get_global():
                with contextlib.suppress(Exception):
                    name, tag, url, _nothing = await get_latest_lavalink_release()
                    if name and "_" in name:
                        tag = name
                        version, build = name.split("_")
                        build = int(build)
                    elif tag and "_" in tag:
                        name = tag
                        version, build = name.split("_")
                        build = int(build)
                    else:
                        name = tag = version = build = None
                    self._jar_name = name or tag or self._jar_name
                    self._jar_download_url = url or self._jar_download_url
                    self._jar_build = build or self._jar_build
                    self._jar_version = version or self._jar_version

        if self._proc is not None:
            if self._proc.returncode is None:
                raise RuntimeError("Managed node is already running")
            elif self._shutdown:
                raise RuntimeError("Node manager has already been used - create another one")

        await self.maybe_download_jar()

        await self.process_settings()

        args = await self._get_jar_args()
        self._proc = await asyncio.subprocess.create_subprocess_exec(  # pylint:disable=no-member
            *args,
            cwd=str(LAVALINK_DOWNLOAD_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        log.info("Managed node started. PID: %s", self._proc.pid)

        try:
            await asyncio.wait_for(self._wait_for_launcher(), timeout=120)
        except asyncio.TimeoutError:
            log.warning("Timeout occurred whilst waiting for managed node to be ready")

        self._monitor_task = asyncio.create_task(self._monitor())
        self._monitor_task.add_done_callback(task_callback)

    async def _get_jar_args(self) -> List[bytes]:
        (java_available, java_version) = await self._has_java()

        if not java_available:
            raise RuntimeError("You must install Java 11 or 13 for Lavalink to run.")
        args = [
            self._java_exc,
            "-Djdk.tls.client.protocols=TLSv1.2" if (11, 0) <= java_version < (12, 0) else None,
            "-jar",
            str(LAVALINK_JAR_FILE),
        ]
        return list(filter(None, args))

    async def _has_java(self) -> Tuple[bool, Optional[Tuple[int, int]]]:
        if self._java_available is not None:
            # Return cached value if we've checked this before
            return self._java_available, self._java_version
        java_exec = shutil.which(self._java_exc)
        java_available = java_exec is not None
        if not java_available:
            self.java_available = False
            self.java_version = None
        else:
            self._java_exc = java_exec
            self._java_version = version = await self._get_java_version()
            self._java_available = (11, 0) <= version < (12, 0) or (13, 0) <= version < (14, 0)
        return self._java_available, self._java_version

    async def _get_java_version(self) -> Tuple[int, int]:
        """This assumes we've already checked that java exists."""
        _proc: asyncio.subprocess.Process = (
            await asyncio.create_subprocess_exec(  # pylint:disable=no-member
                self._java_exc,
                "-version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        )
        # java -version outputs to stderr
        _, err = await _proc.communicate()

        version_info: str = err.decode("utf-8")
        lines = version_info.splitlines()
        for line in lines:
            match = _RE_JAVA_VERSION_LINE_PRE223.search(line)
            if match is None:
                match = _RE_JAVA_VERSION_LINE_223.search(line)
            if match is None:
                continue
            major = int(match["major"])
            minor = 0
            if minor_str := match["minor"]:
                minor = int(minor_str)

            return major, minor

        raise RuntimeError(f"The output of `{self._java_exc} -version` was unexpected.")

    async def process_settings(self):
        # Copy the application.yml across.
        try:
            with open(BUNDLED_APP_YML, "r") as f:
                data = yaml.safe_load(f)
            data["lavalink"]["server"][
                "jdanas"
            ] = await self.config_cache.managed_lavalink_yaml.get_jda_nsa()
            data["lavalink"]["server"][
                "bufferDurationMs"
            ] = await self.config_cache.managed_lavalink_yaml.get_lavalink_buffer()
            data["lavalink"]["server"][
                "playerUpdateInterval"
            ] = await self.config_cache.managed_lavalink_yaml.get_lavalink_update_intervals()
            data["lavalink"]["server"][
                "youtubeSearchEnabled"
            ] = await self.config_cache.managed_lavalink_yaml.get_lavalink_ytsearch()
            data["lavalink"]["server"][
                "soundcloudSearchEnabled"
            ] = await self.config_cache.managed_lavalink_yaml.get_lavalink_scsearch()
            data["lavalink"]["server"]["sources"][
                "http"
            ] = await self.config_cache.managed_lavalink_yaml.get_source_http()
            data["lavalink"]["server"]["sources"][
                "local"
            ] = await self.config_cache.managed_lavalink_yaml.get_source_local()
            data["lavalink"]["server"]["sources"][
                "bandcamp"
            ] = await self.config_cache.managed_lavalink_yaml.get_source_bandcamp()
            data["lavalink"]["server"]["sources"][
                "soundcloud"
            ] = await self.config_cache.managed_lavalink_yaml.get_source_soundcloud()
            data["lavalink"]["server"]["sources"][
                "twitch"
            ] = await self.config_cache.managed_lavalink_yaml.get_source_twitch()
            data["lavalink"]["server"]["sources"][
                "youtube"
            ] = await self.config_cache.managed_lavalink_yaml.get_source_youtube()

            data["lavalink"]["server"][
                "password"
            ] = await self.config_cache.managed_lavalink_yaml.get_lavalink_password()
            data["server"][
                "address"
            ] = await self.config_cache.managed_lavalink_yaml.get_server_address()
            data["server"][
                "port"
            ] = await self.config_cache.managed_lavalink_yaml.get_server_port()

            with open(LAVALINK_APP_YML, "w") as f:
                yaml.safe_dump(data, f)
        except Exception:
            raise RuntimeError("The value provided for the setting YAML is incorrect.")

    async def _wait_for_launcher(self) -> None:
        log.debug("Waiting for managed node to be ready")
        ready = False
        for i in itertools.cycle(range(50)):
            line = await self._proc.stdout.readline()
            if _RE_READY_LINE.search(line):
                self.ready.set()
                ready = True
                break
            if _FAILED_TO_START.search(line):
                if b"Port 2333 was already in use" in line:
                    log.warning("Unable to start managed node; Port 2333 is already in use.")
                    raise ShouldAutoRecover
                raise RuntimeError(
                    "Managed Lavalink node failed to start: %s", line.decode().strip()
                )
            if self._proc.returncode is not None:
                # Avoid Console spam only print once every 2 seconds
                ready = False
            if i == 49:
                # Sleep after 50 lines to prevent busylooping
                await asyncio.sleep(0.1)

        if self._proc.returncode == 1:
            raise RuntimeError("Managed node failed to start: Node exited with error code 1.")
        if not ready:
            log.critical("Managed node exited early")
        if self.ready.is_set():
            log.info(
                "Managed node is ready to accept connections on: %s:%s",
                self._host,
                self._port,
            )

    async def _monitor(self) -> None:
        while self._proc.returncode is None:
            await asyncio.sleep(0.5)

        # This task hasn't been cancelled - Lavalink was shut down by something else
        log.info("Managed Lavalink jar shutdown unexpectedly")
        if not self._has_java_error():
            log.info("Restarting managed node")
            await self.start(self._java_exc)
        else:
            log.critical(
                "Your Java install is broken. Please find the hs_err_pid%d.log file"
                " in the Audio data folder and report this issue.",
                self._proc.pid,
            )

    def _has_java_error(self) -> bool:
        poss_error_file = LAVALINK_DOWNLOAD_DIR / "hs_err_pid{}.log".format(self._proc.pid)
        return poss_error_file.exists()

    async def shutdown(self) -> None:
        if self._shutdown is True or self._proc is None:
            # For convenience, calling this method more than once or calling it before starting it
            # does nothing.
            return
        log.info("Shutting down managed node")
        if self._monitor_task is not None:
            self._monitor_task.cancel()
        if not self._proc.returncode:
            self._proc.terminate()
        await self._proc.wait()
        self._shutdown = True

    async def _download_jar(self) -> None:
        log.info("Downloading Lavalink.jar...")
        async with aiohttp.ClientSession(json_serialize=json.dumps) as session:
            async with session.get(self._jar_download_url) as response:
                if response.status == 404:
                    # A 404 means our LAVALINK_DOWNLOAD_URL is invalid, so likely the jar version
                    # hasn't been published yet
                    raise LavalinkDownloadFailed(
                        f"Lavalink server version {self._jar_version}_{self._jar_build} "
                        "hasn't been published yet",
                        response=response,
                        should_retry=False,
                    )
                elif 400 <= response.status < 600:
                    # Other bad responses should be raised but we should retry just incase
                    raise LavalinkDownloadFailed(response=response, should_retry=True)
                fd, path = tempfile.mkstemp()
                file = open(fd, "wb")
                nbytes = 0
                with tqdm(
                    desc="Lavalink.jar",
                    total=response.content_length,
                    file=sys.stdout,
                    unit="B",
                    unit_scale=True,
                    miniters=1,
                    dynamic_ncols=True,
                    leave=False,
                ) as progress_bar:
                    try:
                        chunk = await response.content.read(1024)
                        while chunk:
                            chunk_size = file.write(chunk)
                            nbytes += chunk_size
                            progress_bar.update(chunk_size)
                            chunk = await response.content.read(1024)
                        file.flush()
                    finally:
                        file.close()

                shutil.move(path, str(LAVALINK_JAR_FILE), copy_function=shutil.copyfile)

        log.info("Successfully downloaded Lavalink.jar (%s bytes written)", format(nbytes, ","))
        await self._is_up_to_date()

    async def _is_up_to_date(self):
        if self._up_to_date is True:
            # Return cached value if we've checked this before
            return True
        args = await self._get_jar_args()
        args.append(b"--version")
        _proc = await asyncio.subprocess.create_subprocess_exec(  # pylint:disable=no-member
            *args,
            cwd=str(LAVALINK_DOWNLOAD_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout = (await _proc.communicate())[0]
        if (build := _RE_BUILD_LINE.search(stdout)) is None:
            # Output is unexpected, suspect corrupted jarfile
            return False
        else:
            build = int(build["build"])
            self._lavalink_build = build

        if (branch := LAVALINK_BRANCH_LINE.search(stdout)) is None:
            # Output is unexpected, suspect corrupted jarfile
            return False
        else:
            self._lavalink_branch = branch["branch"].decode()
        if (java := LAVALINK_JAVA_LINE.search(stdout)) is None:
            # Output is unexpected, suspect corrupted jarfile
            return False
        else:
            self._jvm = java["jvm"].decode()

        if (lavaplayer := LAVALINK_LAVAPLAYER_LINE.search(stdout)) is None:
            # Output is unexpected, suspect corrupted jarfile
            return False
        else:
            self._lavaplayer = lavaplayer["lavaplayer"].decode()

        if (buildtime := LAVALINK_BUILD_TIME_LINE.search(stdout)) is None:
            # Output is unexpected, suspect corrupted jarfile
            return False
        else:
            date = buildtime["build_time"].decode()
            date = date.replace(".", "/")
            self._buildtime = date
        self._up_to_date = self._lavalink_build >= self._jar_build
        return self._up_to_date

    async def maybe_download_jar(self):
        if not (LAVALINK_JAR_FILE.exists() and await self._is_up_to_date()):
            await self._download_jar()
            if not await self._is_up_to_date():
                raise LavalinkDownloadFailed(
                    f"Download of Lavalink build {self.ll_build} from {self.ll_branch} "
                    f"({self._jar_download_url}) failed, Expected build {self._jar_build} "
                    f"But downloaded {self._lavalink_build}",
                    response=None,
                    should_retry=False,
                )
