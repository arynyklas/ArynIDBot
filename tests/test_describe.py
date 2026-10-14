from datetime import UTC, datetime
from typing import Any

import pytest
from telethon.tl import types

from src import texts
from src.describe import (
    album_platform_line,
    document_kind,
    forward_origin,
    media_location,
)

_STICKER = types.DocumentAttributeSticker(
    alt="🙂", stickerset=types.InputStickerSetEmpty()
)
_VIDEO = types.DocumentAttributeVideo(duration=1.0, w=512, h=512)


def _document(
    *attributes: types.TypeDocumentAttribute, dc_id: int = 2
) -> types.Document:
    return types.Document(
        id=1,
        access_hash=2,
        file_reference=b"\x01",
        date=None,
        mime_type="application/octet-stream",
        size=1,
        dc_id=dc_id,
        attributes=list(attributes),
    )


@pytest.mark.parametrize(
    ("attributes", "kind"),
    [
        ((_STICKER, types.DocumentAttributeImageSize(w=512, h=512)), "sticker"),
        ((_STICKER, _VIDEO), "sticker"),
        ((types.DocumentAttributeAnimated(), _VIDEO), "GIF"),
        ((types.DocumentAttributeAudio(duration=3, voice=True),), "voice message"),
        ((types.DocumentAttributeAudio(duration=3, title="Song"),), "audio file"),
        (
            (
                types.DocumentAttributeVideo(
                    duration=1.0, w=240, h=240, round_message=True
                ),
            ),
            "video message",
        ),
        ((_VIDEO, types.DocumentAttributeFilename(file_name="a.mp4")), "video"),
        ((types.DocumentAttributeFilename(file_name="a.pdf"),), "file"),
    ],
)
def test_documents_are_named_as_users_see_them(attributes, kind):
    assert document_kind(_document(*attributes)) == kind


def test_the_dc_of_a_photo_or_document_is_reported():
    photo = types.Photo(
        id=1, access_hash=2, file_reference=b"", date=None, sizes=[], dc_id=4
    )

    assert media_location(types.MessageMediaPhoto(photo=photo)) == ("photo", 4)
    assert media_location(
        types.MessageMediaDocument(document=_document(_STICKER, dc_id=5))
    ) == ("sticker", 5)


@pytest.mark.parametrize(
    "media",
    [
        None,
        types.MessageMediaPhoto(photo=types.PhotoEmpty(id=1)),
        types.MessageMediaDocument(document=types.DocumentEmpty(id=1)),
        types.MessageMediaDice(value=6, emoticon="🎲"),
    ],
    ids=["no-media", "expired-photo", "expired-document", "dice"],
)
def test_media_without_a_file_has_no_dc(media):
    assert media_location(media) is None


@pytest.mark.parametrize(
    ("platforms", "named"),
    [
        (["iOS", "iOS", "iOS"], "iOS"),
        (
            ["Android", "Desktop Linux, Unigram, Generic", "Android"],
            "Android; Desktop Linux, Unigram, Generic",
        ),
        ([None, "iOS", None], f"iOS; {texts.UNKNOWN_PLATFORM}"),
    ],
    ids=["one-platform", "two-platforms", "partly-unknown"],
)
def test_an_album_names_each_platform_once(platforms, named):
    assert album_platform_line(platforms) == texts.ALBUM_PLATFORMS.format(
        platforms=named
    )


def test_an_album_of_unknown_platforms_says_so():
    assert album_platform_line([None, None]) == texts.ALBUM_UNKNOWN


def _header(**fields: Any) -> types.MessageFwdHeader:
    return types.MessageFwdHeader(date=datetime(2026, 1, 1, tzinfo=UTC), **fields)


def _user(*, bot: bool) -> types.User:
    return types.User(id=10, bot=bot)


def _channel(*, megagroup: bool) -> types.Channel:
    return types.Channel(
        id=1234567890,
        title="t",
        photo=types.ChatPhotoEmpty(),
        date=None,
        megagroup=megagroup,
        broadcast=not megagroup,
    )


def test_a_forward_from_a_user_shows_their_id():
    header = _header(from_id=types.PeerUser(user_id=10))

    assert forward_origin(header, _user(bot=False)) == texts.FORWARDED_USER.format(
        user_id=10
    )
    assert forward_origin(header, None) == texts.FORWARDED_USER.format(user_id=10)


def test_a_forward_from_a_bot_says_so():
    header = _header(from_id=types.PeerUser(user_id=10))

    assert forward_origin(header, _user(bot=True)) == texts.FORWARDED_BOT.format(
        user_id=10
    )


def test_a_forward_from_a_channel_shows_its_bot_api_id_and_the_post():
    header = _header(from_id=types.PeerChannel(channel_id=1234567890), channel_post=77)

    assert forward_origin(header, _channel(megagroup=False)) == (
        texts.FORWARDED_CHANNEL.format(chat_id=-1001234567890)
        + "\n"
        + texts.FORWARDED_POST.format(message_id=77)
    )


@pytest.mark.parametrize(
    ("peer", "entity", "chat_id"),
    [
        (
            types.PeerChannel(channel_id=1234567890),
            _channel(megagroup=True),
            -1001234567890,
        ),
        (types.PeerChat(chat_id=55), None, -55),
    ],
    ids=["supergroup", "basic-group"],
)
def test_a_forward_from_a_group_says_group(peer, entity, chat_id):
    assert forward_origin(_header(from_id=peer), entity) == (
        texts.FORWARDED_GROUP.format(chat_id=chat_id)
    )


def test_a_hidden_sender_is_reported_as_hidden():
    header = _header(from_name="Somebody")

    assert forward_origin(header, None) == texts.FORWARDED_HIDDEN
