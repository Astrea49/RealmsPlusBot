import typing
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Optional, Union
from uuid import UUID

import apischema

__all__ = (
    "ClubUserPresence",
    "ClubDeeplinkMetadata",
    "ClubDeeplinks",
    "ClubPresence",
    "ClubType",
    "AssociatedTitles",
    "ProfileMetadata",
    "IsRecommendable",
    "Profile",
    "TitleDeeplinkMetadata",
    "TitleDeeplinks",
    "Club",
    "ClubResponse",
    "parse_club_response",
)


def _camel_to_const_snake(s: str) -> str:
    return "".join([f"_{c}" if c.isupper() else c.upper() for c in s]).lstrip("_")


class ClubUserPresence(IntEnum):
    UNKNOWN = -1
    NOT_IN_CLUB = 0
    IN_CLUB = 1
    CHAT = 2
    FEED = 3
    ROSTER = 4
    PLAY = 5
    IN_GAME = 6

    @classmethod
    def from_xbox_api(cls, value: str) -> typing.Self:
        try:
            return cls[_camel_to_const_snake(value)]
        except KeyError:
            # it's not like i forgot a value, it's just that some are
            # literally not documented
            return cls.UNKNOWN


@dataclass
class ClubDeeplinkMetadata:
    page_name: str
    uri: str


@dataclass
class ClubDeeplinks:
    xbox: list[ClubDeeplinkMetadata]
    pc: list[ClubDeeplinkMetadata]


@dataclass
class ClubPresence:
    xuid: str
    last_seen_timestamp: datetime
    last_seen_state: str

    @property
    def last_seen_state_enum(self) -> ClubUserPresence:
        return ClubUserPresence.from_xbox_api(self.last_seen_state)


@dataclass
class ClubType:
    type: str
    genre: str
    localized_title_family_name: str
    title_family_id: UUID


@dataclass
class AssociatedTitles:
    value: list[str]
    can_viewer_change_setting: bool
    allowed_values: typing.Optional[typing.Any] = None


@dataclass
class ProfileMetadata:
    can_viewer_change_setting: bool
    value: Optional[Union[list[str], str]] = None
    allowed_values: typing.Optional[typing.Any] = None


@dataclass
class IsRecommendable:
    value: bool
    can_viewer_change_setting: bool
    allowed_values: Optional[list[bool]] = None


@dataclass
class Profile:
    description: ProfileMetadata
    rules: ProfileMetadata
    name: ProfileMetadata
    short_name: ProfileMetadata
    is_searchable: IsRecommendable
    is_recommendable: IsRecommendable
    request_to_join_enabled: IsRecommendable
    open_join_enabled: IsRecommendable
    leave_enabled: IsRecommendable
    transfer_ownership_enabled: IsRecommendable
    mature_content_enabled: IsRecommendable
    watch_club_titles_only: IsRecommendable
    display_image_url: ProfileMetadata
    background_image_url: ProfileMetadata
    preferred_locale: ProfileMetadata
    tags: ProfileMetadata
    associated_titles: AssociatedTitles
    primary_color: ProfileMetadata
    secondary_color: ProfileMetadata
    tertiary_color: ProfileMetadata


@dataclass
class TitleDeeplinkMetadata:
    title_id: str
    uri: str = field(metadata=apischema.alias("Uri"))  # wtf


@dataclass
class TitleDeeplinks:
    xbox: list[TitleDeeplinkMetadata]
    pc: list[TitleDeeplinkMetadata]
    android: list[TitleDeeplinkMetadata]
    ios: list[TitleDeeplinkMetadata] = field(
        metadata=apischema.alias("iOS")
    )  # this makes more sense at least


@dataclass
class Club:
    id: str
    club_type: ClubType
    creation_date_utc: datetime
    glyph_image_url: str
    banner_image_url: str
    followers_count: int
    members_count: int
    moderators_count: int
    recommended_count: int
    requested_to_join_count: int
    club_presence_count: int
    club_presence_today_count: int
    club_presence_in_game_count: int
    club_presence: list[ClubPresence]
    state: str
    report_count: int
    reported_items_count: int
    max_members_per_club: int
    max_members_in_game: int
    owner_xuid: str
    founder_xuid: str
    title_deeplinks: TitleDeeplinks
    profile: Profile
    club_deeplinks: ClubDeeplinks
    suspended_until_utc: typing.Optional[typing.Any] = None
    roster: typing.Optional[typing.Any] = None
    target_roles: typing.Optional[typing.Any] = None
    recommendation: typing.Optional[typing.Any] = None
    settings: typing.Optional[typing.Any] = None
    short_name: typing.Optional[typing.Any] = None


@dataclass
class ClubResponse:
    clubs: list[Club]
    search_facet_results: typing.Optional[typing.Any] = None
    recommendation_counts: typing.Optional[typing.Any] = None
    club_deeplinks: typing.Optional[typing.Any] = None


parse_club_response = apischema.deserialization_method(ClubResponse)
