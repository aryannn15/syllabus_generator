"""
bridge_loader.py
----------------
Reads System 1 outputs (adaptive_curriculum.json + topic_analysis.json)
and produces List[Module] for System 2's pipeline.

Key responsibilities:
  1. Load both JSON files
  2. Split System 1's "Trees" module into "Trees" (module_id=4) and
     "Heaps and AVL Trees" (module_id=5) using PYQ-derived ratios
  3. Compute per-module pyq_score from topic_analysis.json percentage_weights
  4. Use System 1's allocated hours as baseline (Option B)
  5. Map difficulty strings → DifficultyLevel enum
  6. Map importance scores → ImportanceLevel enum
  7. Load book_weights.json for book_weight field
  8. Return List[Module] in module_id order (1–7)
"""

import json
import os
from typing import List, Dict, Any

from models import Module, DifficultyLevel, ImportanceLevel


# ---------------------------------------------------------------------------
# PYQ percentage_weights per topic (from topic_analysis.json).
# Keyed by the EXACT topic name strings used in System 1.
# These are the canonical values from the handoff document.
# ---------------------------------------------------------------------------
TOPIC_PYQ_WEIGHTS: Dict[str, float] = {
    "Binary Trees":                   15.87,
    "Recurrence Relations":           14.22,
    "Time Complexity":                11.05,
    "Stack":                          10.19,
    "Heap":                            6.61,
    "Asymptotic Notation":             5.64,
    "Arrays":                          5.52,
    "Queue":                           5.31,
    "Bubble Sort":                     3.87,
    "Linked List":                     2.54,
    "Tree Traversals":                 2.54,
    "Algorithm Correctness":           2.15,
    "Algorithm Basics":                2.14,
    "Complexity Analysis (sorting-specific)": 1.96,
    "BST":                             1.94,
    "Dijkstra":                        1.94,
    "Insertion Sort":                  1.94,
    "DFS":                             1.45,
    "Minimum Spanning Tree":           0.97,
    "Hash Functions":                  0.51,
}

# Sum of all topic PYQ weights — used for normalization to [0, 1]
_TOTAL_PYQ_WEIGHT: float = sum(TOPIC_PYQ_WEIGHTS.values())  # ≈ 100.0


# ---------------------------------------------------------------------------
# Module-to-topic mapping (System 1 module name → list of topic names).
# "Trees" entry intentionally includes Heap because we split it programmatically.
# ---------------------------------------------------------------------------
MODULE_TOPICS: Dict[str, List[str]] = {
    "Algorithm Foundations": [
        "Algorithm Basics",
        "Time Complexity",
        "Asymptotic Notation",
        "Recurrence Relations",
        "Algorithm Correctness",
    ],
    "Linear Data Structures": [
        "Arrays",
        "Linked List",
        "Stack",
        "Queue",
    ],
    "Searching And Sorting": [
        "Bubble Sort",
        "Complexity Analysis (sorting-specific)",
        "Insertion Sort",
    ],
    # Full Trees block — will be split in code
    "Trees": [
        "Binary Trees",
        "Heap",
        "Tree Traversals",
        "BST",
    ],
    "Graphs": [
        "Dijkstra",
        "DFS",
        "Minimum Spanning Tree",
    ],
    "Hashing": [
        "Hash Functions",
    ],
}

# Topics that belong to the HEAP split (not the Trees split)
HEAP_TOPICS: List[str] = ["Heap"]

# Topics that stay in the Trees split
TREES_TOPICS: List[str] = ["Binary Trees", "Tree Traversals", "BST"]


# ---------------------------------------------------------------------------
# System 1 module → System 2 module mapping metadata
# ---------------------------------------------------------------------------
MODULE_MAP = [
    {
        "sys1_name": "Algorithm Foundations",
        "module_id": 1,
        "sys2_name": "Algorithm Analysis",
    },
    {
        "sys1_name": "Linear Data Structures",
        "module_id": 2,
        "sys2_name": "Linear Data Structures",
    },
    {
        "sys1_name": "Searching And Sorting",
        "module_id": 3,
        "sys2_name": "Searching and Sorting",
    },
    # Trees split is handled separately below (module_id 4 & 5)
    {
        "sys1_name": "Graphs",
        "module_id": 6,
        "sys2_name": "Graphs",
    },
    {
        "sys1_name": "Hashing",
        "module_id": 7,
        "sys2_name": "Hashing",
    },
]


