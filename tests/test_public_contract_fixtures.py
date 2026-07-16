from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any, Callable

import pytest

from daily3albums.artifact_writer import write_daily_artifacts
from daily3albums.public_contract import PublicContractError, validate_index, validate_issue
from scripts import restore_static_archive_seed as restore
from scripts import self_check


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "public_contract"
MANIFEST = json.loads((FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8"))


def _tokens(pointer: str) -> list[str]:
    if not pointer.startswith("/"):
        raise AssertionError(f"invalid fixture pointer: {pointer}")
    return [token.replace("~1", "/").replace("~0", "~") for token in pointer[1:].split("/")]


def _apply_mutations(payload: Any, mutations: list[dict[str, Any]] | None) -> Any:
    result = copy.deepcopy(payload)
    for mutation in mutations or []:
        parts = _tokens(mutation["path"])
        parent = result
        for token in parts[:-1]:
            parent = parent[int(token)] if isinstance(parent, list) else parent[token]
        final = parts[-1]
        op = mutation["op"]
        if op == "set":
            if isinstance(parent, list):
                parent[int(final)] = copy.deepcopy(mutation["value"])
            else:
                parent[final] = copy.deepcopy(mutation["value"])
        elif op == "delete":
            if isinstance(parent, list):
                parent.pop(int(final))
            else:
                del parent[final]
        elif op == "append":
            target = parent[int(final)] if isinstance(parent, list) else parent[final]
            target.append(copy.deepcopy(mutation["value"]))
        else:
            raise AssertionError(f"unsupported fixture mutation: {op}")
    return result


def _load_case(case: dict[str, Any]) -> Any:
    payload = json.loads((FIXTURE_ROOT / case["base"]).read_text(encoding="utf-8"))
    return _apply_mutations(payload, case.get("mutations"))


def _artifact_consumer(case: dict[str, Any], payload: Any) -> None:
    if case["artifact_kind"] == "index":
        validate_index(payload)
        return
    validate_issue(
        payload,
        artifact_kind=case["artifact_kind"],
        profile=case["profile"],
    )


def _seed_restore_consumer(case: dict[str, Any], payload: Any) -> None:
    if case["artifact_kind"] == "index":
        restore._validate_index(payload, case["id"], max_days=7)
        return
    if case["artifact_kind"] == "archive":
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        restore._validate_archive(
            data,
            {"date": payload.get("date"), "run_id": payload.get("run_id")},
            case["id"],
        )
        return
    raise pytest.skip.Exception("not applicable")


def _self_check_consumer(case: dict[str, Any], payload: Any) -> None:
    path = Path(case["id"] + ".json")
    if case["artifact_kind"] == "today":
        self_check._validate_today(payload, path)
    elif case["artifact_kind"] == "archive":
        self_check._validate_archive_payload(payload, path)
    else:
        self_check._validate_index(payload, path)


CONSUMERS: dict[str, Callable[[dict[str, Any], Any], None]] = {
    "python_artifact": _artifact_consumer,
    "seed_restore": _seed_restore_consumer,
    "self_check": _self_check_consumer,
}


def _applicable(case: dict[str, Any], consumer: str) -> bool:
    if consumer == "seed_restore" and case["artifact_kind"] == "today":
        return False
    return True


@pytest.mark.parametrize("case", MANIFEST["cases"], ids=lambda case: case["id"])
@pytest.mark.parametrize("consumer", list(CONSUMERS))
def test_canonical_contract_fixture_matrix(case: dict[str, Any], consumer: str):
    if not _applicable(case, consumer):
        pytest.skip("consumer not applicable to artifact kind")
    payload = _load_case(case)
    expected_valid = case["expected"] in {"valid", "valid_legacy"}
    if expected_valid:
        CONSUMERS[consumer](case, payload)
        return
    with pytest.raises(Exception) as caught:
        CONSUMERS[consumer](case, payload)
    assert case["error_code"] in str(caught.value)


def _materialize_bundle(case: dict[str, Any], root: Path) -> tuple[dict[str, Any], Path]:
    source = root / "source" / "data"
    source.mkdir(parents=True)
    index = json.loads((FIXTURE_ROOT / case["index"]).read_text(encoding="utf-8"))
    index = _apply_mutations(index, case.get("index_mutations"))
    (source / "index.json").write_text(json.dumps(index), encoding="utf-8")
    item = index["items"][0]
    run_path = source / "archive" / item["date"] / f"{item['run_id']}.json"
    alias_path = source / "archive" / f"{item['date']}.json"
    if case.get("run_file"):
        run_path.parent.mkdir(parents=True, exist_ok=True)
        run_path.write_bytes((FIXTURE_ROOT / case["run_file"]).read_bytes())
    if case.get("alias_file"):
        alias_path.parent.mkdir(parents=True, exist_ok=True)
        alias_path.write_bytes((FIXTURE_ROOT / case["alias_file"]).read_bytes())
    return index, source


@pytest.mark.parametrize("case", MANIFEST["bundle_cases"], ids=lambda case: case["id"])
@pytest.mark.parametrize("consumer", ["seed_restore", "self_check"])
def test_archive_bundle_fixture_matrix(tmp_path: Path, case: dict[str, Any], consumer: str):
    index, source = _materialize_bundle(case, tmp_path / consumer)
    expected_valid = case["expected"] == "valid"

    def invoke() -> None:
        if consumer == "seed_restore":
            restore._materialize_local_provider(
                restore.Provider("contract", "local", str(source)),
                tmp_path / consumer / "out",
                max_days=7,
            )
        else:
            self_check._validate_index(index, source / "index.json")
            self_check._validate_index_archives(index, source / "index.json", source.parent)

    if expected_valid:
        invoke()
        return
    with pytest.raises(Exception) as caught:
        invoke()
    expected_code = case["error_code"]
    if consumer == "seed_restore":
        expected_code = {
            "ARCHIVE_MISSING": "code=missing",
            "INVALID_JSON": "code=corrupt",
        }.get(expected_code, expected_code)
    assert expected_code in str(caught.value)


def test_current_writer_fixture_round_trips_without_mutation(tmp_path: Path):
    payload = _load_case(next(case for case in MANIFEST["cases"] if case["id"] == "current_today_valid"))
    before = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    validate_issue(payload, artifact_kind="today", profile="current")
    after = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert after == before

    expected_bytes = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    paths = write_daily_artifacts(payload, tmp_path / "public")
    assert paths["today"].read_bytes() == expected_bytes
    assert paths["archive"].read_bytes() == expected_bytes
    assert paths["archive_flat"].read_bytes() == expected_bytes
    assert paths["archive"].read_bytes() == paths["archive_flat"].read_bytes()
    index = json.loads(paths["index"].read_text(encoding="utf-8"))
    assert "path" not in index["items"][0]


def test_contract_error_exposes_stable_code():
    payload = _load_case(next(case for case in MANIFEST["cases"] if case["id"] == "unknown_schema_version"))
    with pytest.raises(PublicContractError) as caught:
        validate_issue(payload, artifact_kind="today", profile="current")
    assert caught.value.code == "UNKNOWN_SCHEMA_VERSION"


def test_production_style_fixture_passes_full_self_check(tmp_path: Path, monkeypatch):
    payload = _load_case(next(case for case in MANIFEST["cases"] if case["id"] == "current_today_valid"))
    public = tmp_path / "public"
    public.mkdir()
    (public / "index.html").write_text("<!doctype html><title>fixture</title>", encoding="utf-8")
    (public / "archive.html").write_text("<!doctype html><title>archive fixture</title>", encoding="utf-8")
    write_daily_artifacts(payload, public)
    monkeypatch.setattr(self_check, "_current_bjt_date_key", lambda: payload["date"])
    monkeypatch.setattr(sys, "argv", ["self_check.py", "--path", str(public)])
    assert self_check.main() == 0
