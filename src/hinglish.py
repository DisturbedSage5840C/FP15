"""Possible Hinglish: Hindi written in Latin letters, found with a list of common romanised function words.

The list holds function words only (pronouns, particles, postpositions, auxiliaries, conjunctions, question
words). It holds no names and no text taken from the posts. A word that is also a common English word is
left out on purpose (for example the, to, do, me, main, is, so, par, tab, mat, hi), so the flag can miss
Hindi that is written with only those words. The flag says "possible": it is a counting rule, not a reading
of the text, and the committed report states its precision once a human has checked a sample.
"""
from __future__ import annotations

import re

HINGLISH_WORDS: frozenset[str] = frozenset(
    {
        # auxiliaries and verb endings
        "hai", "hain", "tha", "thi", "hoga", "hogi", "honge", "hota", "hoti", "hote", "hua", "hui", "hue",
        "raha", "rahi", "rahe", "gaya", "gayi", "gaye", "kar", "karna", "karo", "karke", "kiya", "kiye",
        "kare", "karein", "sakta", "sakti", "sakte", "chahiye",
        # question words
        "kya", "kyun", "kyon", "kyunki", "kaise", "kaisa", "kaisi", "kaun", "kab", "kahan", "kitna", "kitni",
        "kitne",
        # negation, conjunctions, adverbs
        "nahi", "nahin", "aur", "lekin", "magar", "agar", "toh", "bhi", "sirf", "abhi", "jab", "phir",
        "isliye", "yahan", "wahan", "bahut", "bohot", "bilkul", "jaise", "jaisa",
        # pronouns and possessives
        "yeh", "ye", "woh", "wo", "iss", "uss", "isse", "usse", "mein", "mujhe", "hum", "humein", "hamara",
        "hamari", "hamare", "tum", "tumhara", "aap", "aapka", "aapki", "aapke", "apna", "apni", "apne", "mera",
        "meri", "mere", "uska", "uski", "unka", "unki", "unke", "jis", "jisse", "sab", "sabhi", "sabko",
        "kuch", "koi",
        # postpositions and particles
        "ka", "ki", "ke", "ko", "se", "ne", "ek", "liye", "saath", "baad", "pehle", "tak", "wala", "wali",
        "wale",
    }
)
_LATIN_WORD = re.compile(r"[a-z]+")


def hinglish_hits(text: str) -> tuple[int, int]:
    """(words found in the list, all Latin-letter words) in the text, compared in lower case."""
    words = _LATIN_WORD.findall(text.lower())
    return sum(word in HINGLISH_WORDS for word in words), len(words)
