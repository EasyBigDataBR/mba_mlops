"""Plan an auditable daily snapshot from the ten synthetic CSV deliveries.

This module is pure: no filesystem writes, Spark, MLflow or cloud calls.  The
caller supplies the cumulative set of files and the approved manifest.  Only a
READY plan is publishable.  BLOCKED/INCOMPLETE plans retain a diagnostic candidate
DataFrame, which MUST NOT replace silver data or trigger a causal analysis.

Corrections replace whole rows by date.  Explicit supersession preserves the
original validation errors in the historical event.  A known rejected delivery
can be superseded; an unrecognized hash cannot be silently excused.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
from datetime import date, timedelta
from typing import Any

import pandas as pd


INPUT_COLUMNS = ["date", "treated", "control_a", "control_b"]
SOURCE_COLUMNS = ["source_file", "source_sha256", "source_revision"]
OUTPUT_COLUMNS = INPUT_COLUMNS + SOURCE_COLUMNS
INT64_MAX = 2**63 - 1
_INTEGER = re.compile(r"(?:0|[1-9][0-9]*)\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _day(value: Any) -> date:
    if not isinstance(value, str):
        raise ValueError("date must be an ISO string")
    result = date.fromisoformat(value)
    if result.isoformat() != value:
        raise ValueError("date must use YYYY-MM-DD")
    return result


def _days(start: date, end: date) -> list[str]:
    return [(start + timedelta(days=index)).isoformat() for index in range((end - start).days + 1)]


def _positive_integer(value: Any) -> bool:
    return type(value) is int and 1 <= value <= INT64_MAX


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_snapshot_bytes(data: pd.DataFrame) -> bytes:
    """Hash representation from manifest.snapshot_hash_contract.

    Provenance columns do not affect data identity.  This is a serialization
    helper for an already validated snapshot, not an input-validation shortcut.
    """
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(INPUT_COLUMNS)
    for row in data[INPUT_COLUMNS].sort_values("date").itertuples(index=False, name=None):
        writer.writerow([str(row[0]), *(int(value) for value in row[1:])])
    return stream.getvalue().encode("utf-8")


def _frame(rows: dict[str, dict[str, Any]]) -> pd.DataFrame:
    result = pd.DataFrame([rows[key] for key in sorted(rows)], columns=OUTPUT_COLUMNS)
    for column in ["treated", "control_a", "control_b", "source_revision"]:
        result[column] = result[column].astype("int64")
    return result


def _manifest_specs(manifest: Any) -> tuple[list[dict[str, Any]], list[str]]:
    """Validate the trusted manifest's schema and cross-file declarations."""
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return [], ["MANIFEST_NOT_OBJECT"]
    try:
        start = _day(manifest["pre_start"])
        pre_end = _day(manifest["pre_end"])
        intervention = _day(manifest["intervention_date"])
        end = _day(manifest["as_of"])
        if (intervention - start).days != 84 or pre_end != intervention - timedelta(days=1):
            errors.append("MANIFEST_PRE_PERIOD_MUST_BE_84_DAYS")
        if end < intervention + timedelta(days=13):
            errors.append("MANIFEST_POST_PERIOD_SHORTER_THAN_14_DAYS")
        if (end - start).days > 730:
            errors.append("MANIFEST_PERIOD_EXCEEDS_730_DAYS")
        if manifest.get("initial_post_days", 14) != 14:
            errors.append("MANIFEST_INITIAL_POST_DAYS_MUST_BE_14")
        if manifest.get("csv_contract", {}).get("columns") != INPUT_COLUMNS:
            errors.append("MANIFEST_COLUMNS_MISMATCH")
        if manifest.get("row_key") != ["date"]:
            errors.append("MANIFEST_ROW_KEY_MUST_BE_DATE")
    except (ValueError, TypeError, KeyError, AttributeError):
        return [], ["MANIFEST_DATE_OR_SCHEMA_INVALID"]
    entries = manifest.get("files")
    if not isinstance(entries, list) or len(entries) != 10:
        return [], errors + ["MANIFEST_MUST_DECLARE_EXACTLY_TEN_FILES"]
    specs: list[dict[str, Any]] = []
    for position, entry in enumerate(entries, start=1):
        prefix = f"MANIFEST_ENTRY_{position}"
        if not isinstance(entry, dict):
            errors.append(f"{prefix}:NOT_OBJECT")
            continue
        try:
            name = entry["filename"]
            if not isinstance(name, str) or not name.endswith(".csv") or "/" in name or "\\" in name:
                raise ValueError("unsafe filename")
            if not _positive_integer(entry["batch_number"]):
                raise ValueError("invalid batch number")
            if not _positive_integer(entry["revision"]):
                raise ValueError("invalid revision")
            if not _positive_integer(entry["row_count"]):
                raise ValueError("invalid row count")
            if not isinstance(entry["sha256"], str) or not _SHA256.fullmatch(entry["sha256"]):
                raise ValueError("invalid SHA256")
            first, last = _day(entry["period_start"]), _day(entry["period_end"])
            if not start <= first <= last <= end:
                raise ValueError("date range outside design")
            if entry["row_count"] != (last - first).days + 1:
                raise ValueError("row count inconsistent with daily range")
            if entry["kind"] not in {"base", "append", "correction"}:
                raise ValueError("invalid kind")
            correction_dates = entry.get("correction_dates", [])
            supersedes = entry.get("supersedes_files", [])
            revises = entry.get("revises_files", [])
            if any(not isinstance(values, list) or len(values) != len(set(values)) for values in (correction_dates, supersedes, revises)):
                raise ValueError("invalid declaration list")
            if any(not isinstance(value, str) for value in correction_dates + supersedes + revises):
                raise ValueError("declaration values must be strings")
            expected_dates = _days(first, last)
            if entry["kind"] == "correction":
                if sorted(correction_dates) != expected_dates:
                    raise ValueError("correction dates must exactly cover the declared delivery")
            elif correction_dates or supersedes or revises:
                raise ValueError("only a correction may replace or supersede data")
            specs.append(dict(entry))
        except (ValueError, TypeError, KeyError):
            errors.append(f"{prefix}:INVALID_FILE_CONTRACT")
    if len(specs) != 10:
        return [], errors
    names = [entry["filename"] for entry in specs]
    if len(set(names)) != 10 or sorted(entry["batch_number"] for entry in specs) != list(range(1, 11)):
        errors.append("MANIFEST_NAMES_OR_BATCH_NUMBERS_NOT_UNIQUE_1_TO_10")
    by_name = {entry["filename"]: entry for entry in specs}
    for entry in specs:
        for relation in ("supersedes_files", "revises_files"):
            for target_name in entry.get(relation, []):
                target = by_name.get(target_name)
                if target is None or target["batch_number"] >= entry["batch_number"]:
                    errors.append(f"MANIFEST_{entry['filename']}:INVALID_{relation.upper()}")
                elif relation == "supersedes_files" and not (
                    entry["period_start"] <= target["period_start"]
                    and entry["period_end"] >= target["period_end"]
                ):
                    errors.append(f"MANIFEST_{entry['filename']}:SUPERSESSION_DOES_NOT_COVER_TARGET")
    return sorted(specs, key=lambda entry: entry["batch_number"]), errors


