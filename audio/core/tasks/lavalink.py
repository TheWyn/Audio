import asyncio
import logging

import lavalink
from redbot.core import data_manager

from ...errors import LavalinkDownloadFailed, ShouldAutoRecover
from ...manager import ServerManager
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = logging.getLogger("red.cogs.Audio.cog.Tasks.lavalink")
_ = lambda s: s


class LavalinkTasks(MixinMeta, metaclass=CompositeMetaClass):
    def lavalink_restart_connect(self) -> None:
        lavalink.unregister_event_listener(self.lavalink_event_handler)
        lavalink.unregister_update_listener(self.lavalink_update_handler)
        if self.lavalink_connect_task:
            self.lavalink_connect_task.cancel()
        if self._restore_task:
            self._restore_task.cancel()

        self._restore_task = None
        lavalink.register_event_listener(self.lavalink_event_handler)
        lavalink.register_update_listener(self.lavalink_update_handler)
        self.lavalink_connect_task = self.bot.loop.create_task(self.lavalink_attempt_connect())

    async def lavalink_attempt_connect(self, timeout: int = 50) -> None:
        self.lavalink_connection_aborted = False
        max_retries = 5
        retry_count = 0
        lazy_external = False
        node = "primary"
        while retry_count < max_retries:
            managed = await self.config_cache.use_managed_lavalink.get_global()
            java_exec = str(await self.config_cache.java_exec.get_global())
            host = await self.config_cache.node_config.get_host(node_identifier=node)
            password = await self.config_cache.node_config.get_password(node_identifier=node)
            port = await self.config_cache.node_config.get_port(node_identifier=node)
            name = await self.config_cache.node_config.get_identifier(node_identifier=node)
            rest_uri = await self.config_cache.node_config.get_rest_uri(node_identifier=node)
            if managed is True:
                if self.player_manager is not None:
                    await self.player_manager.shutdown()
                self.player_manager = ServerManager(host, password, port, self.config_cache)
                try:
                    await self.player_manager.start(java_exec)
                except ShouldAutoRecover:
                    if self.player_manager is not None:
                        await self.player_manager.shutdown()
                    self.player_manager = None
                    log.warning(
                        "Managed node cannot be started due to port 2333 "
                        "already being taken, attempting to connect to existing node."
                    )
                    lazy_external = True
                    break
                except LavalinkDownloadFailed as exc:
                    await asyncio.sleep(1)
                    if exc.should_retry:
                        log.exception(
                            "Exception whilst starting managed node, retrying...",
                            exc_info=exc,
                        )
                        retry_count += 1
                        continue
                    else:
                        log.exception(
                            "Fatal exception whilst starting managed node, aborting...",
                            exc_info=exc,
                        )
                        self.lavalink_connection_aborted = True
                        raise
                except asyncio.CancelledError:
                    log.exception(
                        "Invalid machine architecture, cannot run a managed Lavalink node."
                    )
                    raise
                except Exception as exc:
                    log.exception(
                        "Unhandled exception whilst starting managed node, aborting...",
                        exc_info=exc,
                    )
                    self.lavalink_connection_aborted = True
                    raise
                else:
                    break
            else:
                break
        else:
            log.critical(
                "Setting up the managed node failed after multiple attempts. "
                "See above tracebacks for details."
            )
            self.lavalink_connection_aborted = True
            return

        retry_count = 0
        while retry_count < max_retries:
            if lavalink.node._nodes:
                await lavalink.node.disconnect()
            try:
                await lavalink.initialize(
                    bot=self.bot,
                    host=host,
                    password=password,
                    ws_port=port,
                    timeout=timeout,
                    resume_key=f"Red-Core-Audio-{self.bot.user.id}-{data_manager.instance_name}",
                    node_name=name,
                    rest_uri=rest_uri,
                )
            except asyncio.TimeoutError:
                log.error("Connecting to node timed out, retrying...")
                if managed is True and self.player_manager is not None:
                    await self.player_manager.shutdown()
                retry_count += 1
                await asyncio.sleep(1)  # prevent busylooping
            except Exception as exc:
                log.exception(
                    "Unhandled exception whilst connecting to node, aborting...", exc_info=exc
                )
                self.lavalink_connection_aborted = True
                raise
            else:
                break
        else:
            self.lavalink_connection_aborted = True
            if not lazy_external:
                log.critical(
                    "Connecting to the node failed after multiple attempts. "
                    "See above tracebacks for details."
                )
            else:
                log.critical(
                    "Connecting to the existing node failed after multiple attempts. "
                    "This could be due to another program using port 2333, "
                    "please stop that program and reload audio; If you are unsure what program is "
                    "using port 2333, please restart the machine as it could be a ghost node. "
                    "Keep in mind, I'm using HOST: %s | PASSWORD: %s | PORT: %s, to connect to to"
                    "the existing server, if you have an external server already ensure you have "
                    "set the correct host, password and port using `[p]audioset lavalink ...` on this bot.",
                    host,
                    password,
                    port,
                )
            return
        if managed is False:
            await asyncio.sleep(5)
        self._restore_task = asyncio.create_task(self.restore_players())
