import os
import sys
import time
import logging

# ── Load environment variables from .env ─────────────────────────
from dotenv import load_dotenv
load_dotenv()

# ── Logging configuration ─────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("agent_run.log", mode="w", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ── Import agents ─────────────────────────────────────────────────
from agents.research_agent       import run_research_agent
from agents.validator_agent      import run_validator_agent
from agents.pdf_generator_agent  import run_pdf_generator_agent


# ════════════════════════════════════════════════════════════════
# Banner
# ════════════════════════════════════════════════════════════════

BANNER = r"""
╔══════════════════════════════════════════════════════════════╗
║         Multi-Agent AI Research PDF Generator               ║
║         Powered by Google ADK + OpenAI + ReportLab          ║
╚══════════════════════════════════════════════════════════════╝
"""


# ════════════════════════════════════════════════════════════════
# Pipeline orchestrator
# ════════════════════════════════════════════════════════════════

def run_pipeline(topic: str) -> str:
    """
    Run the full three-agent pipeline for a given topic.

    Args:
        topic: Research topic string.

    Returns:
        Path to the generated PDF file.
    """
    total_start = time.time()

    # ── Agent 1: Research ─────────────────────────────────────────
    print("\n" + "─" * 60)
    print("📚  AGENT 1 — Research Agent")
    print("─" * 60)
    print("Researching topic...")
    t0 = time.time()
    research_data = run_research_agent(topic)
    print(f"✅  Research complete  ({time.time() - t0:.1f}s)")

    # ── Agent 2: Validator ────────────────────────────────────────
    print("\n" + "─" * 60)
    print("🔍  AGENT 2 — Validator Agent")
    print("─" * 60)
    print("Validating content...")
    t0 = time.time()
    validated_data = run_validator_agent(research_data)
    print(f"✅  Validation complete  ({time.time() - t0:.1f}s)")

    # ── Agent 3: PDF Generator ────────────────────────────────────
    print("\n" + "─" * 60)
    print("📄  AGENT 3 — PDF Generator Agent")
    print("─" * 60)
    print("Generating PDF...")
    t0 = time.time()
    pdf_path = run_pdf_generator_agent(validated_data)
    print(f"✅  PDF saved  ({time.time() - t0:.1f}s)")

    print("\n" + "═" * 60)
    elapsed = time.time() - total_start
    print(f"🎉  PDF saved successfully!")
    print(f"📁  Location : {pdf_path}")
    print(f"⏱️   Total time: {elapsed:.1f}s")
    print("═" * 60 + "\n")

    return pdf_path


# ════════════════════════════════════════════════════════════════
# CLI entry point
# ════════════════════════════════════════════════════════════════

def main():
    print(BANNER)

    # Get topic from CLI arg or interactive prompt
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:]).strip()
        print(f"Topic (from argument): {topic}")
    else:
        topic = input("Enter research topic: ").strip()

    if not topic:
        print("❌  No topic provided. Exiting.")
        sys.exit(1)

    logger.info(f"Pipeline starting for topic: '{topic}'")

    try:
        pdf_path = run_pipeline(topic)
        logger.info(f"Pipeline finished. Output: {pdf_path}")
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Pipeline error: {e}")
        print(f"\n❌  Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
