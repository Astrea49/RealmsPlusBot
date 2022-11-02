# realms api classes generated by https://app.quicktype.io/
import asyncio
import os
import typing
from enum import Enum
from types import NoneType
from typing import Any
from typing import Callable
from typing import List
from typing import Optional
from typing import TypeVar

import aiohttp
import attrs
import orjson
import pydantic
from xbox.webapi.authentication.manager import AuthenticationManager
from xbox.webapi.authentication.models import OAuth2TokenResponse

import common.utils as utils

T = TypeVar("T")


# while we do monkeypatch the xbox api lib to make CamelCaseModel faster anyways
# i'd rather have my own implementation just in case there's possiblities to
# speed things up or tweak things


def to_camel(string):
    words = string.split("_")
    return words[0] + "".join(word.capitalize() for word in words[1:])


class CamelCaseModel(pydantic.BaseModel):
    class Config:
        arbitrary_types_allowed = True
        allow_population_by_field_name = True
        alias_generator = to_camel
        json_loads = orjson.loads


def from_list(f: Callable[[Any], T], x: Any) -> List[T]:
    return [f(y) for y in x]


class Permission(Enum):
    VISITOR = "VISITOR"
    MEMBER = "MEMBER"
    OPERATOR = "OPERATOR"


class State(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"


class WorldType(Enum):
    NORMAL = "NORMAL"


class FullRealm(CamelCaseModel):
    id: int
    remote_subscription_id: str
    owner: Optional[str]
    owner_uuid: Optional[str] = None
    name: str
    default_permission: Permission
    state: State
    days_left: int
    expired: bool
    expired_trial: bool
    grace_period: bool
    world_type: WorldType
    players: NoneType
    max_players: int
    minigame_name: NoneType
    minigame_id: NoneType
    minigame_image: NoneType
    active_slot: int
    slots: NoneType
    member: bool
    club_id: Optional[int] = None
    subscription_refresh_status: NoneType
    motd: Optional[str] = None


class FullWorlds(CamelCaseModel):
    servers: List[FullRealm]


class Player(CamelCaseModel):
    uuid: str
    name: NoneType
    operator: bool
    accepted: bool
    online: bool
    permission: Permission


class PartialRealm(CamelCaseModel):
    id: int
    players: List[Player]
    full: bool


class ActivityList(CamelCaseModel):
    servers: List[PartialRealm]


class RealmsAPIException(Exception):
    def __init__(self, resp: aiohttp.ClientResponse, error: Exception):
        self.resp = resp
        self.error = error

        super().__init__(
            "An error occured when trying to access this resource: code"
            f" {resp.status}.\nError: {error}"
        )


@attrs.define()
class RealmsAPI:
    session: aiohttp.ClientSession = attrs.field()
    auth_mgr: AuthenticationManager = attrs.field(init=False)

    def __attrs_post_init__(self):
        self.auth_mgr = AuthenticationManager(
            self.session,
            os.environ["XBOX_CLIENT_ID"],
            os.environ["XBOX_CLIENT_SECRET"],
            "",
        )
        self.auth_mgr.oauth = OAuth2TokenResponse.parse_file(
            os.environ["XAPI_TOKENS_LOCATION"]
        )
        asyncio.create_task(self.refresh_tokens())

    @property
    def HEADERS(self):
        return {
            "Client-Version": utils.MC_VERSION,
            "User-Agent": "MCPE/UWP",
            "Authorization": self.auth_mgr.xsts_token.authorization_header_value,
        }

    async def refresh_tokens(self, force_refresh: bool = False):
        """Refresh all tokens."""
        if force_refresh:
            self.auth_mgr.oauth = await self.auth_mgr.refresh_oauth_token()
            self.auth_mgr.user_token = await self.auth_mgr.request_user_token()
            self.auth_mgr.xsts_token = await self.auth_mgr.request_xsts_token(
                relying_party=utils.REALMS_API_URL
            )
        else:
            if not (self.auth_mgr.oauth and self.auth_mgr.oauth.is_valid()):
                self.auth_mgr.oauth = await self.auth_mgr.refresh_oauth_token()
            if not (self.auth_mgr.user_token and self.auth_mgr.user_token.is_valid()):
                self.auth_mgr.user_token = await self.auth_mgr.request_user_token()
            if not (self.auth_mgr.xsts_token and self.auth_mgr.xsts_token.is_valid()):
                self.auth_mgr.xsts_token = await self.auth_mgr.request_xsts_token(
                    relying_party=utils.REALMS_API_URL
                )

    async def close(self):
        await self.session.close()

    async def request(
        self,
        method: str,
        url: str,
        data: typing.Optional[dict] = None,
        *,
        force_refresh: bool = False,
        times: int = 1,
    ):
        # refresh token as needed
        await self.refresh_tokens(force_refresh=force_refresh)

        async with self.session.request(
            method, f"{utils.REALMS_API_URL}{url}", headers=self.HEADERS, data=data
        ) as resp:
            if resp.status == 401:  # unauthorized
                return await self.request(
                    method, url, data, force_refresh=True, times=times
                )
            if resp.status == 502 and times < 4:  # bad gateway
                await asyncio.sleep(1)
                return await self.request(
                    method, url, data, force_refresh=True, times=times + 1
                )

            try:
                resp.raise_for_status()
                return await resp.json(loads=orjson.loads)
            except Exception as e:
                raise RealmsAPIException(resp, e)

    async def get(self, url: str, data: typing.Optional[dict] = None):
        return await self.request("GET", url, data=data)

    async def post(self, url: str, data: typing.Optional[dict] = None):
        return await self.request("POST", url, data=data)

    async def join_realm_from_code(self, code: str):
        return FullRealm.parse_obj(await self.post(f"invites/v1/link/accept/{code}"))

    async def fetch_realms(self):
        return FullWorlds.parse_obj(await self.get("worlds"))

    async def fetch_activities(self):
        return ActivityList.parse_obj(await self.get("activities/live/players"))