def _validate_file(filename: str, payload: Any, spec: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    event: dict[str, Any] = {
        "filename": filename,
        "sha256": _sha(payload) if isinstance(payload, bytes) else None,
        "batch_number": spec["batch_number"],
        "source_revision": spec["revision"],
        "status": "REJECTED",
        "validation_status": "REJECTED",
        "row_count": 0,
        "errors": [],
        "superseded_by": None,
    }
    errors = event["errors"]
    if not isinstance(payload, bytes):
        errors.append("PAYLOAD_MUST_BE_BYTES")
        return [], event
    if event["sha256"] != spec["sha256"]:
        errors.append("SHA256_MISMATCH")
    if "byte_count" in spec and len(payload) != spec["byte_count"]:
        errors.append("BYTE_COUNT_MISMATCH")
    try:
        text = payload.decode("utf-8")
        parsed = list(csv.reader(io.StringIO(text, newline=""), strict=True))
    except (UnicodeDecodeError, csv.Error):
        errors.append("INVALID_UTF8_OR_CSV")
        return [], event
    if not parsed or parsed[0] != INPUT_COLUMNS:
        errors.append("HEADER_MUST_MATCH_DATE_TREATED_CONTROL_A_CONTROL_B")
        return [], event
    if "\r" in text:
        errors.append("LINE_ENDINGS_MUST_BE_LF")
    rows: list[dict[str, Any]] = []
    observed_dates: list[str] = []
    event["row_count"] = len(parsed) - 1
    for line_number, fields in enumerate(parsed[1:], start=2):
        prefix = f"LINE_{line_number}"
        if len(fields) != len(INPUT_COLUMNS):
            errors.append(f"{prefix}:EXPECTED_FOUR_FIELDS")
            continue
        values: dict[str, Any] = dict(zip(INPUT_COLUMNS, fields))
        valid_row = True
        try:
            _day(values["date"])
            observed_dates.append(values["date"])
        except (ValueError, TypeError):
            errors.append(f"{prefix}:INVALID_ISO_DATE")
            valid_row = False
        for column in INPUT_COLUMNS[1:]:
            raw = values[column]
            if raw == "":
                errors.append(f"{prefix}:{column}:MISSING")
                valid_row = False
            elif not _INTEGER.fullmatch(raw):
                errors.append(f"{prefix}:{column}:EXPECTED_NONNEGATIVE_INTEGER")
                valid_row = False
            elif len(raw) > 19:
                # Reject oversized input before int(); Python itself limits
                # decimal conversion length, which must not escape as a crash.
                errors.append(f"{prefix}:{column}:EXCEEDS_INT64")
                valid_row = False
            else:
                value = int(raw)
                if value > INT64_MAX:
                    errors.append(f"{prefix}:{column}:EXCEEDS_INT64")
                    valid_row = False
                values[column] = value
        if valid_row:
            rows.append(values)
    if event["row_count"] != spec["row_count"]:
        errors.append("ROW_COUNT_MISMATCH")
    expected_dates = set(_days(_day(spec["period_start"]), _day(spec["period_end"])))
    if len(observed_dates) != len(set(observed_dates)):
        errors.append("DUPLICATE_DATE_WITHIN_FILE")
    if set(observed_dates) != expected_dates:
        errors.append("DATE_RANGE_OR_DAILY_COVERAGE_MISMATCH")
    if errors:
        return [], event  # Whole-file rejection; never admit the six good rows of 07.
    event["status"] = "ACCEPTED"
    event["validation_status"] = "VALID"
    return rows, event


def _result(state: dict[str, dict[str, Any]], events: list[dict[str, Any]], errors: list[str], manifest: dict[str, Any], supplied_count: int) -> dict[str, Any]:
    data = _frame(state)
    as_of: str | None = None
    missing_dates: list[str] = []
    if state:
        start = _day(manifest["pre_start"])
        maximum = _day(max(state))
        expected = _days(start, maximum)
        missing_dates = sorted(set(expected) - set(state))
        if missing_dates:
            errors.append("SNAPSHOT_HAS_DAILY_GAPS")
        contiguous_end = start - timedelta(days=1)
        while (contiguous_end + timedelta(days=1)).isoformat() in state:
            contiguous_end += timedelta(days=1)
        if contiguous_end >= start:
            as_of = contiguous_end.isoformat()
    rejected = [event["filename"] for event in events if event["status"] == "REJECTED"]
    pre_count = sum(day < manifest.get("intervention_date", "") for day in state)
    post_count = len(state) - pre_count
    if errors or rejected:
        status = "BLOCKED"
    elif len(state) < 98 or pre_count != 84 or post_count < 14:
        status = "INCOMPLETE"
    else:
        status = "READY"
    summary = {
        "publishable": status == "READY",
        "candidate_only": status != "READY",
        "supplied_file_count": supplied_count,
        "accepted_file_count": sum(event["status"] == "ACCEPTED" for event in events),
        "rejected_file_count": len(rejected),
        "superseded_file_count": sum(event["status"] == "SUPERSEDED" for event in events),
        "candidate_row_count": len(state),
        "pre_days": pre_count,
        "post_days": post_count,
        "minimum_required_rows": 98,
        "rejected_files": rejected,
        "missing_dates": missing_dates,
        "max_candidate_date": max(state) if state else None,
        "errors": list(dict.fromkeys(errors)),
        "treated_total": sum(row["treated"] for row in state.values()),
    }
    return {
        "status": status,
        "data": data,
        "snapshot_id": _sha(canonical_snapshot_bytes(data)),
        "as_of": as_of,
        "events": events,
        "summary": summary,
    }


def plan_snapshot(files: dict[str, bytes], manifest: dict[str, Any]) -> dict[str, Any]:
    """Validate cumulative deliveries and resolve explicit daily revisions.

    This function never publishes.  Consumers must require status == 'READY'.
    Replaying identical accumulated inputs is deterministic and idempotent;
    persistence/NO_NEW_DATA decisions belong to the caller's ingestion control.
    """
    if not isinstance(files, dict):
        raise TypeError("files must be a dictionary mapping filenames to bytes")
    specs, manifest_errors = _manifest_specs(manifest)
    if manifest_errors:
        return _result({}, [], manifest_errors, manifest if isinstance(manifest, dict) else {}, len(files))
    by_name = {spec["filename"]: spec for spec in specs}
    events_by_name: dict[str, dict[str, Any]] = {}
    parsed_rows: dict[str, list[dict[str, Any]]] = {}
    for spec in specs:
        name = spec["filename"]
        if name in files:
            parsed_rows[name], events_by_name[name] = _validate_file(name, files[name], spec)
    unknown_events = []
    for name in sorted(set(files) - set(by_name), key=str):
        payload = files[name]
        unknown_events.append({
            "filename": str(name),
            "sha256": _sha(payload) if isinstance(payload, bytes) else None,
            "status": "REJECTED", "validation_status": "REJECTED", "row_count": 0,
            "errors": ["UNKNOWN_FILE_NOT_DECLARED_IN_MANIFEST"], "superseded_by": None,
        })

    state: dict[str, dict[str, Any]] = {}
    for spec in specs:
        name = spec["filename"]
        event = events_by_name.get(name)
        if event is None or event["validation_status"] != "VALID":
            continue
        rows = parsed_rows[name]
        application_errors: list[str] = []
        supersedes = spec.get("supersedes_files", [])
        revises = spec.get("revises_files", [])
        correction_dates = set(spec.get("correction_dates", []))
        for target_name in supersedes:
            target_event = events_by_name.get(target_name)
            target_spec = by_name[target_name]
            if spec["revision"] <= target_spec["revision"]:
                application_errors.append("SUPERSESSION_REQUIRES_HIGHER_REVISION")
            if target_event is not None and target_event["sha256"] != target_spec["sha256"]:
                application_errors.append("CANNOT_SUPERSEDE_UNRECOGNIZED_FILE_BYTES")
        superseded_domains = {
            day for target_name in supersedes
            for day in _days(_day(by_name[target_name]["period_start"]), _day(by_name[target_name]["period_end"]))
        }
        for row in rows:
            key = row["date"]
            existing = state.get(key)
            if spec["kind"] != "correction":
                if existing is not None:
                    application_errors.append(f"{key}:OVERLAP_WITHOUT_DECLARED_CORRECTION")
            elif key not in correction_dates:
                application_errors.append(f"{key}:UNDECLARED_CORRECTION_DATE")
            elif existing is None:
                # 08 can introduce dates from explicitly superseded rejected 07.
                # 10, a row revision of accepted 05, cannot fabricate its base.
                if key not in superseded_domains:
                    application_errors.append(f"{key}:CORRECTION_HAS_NO_ACCEPTED_BASE_ROW")
            else:
                if spec["revision"] <= existing["source_revision"]:
                    application_errors.append(f"{key}:CORRECTION_REQUIRES_HIGHER_REVISION")
                if existing["source_file"] not in set(supersedes) | set(revises):
                    application_errors.append(f"{key}:ORIGINAL_SOURCE_NOT_DECLARED_FOR_REVISION")
        if application_errors:
            event["status"] = "REJECTED"
            event["errors"].extend(dict.fromkeys(application_errors))
            continue
        # Commit the delivery to the candidate state only after ALL rows pass.
        for row in rows:
            state[row["date"]] = {
                **row,
                "source_file": name,
                "source_sha256": event["sha256"],
                "source_revision": spec["revision"],
            }
        for target_name in supersedes:
            target_event = events_by_name.get(target_name)
            if target_event is not None:
                target_event["status"] = "SUPERSEDED"
                target_event["superseded_by"] = name
                # Retain validation_status and errors: the original rejection
                # remains auditable even after its correction becomes usable.
    events = [events_by_name[spec["filename"]] for spec in specs if spec["filename"] in events_by_name]
    events.extend(unknown_events)
    return _result(state, events, [], manifest, len(files))
