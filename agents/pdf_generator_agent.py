"""
agents/pdf_generator_agent.py
------------------------------
Agent 3 — PDF Report Generator Agent

Responsibilities:
  - Receive validated research content from the Validator Agent
  - Delegate PDF construction to utils/pdf_generator.py
  - Return the path to the saved PDF file
"""

import logging
from typing import Dict, Any

from utils.pdf_generator import generate_pdf

logger = logging.getLogger(__name__)

OUTPUT_DIR = "generated_reports"


def run_pdf_generator_agent(
    validated_data: Dict[str, Any],
    output_dir: str = OUTPUT_DIR,
) -> str:
    """
    Execute the PDF Generator Agent.

    Args:
        validated_data: Cleaned research dict from run_validator_agent().
        output_dir: Folder where the PDF will be saved.

    Returns:
        Absolute file path of the generated PDF.

    Raises:
        RuntimeError: If PDF generation fails.
    """
    topic = validated_data.get("topic", "Research Report")
    logger.info(f"[PDFGeneratorAgent] Generating PDF for: '{topic}'")

    print("  📄  Building PDF layout...")

    try:
        pdf_path = generate_pdf(validated_data, output_dir=output_dir)
        logger.info(f"[PDFGeneratorAgent] PDF saved: {pdf_path}")
        return pdf_path

    except Exception as e:
        logger.exception(f"[PDFGeneratorAgent] PDF generation failed: {e}")
        raise RuntimeError(f"PDF generation failed: {e}") from e
