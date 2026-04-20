"""
pipeline.py
-----------
Main orchestrator for the Adaptive Syllabus Recalibration Engine.

Usage
-----
  python pipeline.py
  python pipeline.py "We finished algorithm analysis in 4 hours. Give more time to Trees."

Programmatic usage
------------------
  from pipeline import run_recalibration
  result, narrative, paths = run_recalibration(user_prompt="...", export_formats=["csv","html","docx","pdf"])
"""

from __future__ import annotations

import sys
from typing import Dict, List, Optional, Tuple

from bridge_loader import load_from_pyq_system
from llm_adapter import parse_user_prompt, format_narrative
from models import Module, RedistributionResult, UserAdjustment
from redistribution_engine import RedistributionEngine
from exporters import export_all

# ---------------------------------------------------------------------------
# File paths (adjust if your JSONs live elsewhere)
# ---------------------------------------------------------------------------
CURRICULUM_PATH     = "adaptive_curriculum.json"
TOPIC_ANALYSIS_PATH = "topic_analysis.json"
BOOK_WEIGHTS_PATH   = "book_weights.json"

DEFAULT_PROMPT = (
    "We completed Algorithm Analysis in 6 hours instead of 13.75. "
    "Please give more time to Trees and Graphs."
)


# ---------------------------------------------------------------------------
# Console summary table
# ---------------------------------------------------------------------------

def _print_summary(result: RedistributionResult) -> None:
    print("\n" + "=" * 76)
    print(f"  {'Module':<26} {'Old h':>6}  {'New h':>6}  {'Delta':>7}  "
          f"{'Importance':<12} {'Difficulty'}")
    print("-" * 76)
    for orig, recal in zip(
        sorted(result.original_modules,     key=lambda m: m.module_id),
        sorted(result.recalibrated_modules, key=lambda m: m.module_id),
    ):
        delta = recal.allocated_hours - orig.original_hours
        delta_str = f"{delta:+.2f}h"
        print(
            f"  {orig.module_name:<26} {orig.original_hours:>5.2f}h"
            f"  {recal.allocated_hours:>5.2f}h  {delta_str:>7}  "
            f"{recal.importance.value:<12} {recal.difficulty.value}"
        )
    print("-" * 76)
    total_orig  = sum(m.original_hours   for m in result.original_modules)
    total_recal = sum(m.allocated_hours  for m in result.recalibrated_modules)
    print(f"  {'TOTAL':<26} {total_orig:>5.2f}h  {total_recal:>5.2f}h")
    print("=" * 76)

    if result.warnings:
        print("\nWARNINGS:")
        for w in result.warnings:
            print(f"  ⚠  {w}")

    if result.adjustment_log:
        print("\nADJUSTMENT LOG:")
        for entry in result.adjustment_log:
            print(f"  · {entry}")
    print()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_recalibration(
    user_prompt: str,
    curriculum_path: str = CURRICULUM_PATH,
    analysis_path: str   = TOPIC_ANALYSIS_PATH,
    book_weights_path: str = BOOK_WEIGHTS_PATH,
    export_formats: List[str] = None,
    output_dir: str = "output",
) -> Tuple[RedistributionResult, str, dict]:
    """
    Full pipeline: load → parse → redistribute → export.

    Returns
    -------
    (RedistributionResult, narrative_text, {format: output_path})
    """
    export_formats = export_formats or ["csv", "html", "docx","pdf"]

    # 1. Load System 1 outputs → 7 Module objects
    print("[pipeline] Loading System 1 outputs via bridge_loader …")
    modules: List[Module] = load_from_pyq_system(
        curriculum_path=curriculum_path,
        analysis_path=analysis_path,
        book_weights_path=book_weights_path,
    )
    print(f"[pipeline] Loaded {len(modules)} modules. "
          f"Total hours: {sum(m.original_hours for m in modules):.2f}h")

    # 2. Parse user prompt via LLM
    print("[pipeline] Parsing user prompt …")
    module_hours = {m.module_name: m.original_hours for m in modules}
    try:
        adjustments, priority_ids, notes = parse_user_prompt(user_prompt, module_hours)
        print(f"[pipeline] Parsed {len(adjustments)} adjustment(s), "
              f"{len(priority_ids)} priority module(s).")
    except Exception as e:
        print(f"[pipeline] LLM parse error: {e}")
        print("[pipeline] Falling back to zero adjustments (LM Studio may not be running).")
        adjustments, priority_ids, notes = [], [], ""

    # 3. Redistribute hours
    print("[pipeline] Running redistribution engine …")
    engine = RedistributionEngine()
    result = engine.redistribute(modules, adjustments, priority_module_ids=priority_ids)

    # 4. Print console summary
    _print_summary(result)

    # 5. Build narrative summary dict for LLM formatter
    summary_for_llm = {
        "modules": [
            {
                "name":     recal.module_name,
                "old_h":    orig.original_hours,
                "new_h":    recal.allocated_hours,
                "delta":    round(recal.allocated_hours - orig.original_hours, 2),
            }
            for orig, recal in zip(
                sorted(result.original_modules,     key=lambda m: m.module_id),
                sorted(result.recalibrated_modules, key=lambda m: m.module_id),
            )
        ],
        "total_saved": result.total_saved,
        "notes": notes,
    }

    # 6. LLM narrative
    print("[pipeline] Generating narrative …")
    try:
        narrative = format_narrative(summary_for_llm)
    except Exception as e:
        narrative = f"[Narrative unavailable: {e}]"

    if narrative:
        print(f"\nNARRATIVE:\n{narrative}\n")

    # 7. Export
    print(f"[pipeline] Exporting to {export_formats} …")
    paths = export_all(result, narrative, formats=export_formats, output_dir=output_dir)

    print(f"\n[pipeline] Done. Output files: {list(paths.values())}")
    return result, narrative, paths


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else DEFAULT_PROMPT
    print(f"\n[pipeline] User prompt: \"{prompt}\"\n")
    run_recalibration(user_prompt=prompt)