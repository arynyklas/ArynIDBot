"""What the bot can tell about a message without asking Telegram anything."""

from collections.abc import Sequence

from telethon import utils
from telethon.tl import types

from src import texts


def document_kind(document: types.Document) -> str:
    """What the user sees the document as."""
    attributes = {type(attribute): attribute for attribute in document.attributes}
    audio = attributes.get(types.DocumentAttributeAudio)
    video = attributes.get(types.DocumentAttributeVideo)

    # Video stickers carry a video attribute too, and GIFs both of these.
    if types.DocumentAttributeSticker in attributes:
        return "sticker"

    if types.DocumentAttributeAnimated in attributes:
        return "GIF"

    if isinstance(audio, types.DocumentAttributeAudio):
        return "voice message" if audio.voice else "audio file"

    if isinstance(video, types.DocumentAttributeVideo):
        return "video message" if video.round_message else "video"

    return "file"


def message_photo(media: types.TypeMessageMedia | None) -> types.Photo | None:
    """The photo attached to a message, if any: link previews do not count."""
    if isinstance(media, types.MessageMediaPhoto) and isinstance(
        media.photo, types.Photo
    ):
        return media.photo

    return None


def media_location(media: types.TypeMessageMedia | None) -> tuple[str, int] | None:
    """`(kind, dc_id)` of the photo or document attached to a message."""
    photo = message_photo(media)

    if photo is not None:
        return "photo", photo.dc_id

    if isinstance(media, types.MessageMediaDocument) and isinstance(
        media.document, types.Document
    ):
        return document_kind(media.document), media.document.dc_id

    return None


def photo_platform_line(platform: str | None) -> str:
    """What to say about the platform one photo was uploaded from."""
    if platform is None:
        return texts.PHOTO_UNKNOWN

    return texts.PHOTO_PLATFORM.format(platform=platform)


def album_platform_line(platforms: Sequence[str | None]) -> str:
    """What to say about the platforms the photos of an album were uploaded from.

    Each platform is named once, in order; photos that match no header (or
    could not be read) add "an unknown platform" last. Labels contain commas,
    hence the semicolons.
    """
    named = list(dict.fromkeys(p for p in platforms if p is not None))

    if not named:
        return texts.ALBUM_UNKNOWN

    if None in platforms:
        named.append(texts.UNKNOWN_PLATFORM)

    return texts.ALBUM_PLATFORMS.format(platforms="; ".join(named))


def forward_origin(header: types.MessageFwdHeader, entity: object | None) -> str:
    """Who a forwarded message came from; `entity` is that user or chat, if known."""
    peer = header.from_id

    if isinstance(peer, types.PeerUser):
        template = (
            texts.FORWARDED_BOT
            if getattr(entity, "bot", False)
            else texts.FORWARDED_USER
        )

        return template.format(user_id=peer.user_id)

    if isinstance(peer, types.PeerChannel | types.PeerChat):
        # A basic group, or a supergroup posting as itself (anonymous admins).
        group = isinstance(peer, types.PeerChat) or getattr(entity, "megagroup", False)
        template = texts.FORWARDED_GROUP if group else texts.FORWARDED_CHANNEL
        text = template.format(chat_id=utils.get_peer_id(peer))

        if header.channel_post is not None:
            text += "\n" + texts.FORWARDED_POST.format(message_id=header.channel_post)

        return text

    # Only a name: the sender hides their account from forwards.
    return texts.FORWARDED_HIDDEN
