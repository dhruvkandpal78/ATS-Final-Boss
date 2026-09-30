"""Conservative review gates; anomaly scores remain advisory evidence."""
import re
import unicodedata

POLICY_VERSION = "2.0"


def keyword_repetition(text, detector):
    """Require a long contiguous repeated, skill-dominated token sequence.

    Density alone reflects occupation and resume layout. This fixed gate looks
    for at least eight exact copies and 32 tokens; it does not prove intent.
    Work is bounded by document limits and a maximum 12-token sequence.
    """
    normalized = unicodedata.normalize("NFKC", text).casefold()
    normalized = "".join(c for c in normalized if unicodedata.category(c) != "Cf")
    for pattern, standard in getattr(detector, "_aliases", []):
        normalized = pattern.sub(standard, normalized)
    tokens = re.findall(r"\w+", normalized)
    skills = {token for keyword in getattr(detector, "keywords", [])
              for token in re.findall(r"\w+", keyword.casefold())}
    if not skills:
        return None
    for width in range(1, 13):
        # Matching token i with token i-width finds periodic runs in linear time.
        run = 0
        for index in range(width, len(tokens)):
            run = run + 1 if tokens[index] == tokens[index - width] else 0
            length = run + width
            if length < max(32, 8 * width):
                continue
            sequence = tokens[index - width + 1:index + 1]
            if sum(token in skills for token in sequence) / width >= 0.5:
                return {"sequence_tokens": width, "repeated_tokens": length,
                        "minimum_copies": length // width}
    return None
