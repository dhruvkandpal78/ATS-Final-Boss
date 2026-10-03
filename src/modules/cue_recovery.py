"""Bounded, passive text views for lexical cue matching.

This module does not decide whether a cue is malicious. Decoded Base64 is
never executed, fetched, or decoded a second time. A decoded match can only
be anchored to its encoded carrier in the original document.
"""

from __future__ import annotations

import base64
import binascii
from bisect import bisect_right
from dataclasses import dataclass
import re
import unicodedata


MAX_DOCUMENT_CHARS = 100_000
MAX_CANDIDATE_BLOCKS = 32
MAX_ENCODED_CHARS = 2_048

# Only common single-character visual substitutes are folded, and only in a
# token that also contains Latin letters. All-Cyrillic/Greek words stay intact.
_LOOKALIKES = {
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y",
    "х": "x", "і": "i", "ј": "j", "ѕ": "s", "ӏ": "l", "һ": "h",
    "α": "a", "β": "b", "ε": "e", "ι": "i", "κ": "k", "μ": "m",
    "ο": "o", "ρ": "p", "τ": "t", "χ": "x",
}
_CONTIGUOUS_B64 = re.compile(
    r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{16,}={0,2}(?![A-Za-z0-9+/=])"
)
_WRAPPED_B64 = re.compile(
    r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{8,}"
    r"(?:[ \t]{0,16}\r?\n[ \t]{0,16}[A-Za-z0-9+/]{4,})*"
    r"[ \t]{0,16}\r?\n[ \t]{0,16}[A-Za-z0-9+/]{1,}"
    r"={0,2}(?![A-Za-z0-9+/=])"
)
_DIRECTIVE = re.compile(r"\b(?:decode|apply|encoded|base64)\b", re.IGNORECASE)
_DIRECTIVE_GAP = re.compile(
    r"^[\s:=-]*(?:(?:this|the|following|payload|text|string|data|base64|"
    r"screening|evaluation|instruction|instructions|directive|directives|note)\b[\s:=-]*)*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CueView:
    text: str
    kind: str
    offsets: tuple[int, ...] | None
    carrier_span: tuple[int, int] | None


def _check_text(text: str) -> None:
    if not isinstance(text, str):
        raise TypeError("Cue text must be a string")
    if len(text) > MAX_DOCUMENT_CHARS:
        raise ValueError("Cue text exceeds the 100,000-character document bound")


def _without_format_controls(text: str) -> str:
    return "".join(char for char in text if unicodedata.category(char) != "Cf")


def _fold_mixed_tokens(text: str) -> str:
    result = list(text)
    position = 0
    while position < len(result):
        if not result[position].isalnum():
            position += 1
            continue
        end = position + 1
        while end < len(result) and result[end].isalnum():
            end += 1
        token = result[position:end]
        mixed = any("LATIN" in unicodedata.name(char, "") for char in token)
        if mixed and any(char in _LOOKALIKES for char in token):
            for index in range(position, end):
                result[index] = _LOOKALIKES.get(result[index], result[index])
        position = end
    return "".join(result)


def _plain_text_and_offsets(text: str) -> tuple[str, tuple[int, ...] | None]:
    normalized = _without_format_controls(unicodedata.normalize("NFKC", text).casefold())
    # NFKC may compose across original character boundaries. In that case a
    # per-character map would invent positions; abstain from mapping the view.
    pieces = []
    offsets = []
    for index, character in enumerate(text):
        piece = _without_format_controls(unicodedata.normalize("NFKC", character).casefold())
        pieces.append(piece)
        offsets.extend([index] * len(piece))
    if "".join(pieces) != normalized:
        mapped = None
    else:
        mapped = tuple(offsets)
    return _fold_mixed_tokens(normalized), mapped


def normalize_cue_text(text: str) -> str:
    """NFKC/casefold text, remove format controls, fold mixed-script lookalikes."""
    _check_text(text)
    return _plain_text_and_offsets(text)[0]


def _has_directive(text: str, start: int) -> bool:
    prefix = text[max(0, start - 80):start]
    for marker in reversed(list(_DIRECTIVE.finditer(prefix))):
        if _DIRECTIVE_GAP.fullmatch(prefix[marker.end():]):
            return True
    return False


def _base64_candidates(text: str):
    all_wrapped = [(match.start(), match.end()) for match in _WRAPPED_B64.finditer(text)]
    wrapped = [(start, end) for start, end in all_wrapped if _has_directive(text, start)]
    wrapped_starts = [start for start, _ in all_wrapped]
    # A line-wrapped carrier must be decoded as a whole or not at all. Its
    # individual lines are not independent encoded tokens.
    contiguous = []
    for match in _CONTIGUOUS_B64.finditer(text):
        containing = bisect_right(wrapped_starts, match.start()) - 1
        if containing >= 0 and match.end() <= all_wrapped[containing][1]:
            continue
        contiguous.append((match.start(), match.end()))
    candidates = sorted(wrapped + contiguous, key=lambda span: (span[0], -span[1]))
    last_end = -1
    for start, end in candidates:
        if start < last_end:
            continue
        last_end = end
        yield start, end


def cue_views(text: str) -> list[CueView]:
    """Return a normalized plain view and bounded, nonrecursive Base64 views.

    Plain offsets index original Python string characters. If cross-character
    Unicode composition makes that mapping ambiguous, offsets is ``None``.
    Decoded views always use ``carrier_span`` as a half-open original range;
    they never claim character offsets into the decoded content.
    """
    _check_text(text)
    plain, offsets = _plain_text_and_offsets(text)
    views = [CueView(plain, "plain", offsets, None)]
    for index, (start, end) in enumerate(_base64_candidates(text)):
        if index >= MAX_CANDIDATE_BLOCKS:
            break
        encoded = re.sub(r"\s", "", text[start:end])
        if len(encoded) > MAX_ENCODED_CHARS:
            continue
        try:
            raw = base64.b64decode(encoded, validate=True)
            decoded = raw.decode("utf-8", errors="strict")
        except (binascii.Error, UnicodeError, ValueError):
            continue
        if len(decoded) < 8 or not all(char.isprintable() or char in "\r\n\t"
                                           for char in decoded):
            continue
        views.append(CueView(normalize_cue_text(decoded), "base64", None, (start, end)))
    return views
