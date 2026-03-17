"""Input sanitization for prompt injection defense.

Strips known injection prefixes, detects suspicious patterns, and
normalizes input before it reaches the LLM pipeline.
"""

from __future__ import annotations

import re
import logging
import unicodedata

logger = logging.getLogger("audhd_agents.sanitize")

# ---- Injection patterns ----
# Each tuple: (compiled regex, human-readable label)
_INJECTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?i)\bignore\s+(all\s+)?previous\s+instructions\b"), "ignore-previous"),
    (re.compile(r"(?i)\bignore\s+(all\s+)?above\s+instructions\b"), "ignore-above"),
    (re.compile(r"(?i)\bforget\s+(all\s+)?prior\s+(instructions|context)\b"), "forget-prior"),
    (re.compile(r"(?i)\byou\s+are\s+now\b"), "role-hijack"),
    (re.compile(r"(?i)\bact\s+as\s+(if\s+you\s+are|a)\b"), "role-hijack"),
    (re.compile(r"(?i)\bpretend\s+(you\s+are|to\s+be)\b"), "role-hijack"),
    (re.compile(r"(?i)^system\s*:", re.MULTILINE), "system-prefix"),
    (re.compile(r"(?i)\bdo\s+not\s+follow\s+(any|your)\s+(rules|instructions)\b"), "rule-override"),
    (re.compile(r"(?i)\b(reveal|show|print|output)\s+(your|the)\s+(system\s+)?prompt\b"), "prompt-leak"),
    (re.compile(r"(?i)\bwhat\s+(are|is)\s+your\s+(system\s+)?(instructions|prompt|rules)\b"), "prompt-leak"),
    (re.compile(r"(?i)\b(disregard|override)\s+(all\s+)?(safety|content)\s+(filters|rules|policies)\b"), "safety-override"),
]

# Max input length (1 MB matches ExecuteRequest.input_text max_length)
MAX_INPUT_LENGTH = 1_048_576


def detect_injection(text: str) -> list[str]:
    """Return list of detected injection pattern labels.

    Does NOT modify the input — purely diagnostic.
    """
    detected = []
    for pattern, label in _INJECTION_PATTERNS:
        if pattern.search(text):
            detected.append(label)
    return detected


def sanitize_input(text: str) -> tuple[str, list[str]]:
    """Sanitize input text and return (cleaned_text, detected_patterns).

    Steps:
    1. Truncate to MAX_INPUT_LENGTH
    2. Strip null bytes and control chars (except newline/tab)
    3. Normalize excessive whitespace
    4. Detect injection patterns (for logging)
    """
    # Truncate
    limit: int = MAX_INPUT_LENGTH
    if len(text) > limit:
        text = text[0:limit]  # Pyre2 workaround: explicit 0 start

    # AUDIT-FIX: P2-1 -- Unicode normalization (NFKC) before pattern matching
    text = unicodedata.normalize("NFKC", text)

    # AUDIT-FIX: P2-1 -- Strip zero-width characters
    text = re.sub(r"[\u200b\u200c\u200d\ufeff\u00ad]", "", text)

    # Strip null bytes and non-printable control characters (keep \n, \r, \t)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # Collapse excessive blank lines (3+ newlines -> 2)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Detect patterns for logging
    detected = detect_injection(text)

    return text, detected
