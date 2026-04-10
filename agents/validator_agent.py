"""
agents/validator_agent.py
--------------------------
Agent 2 — Validator Agent

Responsibilities:
  - Receive structured research content from Research Agent
  - Strip Wikipedia markup, URL-encoded strings, social buttons, garbage
  - Remove duplicate sentences
  - LLM quality pass (if API key available)
  - Return clean, professional research data
"""

import os
import re
import json
import logging
from typing import Dict, Any

from utils.text_cleaner import clean_research_data

logger = logging.getLogger(__name__)

VALIDATOR_SYSTEM_PROMPT = """You are a senior research editor.
You will receive a JSON research report that may contain incomplete or rough content.

Your job:
1. Keep ALL original keys intact.
2. Rewrite each section in clear, professional, academic English.
3. Remove any remaining Wikipedia markup, URL-encoded text, or web garbage.
4. Ensure each section is fully relevant to the topic.
5. If a section is thin (<80 words), expand it logically.
6. Keep the best 5-8 references; remove duplicates.
7. Respond with ONLY valid JSON — no markdown, no explanation.

IMPORTANT: The output must read like a professional research report.
No wiki syntax, no {{templates}}, no ~~~~, no %5B encoded strings.
"""

REQUIRED_KEYS = [
    "introduction", "background", "key_concepts",
    "insights", "applications", "conclusion",
]


def run_validator_agent(research_data: Dict[str, Any]) -> Dict[str, Any]:
    topic = research_data.get("topic", "Unknown Topic")
    logger.info(f"[ValidatorAgent] Validating research for: '{topic}'")

    # Step 1: Deep text cleaning
    print("  🧹  Cleaning markup, URLs, and garbage text...")
    cleaned = clean_research_data(research_data)

    # Step 2: Structural validation
    print("  🔎  Checking research structure...")
    issues = _check_structure(cleaned)
    for issue in issues:
        logger.warning(f"[ValidatorAgent] {issue}")

    # Step 3: Sentence deduplication
    print("  ✂️   Removing duplicate sentences...")
    cleaned = _dedup_all_sections(cleaned)

    # Step 4: LLM quality pass (optional)
    print("  ✨  Improving content quality with AI...")
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    has_key = api_key and not api_key.startswith("your_") and len(api_key) > 20

    if has_key:
        try:
            improved = _llm_improve(cleaned, api_key)
            improved = clean_research_data(improved)
            improved["topic"] = topic
            logger.info("[ValidatorAgent] LLM pass complete.")
            return improved
        except Exception as e:
            logger.warning(f"[ValidatorAgent] LLM pass skipped: {e}")

    cleaned["topic"] = topic
    logger.info("[ValidatorAgent] Validation complete (no LLM pass).")
    return cleaned


def _check_structure(data):
    issues = []
    for key in REQUIRED_KEYS:
        val = data.get(key, "")
        if not val or not val.strip():
            issues.append(f"Missing section: '{key}'")
        elif len(val.split()) < 30:
            issues.append(f"Section '{key}' is short ({len(val.split())} words)")
    if not data.get("references"):
        issues.append("No references found")
    return issues


def _dedup_all_sections(data):
    result = dict(data)
    for key in REQUIRED_KEYS:
        text = result.get(key, "")
        if text:
            result[key] = _dedup_sentences(text)
    return result


def _dedup_sentences(text):
    sentences = re.split(r"(?<=[.!?])\s+", text)
    seen, unique = set(), []
    for s in sentences:
        norm = re.sub(r"\s+", " ", s.lower().strip())
        if norm and norm not in seen and len(norm) > 15:
            seen.add(norm)
            unique.append(s.strip())
    return " ".join(unique)


def _llm_improve(data, api_key):
    import openai
    model  = os.getenv("LLM_MODEL", "gpt-4o-mini")
    client = openai.OpenAI(api_key=api_key)

    user_prompt = (
        f"Topic: {data.get('topic', 'Unknown')}\n\n"
        f"Research JSON:\n{json.dumps(data, indent=2)[:10000]}\n\n"
        "Return the improved, clean JSON."
    )

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": VALIDATOR_SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=4000,
    )

    raw = resp.choices[0].message.content.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw   = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        improved = json.loads(raw)
        improved.setdefault("topic", data.get("topic", ""))
        return improved
    except json.JSONDecodeError:
        logger.warning("[ValidatorAgent] LLM returned invalid JSON — using cleaned data.")
        return data
