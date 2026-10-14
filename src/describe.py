"""What the bot can tell about a message without asking Telegram anything."""

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


def media_location(media: types.TypeMessageMedia | None) -> tuple[str, int] | None:
    """`(kind, dc_id)` of the photo or document attached to a message."""
    if isinstance(media, types.MessageMediaPhoto) and isinstance(
        media.photo, types.Photo
    ):
        return "photo", media.photo.dc_id

    if isinstance(media, types.MessageMediaDocument) and isinstance(
        media.document, types.Document
    ):
        return document_kind(media.document), media.document.dc_id

    return None


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
