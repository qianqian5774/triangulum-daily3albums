from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from daily3albums.cli import _beijing_now, _beijing_slot, _slot_label, _slot_window_start


CONTRACT = json.loads(
    (Path(__file__).parent / "fixtures" / "product_schedule.json").read_text(encoding="utf-8")
)


def _at(value: str) -> datetime:
    return datetime.fromisoformat(f"2026-07-11T{value}")


def test_python_product_clock_uses_canonical_timezone():
    now = _beijing_now()
    assert now.utcoffset() == timedelta(hours=8)
    assert getattr(now.tzinfo, "key", now.tzname()) == CONTRACT["timezone"]


def test_beijing_generation_slot_boundaries_follow_product_schedule():
    for case in CONTRACT["boundary_cases"]:
        assert _beijing_slot(_at(case["time"])) == case["writer_slot_id"]


def test_slot_labels_and_observability_starts_follow_product_schedule():
    slots = CONTRACT["slots"]
    assert len(slots) == CONTRACT["slots_per_day"] == 3
    assert CONTRACT["picks_per_slot"] == 3
    assert [_slot_label(slot["slot_id"]) for slot in slots] == [
        slot["writer_window_label"] for slot in slots
    ]
    assert [_slot_window_start(slot["slot_id"]) for slot in slots] == [
        slot["start"][:5] for slot in slots
    ]

    current_issue = json.loads(
        (Path(__file__).parent / "fixtures" / "public_contract" / "current-issue.json").read_text(
            encoding="utf-8"
        )
    )
    assert len(current_issue["slots"]) == CONTRACT["slots_per_day"]
    assert all(len(slot["picks"]) == CONTRACT["picks_per_slot"] for slot in current_issue["slots"])
