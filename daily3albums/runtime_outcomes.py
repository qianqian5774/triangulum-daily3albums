from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Generic, TypeVar


class OutcomeCode(StrEnum):
    SUCCESS = "success"
    MISSING = "missing"
    LEGITIMATE_EMPTY = "legitimate_empty"
    PROVIDER_NOT_FOUND = "provider_not_found"
    REQUEST_FAILED = "request_failed"
    TIMEOUT = "timeout"
    CORRUPT = "corrupt"
    INVALID_SCHEMA = "invalid_schema"
    IDENTITY_MISMATCH = "identity_mismatch"
    ARCHIVE_ALIAS_MISMATCH = "archive_alias_mismatch"
    FALLBACK_USED = "fallback_used"
    PUBLISHED_ARCHIVE_REUSED = "published_archive_reused"
    DISABLED = "disabled"
    NOT_CONFIGURED = "not_configured"
    RATE_LIMITED = "rate_limited"
    UNAVAILABLE = "unavailable"
    RECOVERY_EXHAUSTED = "recovery_exhausted"
    RENDER_FAILED = "render_failed"


@dataclass(frozen=True)
class RuntimeOutcome:
    code: OutcomeCode
    provider: str
    stage: str
    resource: str
    http_status: int | None = None
    cached: bool | None = None
    fallback: str | None = None

    def safe_fields(self) -> dict[str, str | int | bool]:
        fields: dict[str, str | int | bool] = {
            "code": self.code.value,
            "provider": self.provider,
            "stage": self.stage,
            "resource": self.resource,
        }
        if self.http_status is not None:
            fields["http_status"] = self.http_status
        if self.cached is not None:
            fields["cached"] = self.cached
        if self.fallback is not None:
            fields["fallback"] = self.fallback
        return fields

    def format_safe(self) -> str:
        return " ".join(f"{key}={value}" for key, value in self.safe_fields().items())


T = TypeVar("T")


@dataclass(frozen=True)
class ProviderResult(Generic[T]):
    value: T
    outcome: RuntimeOutcome


def outcome_code_for_http_status(status: int) -> OutcomeCode:
    if status in {404, 410}:
        return OutcomeCode.PROVIDER_NOT_FOUND
    if status == 429:
        return OutcomeCode.RATE_LIMITED
    return OutcomeCode.REQUEST_FAILED


def outcome_code_for_exception(exc: BaseException) -> OutcomeCode:
    raw = getattr(exc, "code", None)
    try:
        if raw is not None:
            return OutcomeCode(str(raw))
    except ValueError:
        pass
    if isinstance(exc, TimeoutError):
        return OutcomeCode.TIMEOUT
    return OutcomeCode.REQUEST_FAILED


def outcome_code_for_contract_error(code: str) -> OutcomeCode:
    if code == "ARCHIVE_IDENTITY_MISMATCH":
        return OutcomeCode.IDENTITY_MISMATCH
    if code == "ARCHIVE_ALIAS_BYTES_MISMATCH":
        return OutcomeCode.ARCHIVE_ALIAS_MISMATCH
    return OutcomeCode.INVALID_SCHEMA
