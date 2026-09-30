"""Source-backed instruction spans. Never guess offsets after normalization."""
import re
import unicodedata


def instruction_spans(text, detector, limit=20):
    normalize = getattr(detector, "_normalize_cue_text", None)
    benign = getattr(detector, "_is_benign_cue_context", None)
    patterns = getattr(detector, "INJECTION_PATTERNS", ())
    if not callable(normalize) or not callable(benign):
        return []
    normalized, offsets = [], []
    for index, character in enumerate(text):
        for value in unicodedata.normalize("NFKC", character).casefold():
            if unicodedata.category(value) != "Cf":
                normalized.append(value)
                offsets.append(index)
    normalized = "".join(normalized)
    # Cross-character Unicode compositions can change positions; abstain.
    if normalized != normalize(text):
        return []
    spans = set()
    for pattern in patterns:
        for match in re.finditer(pattern, normalized):
            if match.end() > match.start() and not benign(normalized, match.start(), match.end()):
                spans.add((offsets[match.start()], offsets[match.end() - 1] + 1))
    return [{"char_start": start, "char_end": end} for start, end in sorted(spans)[:limit]]
