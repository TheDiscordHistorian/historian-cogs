import asyncio
import typing
from datetime import datetime, timedelta

import discord
from core.thread import Thread as OldThread
from core.thread import ThreadManager as OldTM
from core.models import getLogger
from core.utils import match_title, truncate, match_user_id
from discord.ext import commands
from dislash import slash_commands
from dislash.interactions import ActionRow, Button, ButtonStyle

logger = getLogger(__name__)


class NewThread(OldThread):
    async def close(
        self,
        *,
        closer: typing.Union[discord.Member, discord.User],
        after: int = 0,
        silent: bool = False,
        delete_channel: bool = True,
        message: str = None,
        auto_close: bool = False,
    ) -> None:
        """Close a thread now or after a set time in seconds"""

        # restarts the after timer
        await self.cancel_closure(auto_close)

        if after > 0:
            # TODO: Add somewhere to clean up broken closures
            #  (when channel is already deleted)
            now = datetime.utcnow()
            items = {
                # 'initiation_time': now.isoformat(),
                "time": (now + timedelta(seconds=after)).isoformat(),
                "closer_id": closer.id,
                "silent": silent,
                "delete_channel": delete_channel,
                "message": message,
                "auto_close": auto_close,
            }
            self.bot.config["closures"][str(self.id)] = items
            await self.bot.config.update()

            task = self.bot.loop.call_later(
                after, self._close_after, closer, silent, delete_channel, message
            )

            if auto_close:
                self.auto_close_task = task
            else:
                self.close_task = task
        else:
            await self._close(closer, silent, delete_channel, message)

    async def _close(
        self, closer, silent=False, delete_channel=True, message=None, scheduled=False
    ):
        try:
            self.manager.cache.pop(self.id)
        except KeyError as e:
            logger.error("Thread already closed: %s.", e)
            return

        await self.cancel_closure(all=True)

        # Cancel auto closing the thread if closed by any means.

        self.bot.config["subscriptions"].pop(str(self.id), None)
        self.bot.config["notification_squad"].pop(str(self.id), None)

        # Logging
        if self.channel:
            log_data = await self.bot.api.post_log(
                self.channel.id,
                {
                    "open": False,
                    "title": match_title(self.channel.topic),
                    "closed_at": str(datetime.utcnow()),
                    "nsfw": self.channel.nsfw,
                    "close_message": message if not silent else None,
                    "closer": {
                        "id": str(closer.id),
                        "name": closer.name,
                        "discriminator": closer.discriminator,
                        "avatar_url": str(closer.avatar_url),
                        "mod": True,
                    },
                },
            )
        else:
            log_data = None

        if isinstance(log_data, dict):
            prefix = self.bot.config["log_url_prefix"].strip("/")
            if prefix == "NONE":
                prefix = ""
            log_url = f"{self.bot.config['log_url'].strip('/')}{'/' + prefix if prefix else ''}/{log_data['key']}"

            if log_data["title"]:
                sneak_peak = log_data["title"]
            elif log_data["messages"]:
                content = str(log_data["messages"][0]["content"])
                sneak_peak = content.replace("\n", "")
            else:
                sneak_peak = "No content"

            if self.channel.nsfw:
                _nsfw = "NSFW-"
            else:
                _nsfw = ""

            desc = f"[`{_nsfw}{log_data['key']}`]({log_url}): "
            desc += truncate(sneak_peak, max=75 - 13)
        else:
            desc = "Could not resolve log url."
            log_url = None

        embed = discord.Embed(description=desc, color=self.bot.error_color)

        if self.recipient is not None:
            user = f"{self.recipient} (`{self.id}`)"
        else:
            user = f"`{self.id}`"

        if self.id == closer.id:
            _closer = "the Recipient"
        else:
            _closer = f"{closer} ({closer.id})"

        embed.title = user

        event = "Thread Closed as Scheduled" if scheduled else "Thread Closed"
        # embed.set_author(name=f"Event: {event}", url=log_url)
        embed.set_footer(text=f"{event} by {_closer}", icon_url=closer.avatar_url)
        embed.timestamp = datetime.utcnow()
        if log_url is not None:
            components = ActionRow(
                Button(style=ButtonStyle.link, label="Log link", url=f"{log_url}")
                )
        else:
            components = ActionRow(
                Button(style=ButtonStyle.link, label="Log Link", url="https://github.com/kyb3r/modmail")
                )            
        tasks = [self.bot.config.update()]

        if self.bot.log_channel is not None and self.channel is not None:
                tasks.append(self.bot.log_channel.send(embed=embed, components=[components]))

        # Thread closed message

        embed = discord.Embed(
            title=self.bot.config["thread_close_title"], color=self.bot.error_color,
        )
        if self.bot.config["show_timestamp"]:
            embed.timestamp = datetime.utcnow()

        if not message:
            if self.id == closer.id:
                message = self.bot.config["thread_self_close_response"]
            else:
                message = self.bot.config["thread_close_response"]

        message = self.bot.formatter.format(
            message, closer=closer, loglink=log_url, logkey=log_data["key"] if log_data else None
        )

        embed.description = message
        footer = self.bot.config["thread_close_footer"]
        embed.set_footer(text=footer, icon_url=self.bot.guild.icon_url)

        if not silent and self.recipient is not None:
            tasks.append(self.recipient.send(embed=embed))

        if delete_channel:
            tasks.append(self.channel.delete())

        await asyncio.gather(*tasks)
        self.bot.dispatch("thread_close", self, closer, silent, delete_channel, message, scheduled)

