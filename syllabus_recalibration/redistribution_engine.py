"""
redistribution_engine.py
------------------------
Core redistribution math — zero LLM dependency.

Formula
-------
  Weight(m) = α·PYQ(m) + β·Book(m)      α=0.6, β=0.4

  NewHours(m) = AvailableHours × Weight(m) / ΣWeight(m')

Constraints
-----------
  Σ NewHours(m)  = 45h                           (conservation)
  NewHours(m)    ≥ max(1.0, topic_count × 0.5)   (floor)
  All hours      snapped to nearest 0.25h         (quantization)
  Residual       absorbed by highest-weight module

Velocity signal
---------------
  velocity = actual / original
  velocity > 1.15  → reclassify HARD  (took longer → harder)
  velocity < 0.75  → reclassify EASY  (finished faster → easier)
  else             → MEDIUM
"""

from __future__ import annotations

from dataclasses import replace
from typing import Dict, List, Tuple

from models import (
    DifficultyLevel,
    Module,
    RedistributionResult,
    UserAdjustment,
)

ALPHA = 0.6   # PYQ weight
BETA  = 0.4   # Book weight
TOTAL_COURSE_HOURS = 45.0
PRIORITY_BOOST = 1.3   # multiplier applied when user marks a module as priority
MAX_GROWTH_FACTOR = 1.5  # a module can grow at most 50% above its original hours


# ---------------------------------------------------------------------------
# Quantization helpers
# ---------------------------------------------------------------------------

def _snap(hours: float) -> float:
    """Snap to nearest 0.25h."""
    return round(hours * 4) / 4


def _quantize_hours(
    raw: Dict[int, float],
    modules_by_id: Dict[int, Module],
    locked_ids: set = None,
    total: float = TOTAL_COURSE_HOURS,
) -> Dict[int, float]:
    """
    1. Snap every module to nearest 0.25h.
    2. Fix conservation residual on the highest-weight module.
    """
    snapped = {mid: _snap(h) for mid, h in raw.items()}

    residual = _snap(total - sum(snapped.values()))

    if residual != 0.0:
        def _w(mid):
            m = modules_by_id[mid]
            return ALPHA * m.pyq_score + BETA * m.book_weight

        # Never put residual on a locked module — user stated exact hours
        candidates = {
            mid: h for mid, h in snapped.items()
            if locked_ids is None or mid not in locked_ids
        }
        target = max(candidates, key=_w)
        snapped[target] = _snap(snapped[target] + residual)

    return snapped


# ---------------------------------------------------------------------------
# Velocity → difficulty reclassification
# ---------------------------------------------------------------------------

def _reclassify_difficulty(velocity: float) -> DifficultyLevel:
    if velocity > 1.15:
        return DifficultyLevel.HARD    # took longer than expected → harder
    elif velocity < 0.75:
        return DifficultyLevel.EASY    # finished faster than expected → easier
    else:
        return DifficultyLevel.MEDIUM


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------

