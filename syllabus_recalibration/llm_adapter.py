"""
llm_adapter.py
--------------
LM Studio / Qwen2.5-3B-Instruct integration.

The LLM does ONLY two things:
  1. Parse user natural language -> structured JSON (module overrides + priorities)
  2. Format a human-readable narrative from the redistribution result

The LLM does NOT compute hours, weights, or touch any math.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI

from models import UserAdjustment

LM_STUDIO_BASE_URL = "http://localhost:1234/v1"
LM_STUDIO_API_KEY  = "lm-studio"
MODEL_ID           = "qwen2.5-coder-3b-instruct"

_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(base_url=LM_STUDIO_BASE_URL, api_key=LM_STUDIO_API_KEY)
    return _client


def _chat(system: str, user: str, max_tokens: int = 512) -> str:
    response = _get_client().chat.completions.create(
        model=MODEL_ID,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        max_tokens=max_tokens,
        temperature=0.1,
    )
    return response.choices[0].message.content.strip()


_PARSER_SYSTEM = """\
You are a JSON extraction assistant for a university course syllabus tool.
Your ONLY job is to extract structured data from the instructor's message.

You MUST reply with ONLY a valid JSON object - no explanation, no markdown fences.

The JSON must have exactly this structure:
{
  "adjustments": [
    {
      "module_name": "<exact module name>",
      "actual_hours": <float>,
      "confidence": <float 0-1>
    }
  ],
  "priority_modules": ["<module name>", ...],
  "notes": "<any extra context not captured above>"
}

Valid module names (use EXACTLY these strings):
  "Algorithm Analysis"
  "Linear Data Structures"
  "Searching and Sorting"
  "Trees"
  "Heaps and AVL Trees"
  "Graphs"
  "Hashing"

Rules:
- If the instructor says "we did X in N hours", set actual_hours = N.
- If the instructor says "give more time to X" or "focus on X", add X to priority_modules.
- If hours are ambiguous, set confidence < 0.7.
- If a module is not mentioned, do not include it in adjustments.
- Do not invent hours that were not stated.
"""

_MODULE_HOURS_CONTEXT = """\
Current baseline hours per module (for reference only - do not output these):
  Algorithm Analysis:     13.75h
  Linear Data Structures: 10.00h
  Searching and Sorting:   5.00h
  Trees:                   8.25h
  Heaps and AVL Trees:     2.75h
  Graphs:                  4.00h
  Hashing:                 1.25h
  TOTAL:                  45.00h
"""


def parse_user_prompt(
    prompt: str,
    module_hours: Optional[Dict[str, float]] = None,
) -> Tuple[List[UserAdjustment], List[int], str]:
    NAME_TO_ID = {
        "Algorithm Analysis":     1,
        "Linear Data Structures": 2,
        "Searching and Sorting":  3,
        "Trees":                  4,
        "Heaps and AVL Trees":    5,
        "Graphs":                 6,
        "Hashing":                7,
    }

    default_hours = {
        "Algorithm Analysis":     13.75,
        "Linear Data Structures": 10.00,
        "Searching and Sorting":   5.00,
        "Trees":                   8.25,
        "Heaps and AVL Trees":     2.75,
        "Graphs":                  4.00,
        "Hashing":                 1.25,
    }
    if module_hours:
        default_hours.update(module_hours)

    system_prompt = _PARSER_SYSTEM + "\n" + _MODULE_HOURS_CONTEXT
    raw = _chat(system_prompt, prompt, max_tokens=512)

    raw = re.sub(r"^```(?:json)?", "", raw.strip(), flags=re.IGNORECASE)
    raw = re.sub(r"```$", "", raw.strip())

    try:
        parsed: Dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError:
        print(f"[llm_adapter] JSON parse failed. Raw output:\n{raw}")
        return [], [], "LLM parse failed - no adjustments extracted."

    adjustments: List[UserAdjustment] = []
    for item in parsed.get("adjustments", []):
        name = item.get("module_name", "")
        mid  = NAME_TO_ID.get(name)
        if mid is None:
            print(f"[llm_adapter] Unknown module name: '{name}' - skipped.")
            continue

        actual   = float(item.get("actual_hours", 0.0))
        original = default_hours.get(name, 0.0)
        saved    = round(original - actual, 4)
        velocity = round(actual / original, 4) if original > 0 else 1.0
        conf     = float(item.get("confidence", 0.5))

        adjustments.append(UserAdjustment(
            module_id=mid,
            module_name=name,
            actual_hours=actual,
            original_hours=original,
            saved_hours=saved,
            velocity=velocity,
            confidence=conf,
        ))

    priority_names: List[str] = parsed.get("priority_modules", [])
    priority_ids = [NAME_TO_ID[n] for n in priority_names if n in NAME_TO_ID]
    notes: str = parsed.get("notes", "")

    return adjustments, priority_ids, notes


# ---------------------------------------------------------------------------
# Narrative formatter
# ---------------------------------------------------------------------------

_NARRATOR_SYSTEM = """\
You are an academic assistant writing a brief narrative summary of a revised course syllabus.
You will receive JSON describing which modules changed and by how much.
Write 3-4 sentences in plain professional English. Flowing prose only, no bullet points or lists.

STRICT RULES:
- The total course hours are ALWAYS 45h before and after. Never say the total changed.
- Only mention modules where delta is non-zero.
- Do not invent any numbers. Use only the exact delta values in the JSON.
- SAVED scenario means the module finished EARLY so saved hours went TO other modules (they increased).
- OVERRUN scenario means the module took LONGER so hours were TAKEN FROM other modules (they decreased).
- Never mix up SAVED and OVERRUN. Read the scenario field carefully before writing.
"""


def format_narrative(result_summary: Dict[str, Any]) -> str:
    total_orig  = sum(m["old_h"] for m in result_summary["modules"])
    total_recal = sum(m["new_h"] for m in result_summary["modules"])
    saved       = result_summary["total_saved"]

    # Explicit scenario label — removes all ambiguity for the LLM
    if saved > 0:
        scenario = (
            f"SAVED: The adjusted module finished {saved:.2f}h ahead of schedule. "
            f"Those hours were freed up and redistributed TO other modules, which is why those modules show increases."
        )
    else:
        scenario = (
            f"OVERRUN: The adjusted module ran {abs(saved):.2f}h over schedule. "
            f"Those extra hours were borrowed FROM other modules, which is why those modules show decreases."
        )

    changed_modules = [
        m for m in result_summary["modules"] if abs(m["delta"]) > 0.01
    ]

    clean_summary = {
        "scenario": scenario,
        "changed_modules": changed_modules,
        "total_hours": 45.0,
        "notes": result_summary.get("notes", ""),
    }

    system = _NARRATOR_SYSTEM + f"""
VERIFIED FACTS (do not contradict these):
- {scenario}
- Total hours before recalibration: {total_orig:.2f}h
- Total hours after recalibration:  {total_recal:.2f}h
- These two numbers are identical. The total never changes.
"""

    try:
        return _chat(system, json.dumps(clean_summary, indent=2), max_tokens=400)
    except Exception as e:
        return f"[Narrative unavailable - LM Studio not reachable: {e}]"