class ThreadManager(OldTM):
    async def find(
        self,
        *,
        recipient: typing.Union[discord.Member, discord.User] = None,
        channel: discord.TextChannel = None,
        recipient_id: int = None,
    ) -> typing.Optional[NewThread]:
        """Finds a thread from cache or from discord channel topics."""
        if recipient is None and channel is not None:
            thread = await self._find_from_channel(channel)
            if thread is None:
                user_id, thread = next(
                    ((k, v) for k, v in self.cache.items() if v.channel == channel), (-1, None)
                )
                if thread is not None:
                    logger.debug("Found thread with tempered ID.")
                    await channel.edit(topic=f"User ID: {user_id}")
            return thread

        if recipient:
            recipient_id = recipient.id

        thread = self.cache.get(recipient_id)
        if thread is not None:
            try:
                await thread.wait_until_ready()
            except asyncio.CancelledError:
                logger.warning("Thread for %s cancelled, abort creating", recipient)
                return thread
            else:
                if not thread.channel or not self.bot.get_channel(thread.channel.id):
                    logger.warning(
                        "Found existing thread for %s but the channel is invalid.", recipient_id
                    )
                    self.bot.loop.create_task(
                        thread.close(closer=self.bot.user, silent=True, delete_channel=False)
                    )
                    thread = None
        else:
            channel = discord.utils.get(
                self.bot.modmail_guild.text_channels, topic=f"User ID: {recipient_id}"
            )
            if channel:
                thread = NewThread(self, recipient or recipient_id, channel)
                if thread.recipient:
                    # only save if data is valid
                    self.cache[recipient_id] = thread
                thread.ready = True
        return thread

    async def _find_from_channel(self, channel):
        """
        Tries to find a thread from a channel channel topic,
        if channel topic doesnt exist for some reason, falls back to
        searching channel history for genesis embed and
        extracts user_id from that.
        """
        user_id = -1

        if channel.topic:
            user_id = match_user_id(channel.topic)

        if user_id == -1:
            return None

        if user_id in self.cache:
            return self.cache[user_id]

        try:
            recipient = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
        except discord.NotFound:
            recipient = None

        if recipient is None:
            thread = NewThread(self, user_id, channel)
        else:
            self.cache[user_id] = thread = NewThread(self, recipient, channel)
        thread.ready = True

        return thread

    async def create(
        self,
        recipient: typing.Union[discord.Member, discord.User],
        *,
        message: discord.Message = None,
        creator: typing.Union[discord.Member, discord.User] = None,
        category: discord.CategoryChannel = None,
        manual_trigger: bool = True,
    ) -> NewThread:
        """Creates a Modmail thread"""

        # checks for existing thread in cache
        thread = self.cache.get(recipient.id)
        if thread:
            try:
                await thread.wait_until_ready()
            except asyncio.CancelledError:
                logger.warning("Thread for %s cancelled, abort creating", recipient)
                return thread
            else:
                if thread.channel and self.bot.get_channel(thread.channel.id):
                    logger.warning("Found an existing thread for %s, abort creating.", recipient)
                    return thread
                logger.warning(
                    "Found an existing thread for %s, closing previous thread.", recipient
                )
                self.bot.loop.create_task(
                    thread.close(closer=self.bot.user, silent=True, delete_channel=False)
                )

        thread = NewThread(self, recipient)

        self.cache[recipient.id] = thread

        # Schedule thread setup for later
        cat = self.bot.main_category
        if category is None and len(cat.channels) >= 49:
            fallback_id = self.bot.config["fallback_category_id"]
            if fallback_id:
                fallback = discord.utils.get(cat.guild.categories, id=int(fallback_id))
                if fallback and len(fallback.channels) < 49:
                    category = fallback

            if not category:
                category = await cat.clone(name="Fallback Modmail")
                self.bot.config.set("fallback_category_id", str(category.id))
                await self.bot.config.update()

        if (message or not manual_trigger) and self.bot.config["confirm_thread_creation"]:
            if not manual_trigger:
                destination = recipient
            else:
                destination = message.channel
            confirm = await destination.send(
                embed=discord.Embed(
                    title=self.bot.config["confirm_thread_creation_title"],
                    description=self.bot.config["confirm_thread_response"],
                    color=self.bot.main_color,
                )
            )
            accept_emoji = self.bot.config["confirm_thread_creation_accept"]
            deny_emoji = self.bot.config["confirm_thread_creation_deny"]
            await confirm.add_reaction(accept_emoji)
            await asyncio.sleep(0.2)
            await confirm.add_reaction(deny_emoji)
            try:
                r, _ = await self.bot.wait_for(
                    "reaction_add",
                    check=lambda r, u: u.id == recipient.id
                    and r.message.id == confirm.id
                    and r.message.channel.id == confirm.channel.id
                    and str(r.emoji) in (accept_emoji, deny_emoji),
                    timeout=20,
                )
            except asyncio.TimeoutError:
                thread.cancelled = True

                await confirm.remove_reaction(accept_emoji, self.bot.user)
                await asyncio.sleep(0.2)
                await confirm.remove_reaction(deny_emoji, self.bot.user)
                await destination.send(
                    embed=discord.Embed(
                        title="Cancelled", description="Timed out", color=self.bot.error_color
                    )
                )
                del self.cache[recipient.id]
                return thread
            else:
                if str(r.emoji) == deny_emoji:
                    thread.cancelled = True

                    await confirm.remove_reaction(accept_emoji, self.bot.user)
                    await asyncio.sleep(0.2)
                    await confirm.remove_reaction(deny_emoji, self.bot.user)
                    await destination.send(
                        embed=discord.Embed(title="Cancelled", color=self.bot.error_color)
                    )
                    del self.cache[recipient.id]
                    return thread

        self.bot.loop.create_task(
            thread.setup(creator=creator, category=category, initial_message=message)
        )
        return thread

    async def find_or_create(self, recipient) -> NewThread:
        return await self.find(recipient=recipient) or await self.create(recipient)

class LogButton(commands.Cog):
    """Just to define everything idk."""
    def __init__(self, bot):
        self.bot = bot

        if not hasattr(self.bot, "slash"):
            slash_commands.SlashClient(self.bot)
        self.bot.threads = ThreadManager(self.bot)


def setup(bot):
    bot.add_cog(LogButton(bot))
