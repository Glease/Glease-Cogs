import datetime
import io
import typing
from typing import Literal

import chat_exporter
import discord
from redbot.core import checks, commands


class MyCog(commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def red_delete_data_for_user(self, *,
                                       requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
                                       user_id: int):
        pass

    async def get_messages(self,
                           ctx: commands.Context,
                           channel: discord.TextChannel,
                           curator: int,
                           approve_emoji: typing.Union[discord.Emoji, discord.PartialEmoji],
                           before: typing.Optional[typing.Union[discord.abc.Snowflake, datetime.datetime]],
                           after: typing.Optional[typing.Union[discord.abc.Snowflake, datetime.datetime]],
                           limit: typing.Optional[int]):
        async def process_message(message: discord.Message):
            for reaction in message.reactions:
                if reaction.emoji == approve_emoji:
                    async for u in reaction.users():  # type: discord.User
                        if u == curator:
                            messages.append(message)
                            return
                    return

        tracker = await ctx.send('Starting processing')
        processed = 0
        messages: typing.List[discord.Message] = []
        async for message in channel.history(limit=limit, before=before, after=after, oldest_first=True):
            processed += 1
            await process_message(message)
            if processed % 100 == 0:
                await tracker.edit(content=f'Processed {processed} Found {len(messages)}')
        await tracker.edit(content=f'Processed {processed} Found {len(messages)}. Finalizing...')
        if messages:
            return await chat_exporter.raw_export(channel=channel, messages=messages, guild=channel.guild)
        else:
            return None

    @checks.mod()
    @commands.guild_only()
    @commands.group(name="scrape_approved")
    async def scrape_approved(self, ctx: commands.Context):
        """Commands for exporting messages to which you have reacted."""

    @scrape_approved.command()
    async def do(self, ctx: commands.Context,
                 channel: discord.TextChannel,
                 approve: typing.Union[discord.Emoji, discord.PartialEmoji],
                 after: typing.Optional[typing.Union[discord.PartialMessage, discord.Message]] = None,
                 before: typing.Optional[typing.Union[discord.PartialMessage, discord.Message]] = None,
                 limit: typing.Optional[int] = None, ):
        """
        Export with all options available
        """
        with ctx.typing():
            transcript = await self.get_messages(ctx, channel, ctx.author, approve, before, after, limit)
            if transcript:
                file = discord.File(io.BytesIO(transcript.encode('utf-8')),
                                    filename=f"transcript-{datetime.datetime.now().timestamp()}.html")
                await ctx.send("Transcript generated.", file=file)
        await ctx.tick()

