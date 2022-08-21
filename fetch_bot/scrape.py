import datetime
import io
import json
import typing
from typing import Literal

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
                           export_type: typing.Literal["html", "json-short"],
                           limit: typing.Optional[int]) -> typing.Optional[discord.File]:
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
            if export_type == 'html':
                try:
                    import chat_exporter
                except ImportError:
                    await ctx.send("!!!Install chat_exporter==1.7.3 to use html export type!!!")
                    return None
                html = await chat_exporter.raw_export(channel=channel, messages=messages, guild=channel.guild)
                return discord.File(io.BytesIO(html.encode()), f'transcript-{datetime.datetime.now().timestamp()}.html')
            elif export_type == 'json-short':
                wrapper = io.TextIOWrapper(io.BytesIO(), encoding='utf-8')
                json.dump([
                    {
                        'content': message.clean_content,
                        'link': message.jump_url,
                        'author': {
                            'id': message.author.id,
                            'display_name': message.author.display_name,
                            'unique_name': str(message.author)
                        },
                        'embeds': [
                            embed.to_dict()
                            for embed in message.embeds
                        ],
                        'attachments': [
                            attachment.proxy_url
                            for attachment in message.attachments
                        ]
                    }
                    for message in messages
                ], wrapper)
                buffer = wrapper.detach()
                buffer.seek(0)
                return discord.File(buffer, f'transcript-{datetime.datetime.now().timestamp()}.json')
            else:
                await ctx.send("!!!Unknown export type!!!")
                return None
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
                 export_type: typing.Literal["html", "json-short"] = 'json-short',
                 limit: typing.Optional[int] = None, ):
        """
        Export with all options available
        """
        with ctx.typing():
            transcript = await self.get_messages(ctx, channel, ctx.author, approve, before, after, export_type, limit)
            if transcript:
                await ctx.send("Transcript generated.", file=transcript)
        await ctx.tick()
