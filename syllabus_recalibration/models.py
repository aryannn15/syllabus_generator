"""
models.py
---------
All data models for the Adaptive Syllabus Recalibration Engine (System 2).
"""

from __future__ import annotations
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DifficultyLevel(Enum):
    EASY   = "Easy"
    MEDIUM = "Medium"
    HARD   = "Hard"


class ImportanceLevel(Enum):
    LOW       = "Low"
    MEDIUM    = "Medium"
    HIGH      = "High"
    VERY_HIGH = "Very High"


# ---------------------------------------------------------------------------
# Core dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Module:
    module_id:      int
    module_name:    str
    original_hours: float          # System 1 PYQ-optimized hours (Option B baseline)
    topics:         List[str]
    allocated_hours: float         # Set after redistribution
    min_hours:      float          # max(1.0, topic_count × 0.5)
    difficulty:     DifficultyLevel
    importance:     ImportanceLevel
    pyq_score:      float          # normalised [0, 1] from topic_analysis.json
    book_weight:    float          # from book_weights.json [0, 1]
    velocity_signal: float         # actual / original — 1.0 until feedback arrives


@dataclass(frozen=True)
class UserAdjustment:
    module_id:      int
    module_name:    str
    actual_hours:   float
    original_hours: float
    saved_hours:    float          # original - actual  (negative = overrun)
    velocity:       float          # actual / original
    confidence:     float          # LLM parser confidence [0, 1]


@dataclass
class RedistributionResult:
    original_modules:     List[Module]
    recalibrated_modules: List[Module]
    total_hours:          float          # always 45.0
    total_saved:          float
    adjustment_log:       List[str]
    warnings:             List[str]