class RedistributionEngine:

    def redistribute(
        self,
        modules: List[Module],
        adjustments: List[UserAdjustment],
        priority_module_ids: List[int] = None,
    ) -> RedistributionResult:
        """
        Redistribute hours across modules given user adjustments.

        Parameters
        ----------
        modules          : 7 Module objects from bridge_loader
        adjustments      : parsed user overrides (which modules are done + actual hours)
        priority_module_ids : module ids the user wants to give extra time to
        """
        priority_ids = set(priority_module_ids or [])
        adj_by_id: Dict[int, UserAdjustment] = {a.module_id: a for a in adjustments}
        modules_by_id: Dict[int, Module] = {m.module_id: m for m in modules}

        log: List[str] = []
        warnings: List[str] = []

        # ------------------------------------------------------------------
        # 1. Compute total saved hours and mark adjusted modules
        # ------------------------------------------------------------------
        adjusted_ids = set(adj_by_id.keys())
        total_saved = sum(a.saved_hours for a in adjustments)

        log.append(
            f"Adjusted modules: {sorted(adjusted_ids)} | "
            f"Total saved: {total_saved:+.2f}h"
        )

        # ------------------------------------------------------------------
        # 2. Floor check — adjusted modules must satisfy min_hours
        # ------------------------------------------------------------------
        for adj in adjustments:
            m = modules_by_id[adj.module_id]
            if adj.actual_hours < m.min_hours:
                warnings.append(
                    f"Module {m.module_name}: actual hours {adj.actual_hours:.2f}h "
                    f"is below minimum {m.min_hours:.2f}h — clamped to minimum."
                )

        # ------------------------------------------------------------------
        # 3. Non-adjusted modules receive the redistributed hours
        # ------------------------------------------------------------------
        free_modules: List[Module] = [
            m for m in modules if m.module_id not in adjusted_ids
        ]

        # Compute weighted scores for free modules (with optional priority boost)
        def _composite_weight(m: Module) -> float:
            w = ALPHA * m.pyq_score + BETA * m.book_weight
            if m.module_id in priority_ids:
                w *= PRIORITY_BOOST
            return w

        free_weights = {m.module_id: _composite_weight(m) for m in free_modules}
        total_weight = sum(free_weights.values())

        # Available hours to distribute among free modules
        # = their original allocated hours + any saved hours from adjusted modules
        free_original = sum(m.original_hours for m in free_modules)
        available = free_original + total_saved

        log.append(
            f"Available hours for redistribution: {available:.2f}h "
            f"across {len(free_modules)} modules"
        )

        # ------------------------------------------------------------------
        # 4. Compute raw new hours for free modules
        # ------------------------------------------------------------------
        raw_new: Dict[int, float] = {}

        if total_weight == 0 or len(free_modules) == 0:
            # Edge case: everything was adjusted
            warnings.append("All modules were adjusted — no redistribution needed.")
            raw_new = {m.module_id: m.original_hours for m in free_modules}
        else:
            for m in free_modules:
                raw_hours = available * (free_weights[m.module_id] / total_weight)
                # Apply floor constraint
                raw_hours = max(raw_hours, m.min_hours)
                # Apply growth cap: no module grows more than MAX_GROWTH_FACTOR × original
                cap = m.original_hours * MAX_GROWTH_FACTOR
                if raw_hours > cap:
                    log.append(
                        f"{m.module_name}: capped at {cap:.2f}h "
                        f"(was {raw_hours:.2f}h, cap={MAX_GROWTH_FACTOR}× baseline)"
                    )
                    raw_hours = cap
                raw_new[m.module_id] = raw_hours

            # If cap freed up hours, redistribute the excess to uncapped high-weight modules
            raw_total = sum(raw_new.values())
            excess = available - raw_total
            if excess > 0.01:
                # Modules not yet at their cap, sorted by weight descending
                uncapped = [
                    m for m in free_modules
                    if raw_new[m.module_id] < m.original_hours * MAX_GROWTH_FACTOR - 0.01
                ]
                if uncapped:
                    uw_total = sum(free_weights[m.module_id] for m in uncapped)
                    for m in uncapped:
                        bonus = excess * (free_weights[m.module_id] / uw_total)
                        new_val = raw_new[m.module_id] + bonus
                        cap = m.original_hours * MAX_GROWTH_FACTOR
                        raw_new[m.module_id] = min(new_val, cap)
                    log.append(f"Growth-cap excess {excess:.2f}h redistributed to {len(uncapped)} uncapped modules.")

            # Final re-normalise for any residual from floor or cap interactions
            raw_total = sum(raw_new.values())
            if abs(raw_total - available) > 0.1:
                scale = available / raw_total
                raw_new = {mid: h * scale for mid, h in raw_new.items()}
                log.append(
                    f"Floor/cap correction: rescaled by {scale:.4f}"
                )

        # ------------------------------------------------------------------
        # 5. Adjusted modules: lock to actual_hours (floor-clamped)
        # ------------------------------------------------------------------
        raw_adjusted: Dict[int, float] = {}
        for adj in adjustments:
            m = modules_by_id[adj.module_id]
            raw_adjusted[adj.module_id] = max(adj.actual_hours, m.min_hours)

        # ------------------------------------------------------------------
        # 6. Merge and quantize
        # ------------------------------------------------------------------
        all_raw = {**raw_adjusted, **raw_new}
        snapped = _quantize_hours(all_raw, modules_by_id, locked_ids=adjusted_ids, total=TOTAL_COURSE_HOURS)

        # Verify conservation
        final_total = sum(snapped.values())
        if abs(final_total - TOTAL_COURSE_HOURS) > 0.01:
            warnings.append(
                f"Conservation check failed: total = {final_total:.2f}h (expected 45.0h)"
            )

        # ------------------------------------------------------------------
        # 7. Build recalibrated Module objects
        # ------------------------------------------------------------------
        recalibrated: List[Module] = []
        for m in modules:
            new_hours = snapped[m.module_id]

            # Velocity signal
            if m.module_id in adj_by_id:
                vel = adj_by_id[m.module_id].velocity
                new_diff = _reclassify_difficulty(vel)
                log.append(
                    f"{m.module_name}: velocity={vel:.2f} → "
                    f"difficulty reclassified to {new_diff.name}"
                )
            else:
                vel = m.velocity_signal
                new_diff = m.difficulty

            recalibrated.append(
                replace(
                    m,
                    allocated_hours=new_hours,
                    velocity_signal=vel,
                    difficulty=new_diff,
                )
            )

        recalibrated.sort(key=lambda m: m.module_id)

        return RedistributionResult(
            original_modules=modules,
            recalibrated_modules=recalibrated,
            total_hours=TOTAL_COURSE_HOURS,
            total_saved=total_saved,
            adjustment_log=log,
            warnings=warnings,
        )