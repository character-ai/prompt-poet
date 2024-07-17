"""Helpers for CAI-specific example templates."""

import re
from dataclasses import dataclass
from typing import Union

DEFAULT_USERNAME = "user"
NARRATOR_NAME = "narrator"
DASH = "-"


@dataclass
class CAIMessage:
    """CAI-specific abstraction over a message."""

    author: str
    text: str
    # Unspecified: 0
    # HumanMessage: 1
    # CharacterMessage: 2
    # SystemMessage: 3
    type: int = 0
    is_pinned: bool = False


def canonicalize_name(name: Union[str, None]) -> str:
    """Makes name format consistent with author names we use in training data."""
    if not name:
        return DASH
    return DASH.join(name.split())


def canonicalize_user_name(name: Union[str, None]) -> str:
    """Makes name format consistent with author names we use in training data."""
    # The "-" is used in upstream components and should be overriden to default value.
    if not name or name == DASH:
        return DEFAULT_USERNAME
    return DASH.join(name.split())


def get_character_definition_messages(
    character: dict,
    username: str,
) -> list[CAIMessage]:
    """Returns messages made from character name, descrption and definition."""
    del username
    charname = canonicalize_name(character.get("participant__name", ""))

    messages = []
    if description := character.get("description"):
        if title := character.get("title"):
            description = f"{title} - {description}"
        messages.append(CAIMessage(author=charname, text=description))
    elif title := character.get("title"):
        messages.append(CAIMessage(author=charname, text=title))

    if definition := character.get("definition"):
        for line in definition.split("\n"):
            messages.append(CAIMessage(author="", text=line))

    return messages


def maybe_inject_narrator(message: str, default_author: str = NARRATOR_NAME) -> str:
    """Inject narrator into the message if applicable."""
    if re.match(r"^[\w-]+:", message):
        return message
    return f"{default_author}: {message}"


def escape_sequences(message: str) -> str:
    """Escape sequences that will break yaml parsing."""
    return message.replace("\n", "\\n").replace("\r", "\\r").replace("'", "'")


def raise_missing_context_data(key: str):
    """Raise missing data from jinja context."""
    raise ValueError(f"Missing required key in jinja context: {key=}")


def pretruncate_messages(
    messages: list[CAIMessage], token_limit: int
) -> list[CAIMessage]:
    """Pretruncates messages for Hermes generation."""
    if token_limit < 0:
        return messages

    message_truncation_step = token_limit // 10
    while len(messages) > 2 * message_truncation_step:
        messages = messages[message_truncation_step:]
    return messages