# ---------------------------------------------------------------------------
# Helper: normalize a raw percentage_weight sum to [0, 1] over all 20 topics
# ---------------------------------------------------------------------------
def _normalize_pyq(raw_sum: float) -> float:
    """Divide a sum of percentage_weights by the grand total to get [0,1]."""
    return raw_sum / _TOTAL_PYQ_WEIGHT


# ---------------------------------------------------------------------------
# Helper: map System 1 difficulty string → DifficultyLevel enum
# ---------------------------------------------------------------------------
def _map_difficulty(difficulty_str: str) -> DifficultyLevel:
    mapping = {
        "easy":     DifficultyLevel.EASY,
        "moderate": DifficultyLevel.MEDIUM,
        "hard":     DifficultyLevel.HARD,
    }
    return mapping.get(difficulty_str.lower(), DifficultyLevel.MEDIUM)


# ---------------------------------------------------------------------------
# Helper: map average_importance float → ImportanceLevel enum
# Thresholds derived from the handoff data range (0.51 – 7.04):
#   < 2.0  → LOW
#   2.0–4.5 → MEDIUM
#   4.5–6.5 → HIGH
#   >= 6.5  → VERY_HIGH
# ---------------------------------------------------------------------------
def _map_importance(avg_importance: float) -> ImportanceLevel:
    if avg_importance >= 6.5:
        return ImportanceLevel.VERY_HIGH
    elif avg_importance >= 4.5:
        return ImportanceLevel.HIGH
    elif avg_importance >= 2.0:
        return ImportanceLevel.MEDIUM
    else:
        return ImportanceLevel.LOW


# ---------------------------------------------------------------------------
# Helper: compute pyq_score for a list of topics
# ---------------------------------------------------------------------------
def _pyq_score_for_topics(topics: List[str]) -> float:
    raw = sum(TOPIC_PYQ_WEIGHTS.get(t, 0.0) for t in topics)
    return _normalize_pyq(raw)


