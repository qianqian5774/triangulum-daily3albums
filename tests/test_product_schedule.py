from __future__ import annotations

from datetime import datetime

from daily3albums.cli import _beijing_slot, _slot_label, _slot_window_start


def test_beijing_generation_slot_boundaries_follow_product_schedule():
    assert _beijing_slot(datetime(2026, 7, 11, 0, 0)) == 0
    assert _beijing_slot(datetime(2026, 7, 11, 12, 29, 59)) == 0
    assert _beijing_slot(datetime(2026, 7, 11, 12, 30)) == 1
    assert _beijing_slot(datetime(2026, 7, 11, 15, 59, 59)) == 1
    assert _beijing_slot(datetime(2026, 7, 11, 16, 0)) == 2


def test_slot_labels_and_observability_starts_follow_product_schedule():
    assert [_slot_label(slot_id) for slot_id in range(3)] == [
        "08:00-12:29",
        "12:30-15:59",
        "16:00-23:59",
    ]
    assert [_slot_window_start(slot_id) for slot_id in range(3)] == [
        "08:00",
        "12:30",
        "16:00",
    ]
