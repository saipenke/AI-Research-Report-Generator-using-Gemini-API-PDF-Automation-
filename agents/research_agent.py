"""
agents/research_agent.py
-------------------------
Agent 1 — Research Agent

Works in two modes:
  • WITH OpenAI key  → full LLM synthesis (rich, structured content)
  • WITHOUT key      → intelligent rule-based synthesis from scraped text
                       (still produces a proper PDF, not an empty one)
"""

import os
import re
import json
import logging
from typing import Dict, Any, List

from tools.web_search_tool import search_web
from tools.scraping_tool   import scrape_multiple

logger = logging.getLogger(__name__)

SECTION_KEYS = [
    "introduction", "background", "key_concepts",
    "insights", "applications", "conclusion",
]

RESEARCH_SYSTEM_PROMPT = """You are an expert research analyst.
Synthesise the raw web data below into a structured JSON research report.

Respond with ONLY a valid JSON object — no markdown fences, no preamble — using exactly these keys:

{
  "introduction":  "<2-3 paragraph overview>",
  "background":    "<historical context and evolution>",
  "key_concepts":  "<core terms and principles — use lines starting with '- '>",
  "insights":      "<important findings, statistics, trends>",
  "applications":  "<real-world use cases — use lines starting with '- '>",
  "conclusion":    "<summary and future outlook>",
  "references":    ["<title — URL>", ...]
}

Requirements:
- Each section must be at least 150 words.
- Use professional, neutral academic English.
- Include at least 5 references.
"""


def run_research_agent(topic: str) -> Dict[str, Any]:
    """Run the full Research Agent pipeline."""
    logger.info(f"[ResearchAgent] Starting research on: '{topic}'")

    # ── Step 1: Web Search ────────────────────────────────────────
    print("  🔍  Searching the web...")
    queries = [
        topic,
        f"{topic} overview history",
        f"{topic} applications and use cases",
        f"{topic} latest trends challenges future",
    ]

    all_results: List[Dict] = []
    for q in queries:
        hits = search_web(q, max_results=6)
        all_results.extend(hits)

    # Deduplicate by URL
    seen, unique = set(), []
    for r in all_results:
        if r["url"] and r["url"] not in seen:
            seen.add(r["url"])
            unique.append(r)

    logger.info(f"[ResearchAgent] {len(unique)} unique results collected.")

    # ── Step 2: Scrape top pages ──────────────────────────────────
    print("  🌐  Scraping top pages for deeper content...")
    top_urls = [r["url"] for r in unique[:8] if r["url"].startswith("http")]
    scraped  = scrape_multiple(top_urls, max_chars_each=3000)
    logger.info(f"[ResearchAgent] Scraped {len(scraped)} pages successfully.")

    # ── Step 3: Build context ─────────────────────────────────────
    context_parts = []
    for r in unique[:15]:
        context_parts.append(
            f"TITLE: {r['title']}\nURL: {r['url']}\nSNIPPET: {r['content'][:800]}\n"
        )
    for url, text in scraped.items():
        context_parts.append(f"SCRAPED: {url}\n{text}\n")

    raw_context = "\n---\n".join(context_parts)

    # ── Step 4: Synthesise ────────────────────────────────────────
    print("  🤖  Synthesising research with AI...")

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    has_key = api_key and not api_key.startswith("your_") and len(api_key) > 20

    if has_key:
        try:
            structured = _llm_synthesise(topic, raw_context, api_key)
            structured["topic"] = topic
            logger.info("[ResearchAgent] LLM synthesis complete.")
            return structured
        except Exception as e:
            logger.warning(f"[ResearchAgent] LLM failed ({e}), using rule-based synthesis.")

    # Rule-based synthesis (no API key needed)
    structured = _rule_based_synthesis(topic, unique, scraped)
    structured["topic"] = topic
    logger.info("[ResearchAgent] Rule-based synthesis complete.")
    return structured


# ══════════════════════════════════════════════════════════════════
# LLM synthesis
# ══════════════════════════════════════════════════════════════════

def _llm_synthesise(topic: str, raw_context: str, api_key: str) -> Dict[str, Any]:
    import openai
    client = openai.OpenAI(api_key=api_key)
    model  = os.getenv("LLM_MODEL", "gpt-4o-mini")

    user_prompt = (
        f"Research Topic: {topic}\n\n"
        f"Raw Web Data:\n{raw_context[:14000]}\n\n"
        "Generate the structured JSON report now."
    )

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": RESEARCH_SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=0.4,
        max_tokens=4000,
    )
    raw = resp.choices[0].message.content.strip()
    return _parse_json(raw)


def _parse_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text  = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return json.loads(m.group())
        raise


