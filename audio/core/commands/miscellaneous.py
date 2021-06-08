# Future Imports
from __future__ import annotations

# Standard Library Imports
import heapq
import logging
import random

# Dependency Imports
from redbot.core import commands
from redbot.core.utils import AsyncIter

# My Modded Imports
import lavalink

# Audio Imports
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = logging.getLogger("red.cogs.Audio.cog.Commands.miscellaneous")


class MiscellaneousCommands(MixinMeta, metaclass=CompositeMetaClass):
    @commands.command(name="sing")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def command_sing(self, ctx: commands.Context):
        """Make Red sing one of her songs."""
        ids = (
            "zGTkAVsrfg8",
            "cGMWL8cOeAU",
            "vFrjMq4aL-g",
            "WROI5WYBU_A",
            "41tIUr_ex3g",
            "f9O2Rjn1azc",
        )
        url = f"https://www.youtube.com/watch?v={random.choice(ids)}"
        await ctx.invoke(self.command_play, queries=[url])

    @commands.command(name="percent")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def command_percent(self, ctx: commands.Context):
        """Queue percentage."""
        if not self._player_check(ctx):
            return await self.send_embed_msg(ctx, title="Nothing playing.")
        player = lavalink.get_player(ctx.guild.id)
        queue_tracks = player.queue
        requesters = {"total": 0, "users": {}}

        async def _usercount(req_username):
            if req_username in requesters["users"]:
                requesters["users"][req_username]["songcount"] += 1
                requesters["total"] += 1
            else:
                requesters["users"][req_username] = {}
                requesters["users"][req_username]["songcount"] = 1
                requesters["total"] += 1

        async for track in AsyncIter(queue_tracks):
            req_username = "{}#{}".format(track.requester.name, track.requester.discriminator)
            await _usercount(req_username)

        try:
            req_username = "{}#{}".format(
                player.current.requester.name, player.current.requester.discriminator
            )
            await _usercount(req_username)
        except AttributeError:
            return await self.send_embed_msg(ctx, title="There's nothing in the queue.")

        async for req_username in AsyncIter(requesters["users"]):
            percentage = float(requesters["users"][req_username]["songcount"]) / float(
                requesters["total"]
            )
            requesters["users"][req_username]["percent"] = round(percentage * 100, 1)

        top_queue_users = heapq.nlargest(
            20,
            [
                (x, requesters["users"][x][y])
                for x in requesters["users"]
                for y in requesters["users"][x]
                if y == "percent"
            ],
            key=lambda x: x[1],
        )
        queue_user = ["{}: {:g}%".format(x[0], x[1]) for x in top_queue_users]
        queue_user_list = "\n".join(queue_user)
        await self.send_embed_msg(
            ctx, title="Queued and playing tracks:", description=queue_user_list
        )
