"""Per-text feature rules (Step B): what can be counted reliably from a post's text.

Every rule here is a plain pattern, written down so the mentors can read it. Nothing is learned and
nothing is inferred about the writer. The counts describe the text that is in the cell, which can
still hold page chrome and several author blocks until segmentation exists, so they are cell-level.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Romanised Hindi forms that are rarely English words. This is an unvalidated proposal for the
# mentors to approve or change; it is not a language detector. "hum" and "hai" are in on purpose
# (the test fixture needs them) although "hum" is also an English verb, which is a known weakness.
ROMAN_HINDI_MARKERS: frozenset[str] = frozenset(
    {
        "hai", "hain", "hum", "hamara", "hamare", "hamari", "aap", "aapka", "aapke", "aapki",
        "tum", "mera", "meri", "mere", "apna", "apni", "apne", "kya", "kyun", "kyunki", "kaise",
        "kaun", "kahan", "kab", "kuch", "sab", "sabhi", "bahut", "bohot", "accha", "acha", "achha",
        "nahi", "nahin", "hoga", "hogi", "honge", "tha", "thi", "kar", "karo", "karna", "karenge",
        "kiya", "kiye", "kaam", "desh", "aur", "lekin", "magar", "ko", "ka", "ki", "ke", "toh",
        "bhi", "yeh", "woh", "wo", "jab", "tab", "abhi", "aaj", "saath", "sath", "liye", "bhai",
        "dost", "shukriya", "dhanyavaad", "namaste", "sirf", "zyada", "jyada", "bilkul", "wala",
        "wali", "wale", "raha", "rahi", "rahe", "chahiye", "sakta", "sakte", "sakti", "zindagi",
        "mehnat", "parivar", "mein",
    }
)

_DEVANAGARI = "ऀ-ॿ"
_TAG_CHARS = rf"\w{_DEVANAGARI}"
_SHORT_HOSTS = r"lnkd\.in|bit\.ly|t\.co|youtu\.be|goo\.gl|tinyurl\.com|buff\.ly|ow\.ly|amzn\.to"
_TLDS = r"com|in|org|net|co|io|ai|edu|gov|app|dev|biz|info|tech|me|ly"

_URL = re.compile(
    rf"(?:https?://|(?<![\w@.])www\.|(?<![\w@.])(?:{_SHORT_HOSTS})/)[^\s<>\"']+", re.IGNORECASE
)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_BARE_DOMAIN = re.compile(rf"(?<![\w@.-])(?:[A-Za-z0-9-]+\.)+(?:{_TLDS})(?![\w-])", re.IGNORECASE)
_HASHTAG = re.compile(rf"(?<!\w)#([{_TAG_CHARS}]+)")
_MENTION = re.compile(rf"(?<!\w)@[{_TAG_CHARS}]+")
_QUESTION_RUN = re.compile(r"\?{2,}|\?!|!\?")
_WORD = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
_DEVANAGARI_RUN = re.compile(rf"[{_DEVANAGARI}]+")

# Emoji: default-emoji characters count by themselves; text-style symbols count only when followed
# by the emoji variation selector. Regional-indicator pairs are flags, a digit plus U+FE0F plus U+20E3 is a keycap.
_DEFAULT_EMOJI = (
    "⌚⌛⏩-⏬⏰⏳◽◾☔☕♈-♓♿⚓⚡"
    "⚪⚫⚽⚾⛄⛅⛎⛔⛪⛲⛳⛵⛺⛽✅"
    "✊✋✨❌❎❓-❕❗➕-➗➰➿⬛⬜⭐"
    "⭕\U0001f004\U0001f0cf\U0001f18e\U0001f191-\U0001f19a\U0001f201\U0001f21a\U0001f22f"
    "\U0001f232-\U0001f23a\U0001f250\U0001f251\U0001f300-\U0001f3fa\U0001f400-\U0001faff"
)
_TEXT_STYLE = (
    "©®‼⁉™ℹ←-⇿⌀-⏿Ⓜ■-➿"
    "⤀-⥿⬀-⯿〰〽㊗㊙"
)
_ELEMENT = rf"(?:[{_DEFAULT_EMOJI}]|[{_TEXT_STYLE}](?=\ufe0f))[\U0001f3fb-\U0001f3ff]?\ufe0f?"
_EMOJI_CLUSTER = re.compile(
    rf"[\U0001f1e6-\U0001f1ff]{{2}}|[0-9#*]\ufe0f?\u20e3|{_ELEMENT}(?:\u200d{_ELEMENT})*"
)
_SYMBOL = re.compile(r"[←-⇿⌀-⏿■-➿⤀-⥿⬀-⯿]")

_REPOST_PHRASE = re.compile(
    r"\b(?:reposted|shared|celebrates|likes|loves|supports|commented on)\s+this\s*$", re.IGNORECASE
)
_REPOSTED_WORD = re.compile(r"\b(?:reposted|reposting)\b", re.IGNORECASE)
_PHRASE_MAX_LINE_CHARS = 120
_FOLLOW_LINES = frozenset({"follow", "+ follow"})


@dataclass(frozen=True)
class TextFeatures:
    """Counts and flags for one text. All defaults are the values for an empty text."""

    chars: int = 0
    words: int = 0
    hashtags: int = 0
    numeric_hashtags: int = 0
    mentions: int = 0
    stray_at: int = 0
    urls: int = 0
    bare_domains: int = 0
    question_marks: int = 0
    question_runs: int = 0
    emoji: int = 0
    symbols: int = 0
    devanagari_tokens: int = 0
    roman_markers: int = 0
    word_tokens: int = 0
    repost_line: bool = False
    repost_phrase: bool = False
    repost_word_in_text: bool = False
    follow_lines: int = 0


def _hashtag_counts(text: str) -> tuple[int, int]:
    """Return (hashtags with a letter, numeric-only hashtags)."""
    letters = 0
    numeric = 0
    for tag in _HASHTAG.findall(text):
        if tag.replace("_", "").isdigit():
            numeric += 1
        elif any(ch.isalpha() or ("ऀ" <= ch <= "ॿ" and not ch.isdigit()) for ch in tag):
            letters += 1
    return letters, numeric


def _mention_counts(text: str) -> tuple[int, int]:
    """Return (mentions, stray at-signs) for text that has no URLs or email addresses left."""
    mentions = len(_MENTION.findall(text))
    return mentions, text.count("@") - mentions


def _emoji_counts(text: str) -> tuple[int, int]:
    """Return (emoji clusters, text-style symbols that are not part of an emoji)."""
    clusters = _EMOJI_CLUSTER.findall(text)
    without_emoji = _EMOJI_CLUSTER.sub(" ", text)
    return len(clusters), len(_SYMBOL.findall(without_emoji))


def _word_counts(text: str) -> tuple[int, int, int]:
    """Return (Devanagari tokens, romanised Hindi markers, Latin word tokens)."""
    prose = _MENTION.sub(" ", _HASHTAG.sub(" ", text))
    words = [word.lower() for word in _WORD.findall(prose)]
    markers = sum(1 for word in words if word in ROMAN_HINDI_MARKERS)
    return len(_DEVANAGARI_RUN.findall(prose)), markers, len(words)


def _line_markers(text: str) -> tuple[bool, bool, int]:
    """Return (a line is exactly 'Repost', an engagement-phrase line, count of Follow lines)."""
    lines = [line.strip() for line in text.splitlines()]
    repost_line = any(line.casefold() == "repost" for line in lines)
    phrase = any(
        len(line) <= _PHRASE_MAX_LINE_CHARS and _REPOST_PHRASE.search(line) is not None
        for line in lines
    )
    follows = sum(1 for line in lines if line.casefold() in _FOLLOW_LINES)
    return repost_line, phrase, follows


def compute_features(text: str) -> TextFeatures:
    """Apply every rule to one text; an empty or blank text gives the all-zero default."""
    stripped = text.strip()
    if not stripped:
        return TextFeatures()
    without_urls = _URL.sub(" ", text)
    without_email = _EMAIL.sub(" ", without_urls)
    hashtags, numeric_hashtags = _hashtag_counts(without_urls)
    mentions, stray_at = _mention_counts(without_email)
    emoji, symbols = _emoji_counts(without_urls)
    devanagari, markers, word_tokens = _word_counts(without_email)
    repost_line, repost_phrase, follow_lines = _line_markers(text)
    return TextFeatures(
        chars=len(stripped),
        words=len(text.split()),
        hashtags=hashtags,
        numeric_hashtags=numeric_hashtags,
        mentions=mentions,
        stray_at=stray_at,
        urls=len(_URL.findall(text)),
        bare_domains=len(_BARE_DOMAIN.findall(without_email)),
        question_marks=without_urls.count("?"),
        question_runs=len(_QUESTION_RUN.findall(without_urls)),
        emoji=emoji,
        symbols=symbols,
        devanagari_tokens=devanagari,
        roman_markers=markers,
        word_tokens=word_tokens,
        repost_line=repost_line,
        repost_phrase=repost_phrase,
        repost_word_in_text=_REPOSTED_WORD.search(text) is not None,
        follow_lines=follow_lines,
    )
