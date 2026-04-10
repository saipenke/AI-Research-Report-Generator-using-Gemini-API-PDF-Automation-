"""
utils/text_cleaner.py
----------------------
Cleans raw scraped web text before it goes into the PDF.
Removes: Wikipedia markup, URL-encoded strings, redirect notices,
         wiki templates, social share buttons, garbage metadata, etc.
"""

import re
from typing import List


# ── Patterns to DELETE entirely ──────────────────────────────────

_DELETE_PATTERNS = [
    # Wikipedia redirect / template markup
    r"\{\{[^}]*\}\}",                          # {{template stuff}}
    r"\[\[Wikipedia[^\]]*\]\]",               # [[Wikipedia:...]]
    r"#REDIRECT\s+\S+",                        # #REDIRECT target
    r"\[subst\s*:[^\]]+\]",                   # [subst: ...]
    r"subst\s*:\s*\w+[^\s]*",                # subst:Rfd notice
    r"~~~~",                                   # wiki signatures
    r"(?:talk|user|file|template)\s+page",    # wiki page references

    # URL-encoded garbage
    r"%[0-9A-Fa-f]{2}(?:[0-9A-Fa-f]{2})+",  # %5B%5D etc.
    r"https?://\S+",                           # bare URLs in body text

    # Social media / share buttons
    r"\b(?:Share|Tweet|Print|Email|Copy\s+Link|LinkedIn|Pinterest|"
      r"Reddit|Flipboard|Bluesky|Facebook)\b",
    r"copied\b",                               # "Link copied"
    r"Leer en espa[ñn]ol",
    r"Add AP News[^.]*\.",
    r"Add \w+ as your[^.]*\.",

    # Wikipedia boilerplate
    r"This page is a redirect[^.]*\.",
    r"The following categories are used[^.]*\.",
    r"From a page move[^.]*\.",
    r"This is a redirect from[^.]*\.",
    r"This title is currently a redirect[^.]*\.",
    r"click there to go to the current target\.",
    r"It has been suggested that[^.]*\.",
    r"Proposed since \w+ \d{4}\.",
    r"Please notify[^.]*\.",
    r"debate closed as delete",
    r"From Wikipedia[^.]*\.",
    r"This article is about[^.]*\.",

    # Metadata noise
    r"Published\s*\d+\s*(?:hours?|days?|minutes?)\s*ago",
    r"By\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,5}Published[^.]*",
    r"\(AP Photo/[^)]+\)",
    r"\.svg\.png",
    r"FlagofRussia\.svg\.png",

    # Navigation / header fragments
    r"\b(?:Home|Menu|Search|Subscribe|Login|Sign\s+in|Sign\s+up|"
      r"Newsletter|Cookie|Privacy\s+Policy|Terms\s+of\s+Service)\b",
]

_DELETE_RE = re.compile("|".join(_DELETE_PATTERNS), re.IGNORECASE)


# ── Sentence-level quality filters ───────────────────────────────

def _is_garbage_sentence(s: str) -> bool:
    """Return True if the sentence should be discarded."""
    s = s.strip()

    # Too short or too long
    if len(s) < 25 or len(s) > 500:
        return True

    # Mostly non-alphabetic (wiki markup / encoded)
    alpha_ratio = sum(c.isalpha() for c in s) / max(len(s), 1)
    if alpha_ratio < 0.55:
        return True

    # Contains URL remnants
    if re.search(r"https?://|www\.", s):
        return True

    # Wiki / template patterns
    bad_fragments = [
        "{{", "}}", "~~~~", "subst:", "#redirect",
        "talk page", "redirect page", "redirect categories",
        "page move", "categories are used",
        "%5b", "%5d", "%3a",          # URL-encoded [ ] :
        "leer en español", "ap photo",
        "svg.png", "flag of",
    ]
    lower = s.lower()
    if any(frag in lower for frag in bad_fragments):
        return True

    # Starts with punctuation or looks like a menu item
    if re.match(r"^[|•\-–—*#@><\[\]{}/\\]", s):
        return True

    return False


# ── Public API ────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    """
    Full cleaning pipeline for a block of raw scraped text.

    1. Strip markup / encoded strings / social buttons.
    2. Collapse whitespace.
    3. Remove garbage sentences.
    4. Re-join into clean paragraphs.
    """
    if not text:
        return ""

    # Stage 1: pattern deletion
    text = _DELETE_RE.sub(" ", text)

    # Stage 2: collapse whitespace
    text = re.sub(r"\s{2,}", " ", text).strip()

    # Stage 3: sentence-level filtering
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
    clean     = [s.strip() for s in sentences if not _is_garbage_sentence(s)]

    return " ".join(clean)


def clean_section(text: str) -> str:
    """Clean a single section that may already be bullet-formatted."""
    if not text:
        return ""

    lines  = text.split("\n")
    result = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        is_bullet = line.startswith(("- ", "• ", "* "))
        prefix    = ""
        if is_bullet:
            prefix = "- "
            line   = re.sub(r"^[-•*]\s+", "", line)

        cleaned = clean_text(line)
        if cleaned and len(cleaned) > 20:
            result.append(prefix + cleaned)

    return "\n".join(result)


def clean_research_data(data: dict) -> dict:
    """
    Apply cleaning to every text section in the research data dict.
    Preserves all keys; cleans all string values.
    """
    text_keys   = ["introduction", "background", "key_concepts",
                   "insights", "applications", "conclusion"]
    bullet_keys = ["key_concepts", "applications"]

    cleaned = dict(data)

    for key in text_keys:
        val = cleaned.get(key, "")
        if not val:
            continue
        if key in bullet_keys:
            cleaned[key] = clean_section(val)
        else:
            cleaned[key] = clean_text(val)

    # Clean references — remove any that are just raw URLs or garbage
    refs = cleaned.get("references", [])
    good_refs = []
    for ref in refs:
        ref = ref.strip()
        # Remove URL-only entries; keep "Title — URL" or "Title" entries
        if ref and len(ref) > 10 and not re.match(r"^https?://\S+$", ref):
            # Strip bare URLs from within the reference text
            ref = re.sub(r"\s*—\s*https?://\S+", "", ref).strip()
            if ref:
                good_refs.append(ref)
    cleaned["references"] = good_refs

    return cleaned