# ---------------------------------------------------------------------------
# Core loader
# ---------------------------------------------------------------------------
def load_from_pyq_system(
    curriculum_path: str,
    analysis_path: str,
    book_weights_path: str = None,
) -> List[Module]:
    """
    Load System 1 outputs and return 7 Module objects ready for pipeline.py.

    Parameters
    ----------
    curriculum_path  : path to adaptive_curriculum.json
    analysis_path    : path to topic_analysis.json  (used for validation / future ext.)
    book_weights_path: path to book_weights.json (defaults to same dir as curriculum)

    Returns
    -------
    List[Module] sorted by module_id (1–7), total original_hours == 45.0
    """
    # ------------------------------------------------------------------
    # 1. Load JSON files
    # ------------------------------------------------------------------
    with open(curriculum_path, "r", encoding="utf-8") as f:
        curriculum: Dict[str, Any] = json.load(f)

    with open(analysis_path, "r", encoding="utf-8") as f:
        _analysis: Dict[str, Any] = json.load(f)  # kept for future extension

    # Resolve book_weights path
    if book_weights_path is None:
        base_dir = os.path.dirname(os.path.abspath(curriculum_path))
        book_weights_path = os.path.join(base_dir, "book_weights.json")

    with open(book_weights_path, "r", encoding="utf-8") as f:
        book_weights_raw: Dict[str, Any] = json.load(f)

    # Build quick lookup: sys2_module_name → book_weight float
    book_weights: Dict[str, float] = {
        name: data["book_weight"] for name, data in book_weights_raw.items()
    }

    # ------------------------------------------------------------------
    # 2. Index System 1 modules by name for easy lookup
    # ------------------------------------------------------------------
    sys1_modules: Dict[str, Dict[str, Any]] = {
        m["module"]: m for m in curriculum["modules"]
    }

    # ------------------------------------------------------------------
    # 3. Build modules 1, 2, 3, 6, 7 (straight mappings)
    # ------------------------------------------------------------------
    modules: List[Module] = []

    for entry in MODULE_MAP:
        sys1_name = entry["sys1_name"]
        module_id = entry["module_id"]
        sys2_name = entry["sys2_name"]

        sys1_mod = sys1_modules[sys1_name]
        topics = MODULE_TOPICS[sys1_name]
        hours = sys1_mod["total_hours"]

        mod = Module(
            module_id=module_id,
            module_name=sys2_name,
            original_hours=hours,
            topics=topics,
            allocated_hours=hours,           # baseline = System 1 hours (Option B)
            min_hours=max(1.0, len(topics) * 0.5),
            difficulty=_map_difficulty(sys1_mod["difficulty_level"]),
            importance=_map_importance(sys1_mod["average_importance"]),
            pyq_score=_pyq_score_for_topics(topics),
            book_weight=book_weights[sys2_name],
            velocity_signal=1.0,             # neutral until user feedback arrives
        )
        modules.append(mod)

    # ------------------------------------------------------------------
    # 4. Split Trees → module_id=4 "Trees" + module_id=5 "Heaps and AVL Trees"
    # ------------------------------------------------------------------
    sys1_trees = sys1_modules["Trees"]
    trees_total_hours: float = sys1_trees["total_hours"]  # 11.0h

    # PYQ-derived split ratio
    # Trees group total PYQ = 26.96% (from topic_groups in handoff)
    # Heap share within Trees group = 6.61%
    # Non-heap share = 26.96 - 6.61 = 20.35%
    trees_group_total: float = 26.96
    heap_pyq_share: float = TOPIC_PYQ_WEIGHTS["Heap"]     # 6.61
    non_heap_pyq_share: float = trees_group_total - heap_pyq_share  # 20.35

    # Hour allocation
    heaps_hours: float = round(
        trees_total_hours * (heap_pyq_share / trees_group_total) * 4
    ) / 4  # snap to 0.25h → 2.75h
    trees_hours: float = trees_total_hours - heaps_hours   # 8.25h

    # Importance: Trees block has average_importance = 6.74 → VERY_HIGH
    # We apply same importance to both splits (same block origin)
    trees_importance = _map_importance(sys1_trees["average_importance"])

    # Difficulty: Trees block = "Moderate" → MEDIUM
    trees_difficulty = _map_difficulty(sys1_trees["difficulty_level"])

    # Module 4 — Trees (Binary Trees, Tree Traversals, BST)
    mod_trees = Module(
        module_id=4,
        module_name="Trees",
        original_hours=trees_hours,
        topics=TREES_TOPICS,
        allocated_hours=trees_hours,
        min_hours=max(1.0, len(TREES_TOPICS) * 0.5),
        difficulty=trees_difficulty,
        importance=trees_importance,
        pyq_score=_pyq_score_for_topics(TREES_TOPICS),
        book_weight=book_weights["Trees"],
        velocity_signal=1.0,
    )

    # Module 5 — Heaps and AVL Trees
    mod_heaps = Module(
        module_id=5,
        module_name="Heaps and AVL Trees",
        original_hours=heaps_hours,
        topics=HEAP_TOPICS,
        allocated_hours=heaps_hours,
        min_hours=max(1.0, len(HEAP_TOPICS) * 0.5),
        difficulty=trees_difficulty,
        importance=trees_importance,
        pyq_score=_pyq_score_for_topics(HEAP_TOPICS),
        book_weight=book_weights["Heaps and AVL Trees"],
        velocity_signal=1.0,
    )

    modules.append(mod_trees)
    modules.append(mod_heaps)

    # ------------------------------------------------------------------
    # 5. Sort by module_id and validate total hours
    # ------------------------------------------------------------------
    modules.sort(key=lambda m: m.module_id)

    total = sum(m.original_hours for m in modules)
    assert abs(total - 45.0) < 0.01, (
        f"bridge_loader: total hours = {total:.2f}, expected 45.0. "
        "Check split logic."
    )

    return modules


# ---------------------------------------------------------------------------
# Diagnostic / smoke-test
# ---------------------------------------------------------------------------
def _print_summary(modules: List[Module]) -> None:
    print(f"\n{'='*72}")
    print(f"{'ID':<4} {'Module':<26} {'Hrs':>5}  {'PYQ':>6}  {'Book':>5}  "
          f"{'Diff':<8} {'Imp':<10}")
    print(f"{'-'*72}")
    total = 0.0
    for m in modules:
        print(
            f"{m.module_id:<4} {m.module_name:<26} {m.original_hours:>5.2f}  "
            f"{m.pyq_score:>6.4f}  {m.book_weight:>5.2f}  "
            f"{m.difficulty.name:<8} {m.importance.name:<10}"
        )
        total += m.original_hours
    print(f"{'-'*72}")
    print(f"{'TOTAL':<31} {total:>5.2f}")
    print(f"{'='*72}\n")


if __name__ == "__main__":
    import sys

    curriculum_path = sys.argv[1] if len(sys.argv) > 1 else "adaptive_curriculum.json"
    analysis_path   = sys.argv[2] if len(sys.argv) > 2 else "topic_analysis.json"

    modules = load_from_pyq_system(curriculum_path, analysis_path)
    _print_summary(modules)