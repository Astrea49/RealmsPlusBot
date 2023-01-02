import asyncio
import typing

import attrs
import naff
import redis.asyncio as aioredis

KT = typing.TypeVar("KT")
VT = typing.TypeVar("VT")
D = typing.TypeVar("D")


@attrs.define(kw_only=True)
class TimedDict(typing.Generic[KT, VT]):
    expires: float = attrs.field(default=60)

    _dict: dict[KT, VT] = attrs.field(factory=dict, init=False)
    _loop: asyncio.AbstractEventLoop = attrs.field(
        factory=asyncio.get_running_loop, init=False
    )
    _timer: typing.Optional[asyncio.TimerHandle] = attrs.field(default=None, init=False)

    def __setitem__(self, key: KT, value: VT):
        self._dict[key] = value

    def __getitem__(self, key: KT) -> VT:
        return self._dict[key]

    def __delitem__(self, key: KT):
        del self._dict[key]

    @typing.overload
    def get(self, key: KT) -> typing.Optional[VT]:
        ...

    @typing.overload
    def get(self, key: KT, default: D) -> typing.Union[VT, D]:
        ...

    def get(
        self, key: KT, default: typing.Optional[D] = None
    ) -> typing.Union[VT, D, None]:
        return self._dict.get(key, default)

    @property
    def filled(self) -> bool:
        return bool(self._timer) and self._loop.time() <= self._timer.when()

    def _clear(self):
        self._dict.clear()
        self._timer = None

    def insert(self, dict: dict[KT, VT]):
        self._dict.update(dict)

        if not self.filled:
            self._timer = self._loop.call_later(self.expires, self._clear)

    def add_one(self, key: KT, value: VT):
        self._dict[key] = value

    def cancel_timer(self):
        if self._timer:
            self._timer.cancel()


def valid_channel_check(channel: naff.GuildChannel):
    if not isinstance(channel, naff.MessageableMixin):
        raise naff.errors.BadArgument(f"Cannot send messages in {channel.name}.")

    perms = channel.permissions_for(channel.guild.me)

    if (
        naff.Permissions.VIEW_CHANNEL not in perms
    ):  # technically pointless, but who knows
        raise naff.errors.BadArgument(f"Cannot read messages in {channel.name}.")
    elif naff.Permissions.READ_MESSAGE_HISTORY not in perms:
        raise naff.errors.BadArgument(f"Cannot read message history in {channel.name}.")
    elif naff.Permissions.SEND_MESSAGES not in perms:
        raise naff.errors.BadArgument(f"Cannot send messages in {channel.name}.")
    elif naff.Permissions.EMBED_LINKS not in perms:
        raise naff.errors.BadArgument(f"Cannot send embeds in {channel.name}.")

    return channel


class ValidChannelConverter(naff.Converter):
    async def convert(self, ctx: naff.InteractionContext, argument: naff.GuildText):
        return valid_channel_check(argument)


class SemaphoreRedis(aioredis.Redis):
    def __init__(self, **kwargs):
        semaphore_value = kwargs.pop("semaphore_value", 1)
        super().__init__(**kwargs)
        self.connection_pool.connection_kwargs.pop("semaphore_value", None)
        self.semaphore = asyncio.BoundedSemaphore(semaphore_value)

    async def execute_command(self, *args, **options):
        async with self.semaphore:
            return await super().execute_command(*args, **options)