# ══════════════════════════════════════════════════════════════════
# Rule-based synthesis (runs when no API key is available)
# ══════════════════════════════════════════════════════════════════

def _rule_based_synthesis(
    topic: str,
    results: List[Dict],
    scraped: Dict[str, str],
) -> Dict[str, Any]:
    """
    Build a proper research structure directly from search snippets
    and scraped page text — no LLM needed.
    """
    # Collect all available text
    snippets = [r["content"] for r in results if r.get("content")]
    pages    = list(scraped.values())
    all_text = snippets + pages
    combined = " ".join(all_text)

    # Split into sentences for intelligent section filling
    sentences = _split_sentences(combined)

    # Assign sentences to sections based on keyword matching
    buckets: Dict[str, List[str]] = {k: [] for k in SECTION_KEYS}

    intro_kw       = {"overview", "introduction", "refers to", "is a", "defined as",
                      "known as", "means", "describes", "represents"}
    background_kw  = {"history", "historically", "origin", "developed", "evolution",
                      "since", "decade", "century", "traditional", "early", "past"}
    concepts_kw    = {"concept", "term", "defined", "principle", "theory", "approach",
                      "method", "technique", "algorithm", "model", "framework", "type"}
    insights_kw    = {"study", "research", "found", "shows", "percent", "%", "billion",
                      "million", "increase", "decrease", "growth", "report", "data",
                      "according", "statistics", "survey"}
    applications_kw= {"used", "uses", "application", "applied", "industry", "sector",
                      "example", "case", "implement", "deploy", "solution", "tool",
                      "platform", "system", "product", "service"}
    conclusion_kw  = {"future", "challenge", "opportunity", "recommend", "conclusion",
                      "outlook", "prospect", "potential", "next", "will", "should",
                      "important", "critical", "need"}

    kw_map = [
        ("introduction",  intro_kw),
        ("background",    background_kw),
        ("key_concepts",  concepts_kw),
        ("insights",      insights_kw),
        ("applications",  applications_kw),
        ("conclusion",    conclusion_kw),
    ]

    for sent in sentences:
        lower = sent.lower()
        for section, kws in kw_map:
            if any(kw in lower for kw in kws):
                if len(buckets[section]) < 20:   # cap at 20 sentences per section
                    buckets[section].append(sent.strip())
                break

    def _fill(key: str, min_sentences: int = 5) -> str:
        sents = buckets[key]
        # If bucket is empty or thin, pull from general pool
        if len(sents) < min_sentences:
            pool = [s for s in sentences if s not in sents]
            sents = sents + pool[:max(0, min_sentences - len(sents))]
        return " ".join(sents[:15])   # up to 15 sentences per section

    # Build references list
    references = []
    for r in results:
        if r.get("title") and r.get("url"):
            references.append(f"{r['title']} — {r['url']}")
    for url in scraped:
        ref = f"Web Source — {url}"
        if ref not in references:
            references.append(ref)

    # Compose introduction with topic context
    intro_base = _fill("introduction")
    introduction = (
        f"{topic.title()} is a significant and rapidly evolving field with wide-ranging "
        f"implications across multiple domains. This report provides a comprehensive "
        f"overview based on current research, industry developments, and expert analysis.\n\n"
        f"{intro_base}"
    )

    # Compose conclusion with topic context
    conc_base = _fill("conclusion")
    conclusion = (
        f"{conc_base}\n\n"
        f"In summary, {topic} continues to develop as a critical area of focus for "
        f"researchers, practitioners, and policymakers alike. Further investment in "
        f"research and cross-sector collaboration will be essential to fully realise "
        f"its potential and address the challenges ahead."
    )

    # Format key concepts as bullet list
    concept_sents = buckets["key_concepts"]
    if concept_sents:
        key_concepts = "\n".join(f"- {s}" for s in concept_sents[:12])
    else:
        key_concepts = _fill("key_concepts")

    # Format applications as bullet list
    app_sents = buckets["applications"]
    if app_sents:
        applications = "\n".join(f"- {s}" for s in app_sents[:12])
    else:
        applications = _fill("applications")

    return {
        "introduction":  introduction,
        "background":    _fill("background"),
        "key_concepts":  key_concepts,
        "insights":      _fill("insights"),
        "applications":  applications,
        "conclusion":    conclusion,
        "references":    references[:10],
    }


def _split_sentences(text: str) -> List[str]:
    """Split text into clean sentences."""
    text = re.sub(r"\s+", " ", text).strip()
    raw  = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
    # Filter: keep sentences between 20 and 400 chars
    return [s.strip() for s in raw if 20 < len(s.strip()) < 400]
