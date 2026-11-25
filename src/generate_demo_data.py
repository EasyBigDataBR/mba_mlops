#!/usr/bin/env python3
"""Create the ten immutable, explicitly synthetic campaign CSV deliveries.

Only the Python standard library is required.  The first generation anchors the
scenario to yesterday in America/Sao_Paulo (or --as-of).  Subsequent executions
reuse the manifest anchor, so opening the course on another day never silently
rewrites the historical data.  Use a NEW output directory for a new scenario.

CSV contract: date,treated,control_a,control_b.  The key is date; corrections
REPLACE that day's values.  They must never be summed with earlier deliveries.
The intentionally missing control appears only in delivery 07.  Delivery 08
explicitly supersedes it.  Delivery 10 corrects one previously delivered day.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


SCHEMA_VERSION = "1.0.0"
GENERATOR_VERSION = "1.0.0"
TIMEZONE = "America/Sao_Paulo"
DEFAULT_SEED = 20261125
PRE_DAYS = 84
POST_DAYS = 35
COLUMNS = ("date", "treated", "control_a", "control_b")
MANIFEST_NAME = "manifest.json"

FILE_NAMES = (
    "01_base_pre_01.csv",
    "02_base_pre_02.csv",
    "03_base_pre_03.csv",
    "04_base_pre_04.csv",
    "05_base_pos_01.csv",
    "06_append_pos_02.csv",
    "07_append_pos_03_invalido.csv",
    "08_correction_pos_03.csv",
    "09_append_pos_04_efeito_atenuado.csv",
    "10_correction_dia_anterior.csv",
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def last_complete_date() -> date:
    return datetime.now(ZoneInfo(TIMEZONE)).date() - timedelta(days=1)


def iso_day(value: str) -> date:
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError(f"Expected an ISO date YYYY-MM-DD, received {value!r}")
    return parsed


def stable_integer(seed: int, day: date, channel: str, low: int, high: int) -> int:
    """A per-date, per-channel draw: independent of generation length/order.

    Hash arithmetic avoids process-randomized hash(), a mutable RNG cursor and
    dependency-specific distribution implementations.  Controls never inspect
    the treatment assignment or intervention date.
    """
    payload = f"campaign-demo-v1|{seed}|{day.isoformat()}|{channel}".encode("ascii")
    value = int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")
    return low + value % (high - low + 1)


def daily_truth(seed: int, day: date, intervention_date: date) -> dict[str, Any]:
    """Construct synthetic integer conversions and a known additive effect.

    Controls share calendar/demand variation and remain unaffected by treatment.
    The untreated outcome is a stable linear combination of those controls plus
    small, bounded measurement noise.  No truth columns enter the CSV features.
    """
    weekday = (-9, -5, -1, 3, 9, 4, -1)[day.weekday()]
    calendar_trend = ((day - date(2020, 1, 1)).days // 7) % 13 - 6
    shared_demand = sum(
        stable_integer(seed, day - timedelta(days=lag), "demand", -10, 10)
        for lag in range(7)
    ) // 3
    control_a = (
        190 + 3 * weekday + calendar_trend + shared_demand
        + stable_integer(seed, day, "control_a_noise", -8, 8)
    )
    control_b = (
        135 + 2 * weekday - calendar_trend + shared_demand
        + stable_integer(seed, day, "control_b_noise", -8, 8)
    )
    # Integer half-up rounding of 25 + 0.55 * a + 0.35 * b.
    counterfactual = (500 + 11 * control_a + 7 * control_b + 10) // 20
    counterfactual += stable_integer(seed, day, "outcome_noise", -5, 5)
    post_day = (day - intervention_date).days
    effect = 0 if post_day < 0 else (35 if post_day < 28 else 8)
    return {
        "date": day.isoformat(),
        "treated": counterfactual + effect,
        "control_a": control_a,
        "control_b": control_b,
        "counterfactual": counterfactual,
        "true_effect": effect,
    }


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    """Canonical projection: fixed header, ISO date sort, integers, LF, UTF-8."""
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in sorted(rows, key=lambda item: item["date"]):
        writer.writerow({column: row[column] for column in COLUMNS})
    return stream.getvalue().encode("utf-8")


def row_validation_errors(rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for row in rows:
        day = row["date"]
        iso_day(day)
        if day in seen:
            errors.append(f"{day}:duplicate_date")
        seen.add(day)
        for column in COLUMNS[1:]:
            value = row[column]
            if value is None:
                errors.append(f"{day}:{column}:missing")
            elif type(value) is not int or value < 0:
                errors.append(f"{day}:{column}:expected_nonnegative_integer")
    return errors


def build_dataset(as_of: date, seed: int = DEFAULT_SEED) -> tuple[dict[str, bytes], dict[str, Any]]:
    """Return all CSV bytes and manifest; do not touch the filesystem."""
    pre_start = as_of - timedelta(days=PRE_DAYS + POST_DAYS - 1)
    intervention = as_of - timedelta(days=POST_DAYS - 1)
    pre_end = intervention - timedelta(days=1)
    days = [pre_start + timedelta(days=offset) for offset in range(PRE_DAYS + POST_DAYS)]
    truth = [daily_truth(seed, day, intervention) for day in days]
    canonical_rows = [{column: row[column] for column in COLUMNS} for row in truth]

    # A late measurement correction, deliberately confined to the POST period.
    # The original delivery stays immutable; delivery 10 supplies the corrected
    # daily observation.  It changes no pre-treatment data or intervention date.
    correction_day = intervention + timedelta(days=5)
    correction_index = PRE_DAYS + 5
    corrected_row = dict(canonical_rows[correction_index])
    initial_rows = [dict(row) for row in canonical_rows]
    initial_rows[correction_index]["treated"] -= 12
    original_row = dict(initial_rows[correction_index])

    deliveries = [
        initial_rows[0:21],
        initial_rows[21:42],
        initial_rows[42:63],
        initial_rows[63:84],
        initial_rows[84:98],
        initial_rows[98:105],
        [dict(row) for row in initial_rows[105:112]],
        [dict(row) for row in initial_rows[105:112]],
        initial_rows[112:119],
        [corrected_row],
    ]
    deliveries[6][3]["control_a"] = None
    invalid_day = deliveries[6][3]["date"]
    output: dict[str, bytes] = {}
    files: list[dict[str, Any]] = []
    purposes = (
        "Primeira parte do pré; entregar com os arquivos 02 a 05.",
        "Segunda parte do pré; entregar com os arquivos 01 e 03 a 05.",
        "Terceira parte do pré; entregar com os arquivos 01, 02, 04 e 05.",
        "Última parte do pré; entregar com os arquivos 01 a 03 e 05.",
        "Primeiros 14 dias do pós; completa a carga inicial de 98 dias.",
        "Acrescenta sete dias completos, mantendo o desenho fixo.",
        "Falha deliberada: um controle ausente; rejeitar o arquivo inteiro.",
        "Corrige o mesmo período de 07 e o substitui explicitamente.",
        "Acrescenta os últimos sete dias; o efeito sintético cai de +35 para +8 por dia.",
        "Corrige a contagem de um dia antigo do pós; substituir a chave date, sem somar.",
    )
    for index, (filename, rows) in enumerate(zip(FILE_NAMES, deliveries), start=1):
        errors = row_validation_errors(rows)
        if index == 7:
            assert errors == [f"{invalid_day}:control_a:missing"], errors
        elif errors:
            raise AssertionError(f"Unexpected invalid delivery {index}: {errors}")
        payload = csv_bytes(rows)
        output[filename] = payload
        kind = "base" if index <= 5 else ("correction" if index in (8, 10) else "append")
        files.append({
            "filename": filename,
            "batch_number": index,
            "sha256": sha256_bytes(payload),
            "byte_count": len(payload),
            "row_count": len(rows),
            "period_start": rows[0]["date"],
            "period_end": rows[-1]["date"],
            "revision": 2 if index in (8, 10) else 1,
            "kind": kind,
            "supersedes_files": [FILE_NAMES[6]] if index == 8 else [],
            "revises_files": [FILE_NAMES[4]] if index == 10 else [],
            "correction_dates": (
                [row["date"] for row in rows] if index in (8, 10) else []
            ),
            "expected_validation": "REJECTED" if index == 7 else "VALID",
            "expected_validation_errors": errors,
            "purpose": purposes[index - 1],
        })

    # Oracle states describe acceptance/replacement, NOT a second ingestion
    # implementation.  They provide an independent content/hash fixture for
    # the notebooks and expose accidental daily summation or partial acceptance.
    run_deliveries = ((1, 2, 3, 4, 5), (6,), (7,), (8,), (9,), (10,))
    state: dict[str, dict[str, Any]] = {}
    run_plan: list[dict[str, Any]] = []
    for run_number, delivery_numbers in enumerate(run_deliveries, start=1):
        rejected = 7 in delivery_numbers
        if not rejected:
            for number in delivery_numbers:
                for row in deliveries[number - 1]:
                    state[row["date"]] = dict(row)
        state_rows = [state[key] for key in sorted(state)]
        if state_rows:
            expected_days = (iso_day(state_rows[-1]["date"]) - pre_start).days + 1
            assert len(state_rows) == expected_days, "Accepted calendar must stay complete"
        run_plan.append({
            "run_number": run_number,
            "deliver_files": [FILE_NAMES[number - 1] for number in delivery_numbers],
            "expected_cycle_status": "REJECTED" if rejected else "READY_FOR_ANALYSIS",
            "publish_new_analysis": not rejected,
            "accepted_row_count": len(state_rows),
            "accepted_pre_days": PRE_DAYS,
            "accepted_post_days": len(state_rows) - PRE_DAYS,
            "accepted_as_of": state_rows[-1]["date"],
            "snapshot_sha256": sha256_bytes(csv_bytes(state_rows)),
            "treated_total": sum(row["treated"] for row in state_rows),
            "supersedes_rejection": FILE_NAMES[6] if 8 in delivery_numbers else None,
        })
    assert len(output) == 10 and len(state) == 119
    assert run_plan[1]["snapshot_sha256"] == run_plan[2]["snapshot_sha256"]
    assert run_plan[4]["snapshot_sha256"] != run_plan[5]["snapshot_sha256"]
    assert run_plan[5]["treated_total"] - run_plan[4]["treated_total"] == 12
    assert csv_bytes(list(state.values())) == csv_bytes(canonical_rows)

    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "dataset_id": f"synthetic_campaign_v1_{as_of.isoformat()}_seed_{seed}",
        "synthetic": True,
        "description": "DADOS SINTÉTICOS para ensino. Não representam campanhas, clientes ou resultados reais.",
        "timezone": TIMEZONE,
        "seed": seed,
        "as_of": as_of.isoformat(),
        "pre_start": pre_start.isoformat(),
        "pre_end": pre_end.isoformat(),
        "intervention_date": intervention.isoformat(),
        "post_start": intervention.isoformat(),
        "post_end": as_of.isoformat(),
        "pre_days": PRE_DAYS,
        "post_days_final": POST_DAYS,
        "initial_post_days": 14,
        "outcome_column": "treated",
        "control_columns": ["control_a", "control_b"],
        "row_key": ["date"],
        "csv_contract": {
            "encoding": "utf-8",
            "delimiter": ",",
            "line_ending": "LF",
            "columns": list(COLUMNS),
            "date_format": "YYYY-MM-DD",
            "numeric_type": "nonnegative_integer",
            "unit": "conversões diárias sintéticas",
            "missing_value": "empty field; permitted only as the intentional error in delivery 07",
        },
        "anchor_policy": {
            "first_generation_default": "last complete date in America/Sao_Paulo",
            "existing_manifest": "reuse fixed as_of and seed; never advance the scenario silently",
            "new_scenario": "use an empty output directory and an explicit new as_of",
        },
        "ingestion_contract": {
            "initial_delivery": list(FILE_NAMES[:5]),
            "subsequent_delivery": "one new file per run, in batch_number order",
            "file_identity": ["filename", "sha256"],
            "replay": "same filename and hash must be a no-op",
            "changed_existing_file": "reject unexpected bytes/hash; publish an explicit correction as a new file",
            "validation": "validate the complete new delivery before publishing any rows or analysis",
            "invalid_delivery": "preserve historical rejection/quarantine; publish no partial data or new analysis",
            "correction_08": "08 explicitly supersedes rejection 07; historical rejection must not block later valid cycles",
            "row_write_semantics": "replace complete row on date; never add old and corrected counts",
            "late_correction_10": "do not reduce as_of to the correction file's maximum date; keep the accepted complete calendar",
        },
        "snapshot_hash_contract": {
            "algorithm": "sha256",
            "representation": "UTF-8 CSV with LF, header date,treated,control_a,control_b, rows ordered by date, integer values, final LF",
            "includes": "all accepted current rows after explicit date-key replacements",
            "excludes": "rejected rows, provenance metadata and manifest instructor truth",
        },
        "files": files,
        "run_plan": run_plan,
        "instructor_truth": {
            "do_not_ingest_as_features": True,
            "controls_unaffected_by_intervention": True,
            "initial_effect_per_day": 35,
            "attenuated_effect_per_day": 8,
            "attenuation_start": (intervention + timedelta(days=28)).isoformat(),
            "true_cumulative_effect_final": 28 * 35 + 7 * 8,
            "late_measurement_correction": {
                "date": correction_day.isoformat(),
                "column": "treated",
                "original_value": original_row["treated"],
                "corrected_value": corrected_row["treated"],
                "delta": 12,
                "changes_pre_period": False,
                "reason": "Uma contagem diária inicialmente subnotificada é corrigida em nova entrega.",
            },
            "daily": [
                {"date": row["date"], "counterfactual": row["counterfactual"],
                 "true_effect": row["true_effect"], "treated_final": row["treated"]}
                for row in truth
            ],
        },
    }
    return output, manifest


def manifest_bytes(manifest: dict[str, Any]) -> bytes:
    return (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def resolve_anchor(output_dir: Path, requested_as_of: date | None, requested_seed: int | None) -> tuple[date, int]:
    manifest_path = output_dir / MANIFEST_NAME
    if not manifest_path.exists():
        return requested_as_of or last_complete_date(), DEFAULT_SEED if requested_seed is None else requested_seed
    existing = json.loads(manifest_path.read_text(encoding="utf-8"))
    if existing.get("generator_version") != GENERATOR_VERSION or existing.get("synthetic") is not True:
        raise ValueError("Existing manifest is not this synthetic generator version; use a new output directory")
    anchored_as_of = iso_day(existing["as_of"])
    anchored_seed = int(existing["seed"])
    if requested_as_of is not None and requested_as_of != anchored_as_of:
        raise ValueError("Changing as_of would rewrite historical dates. Use a new, empty output directory")
    if requested_seed is not None and requested_seed != anchored_seed:
        raise ValueError("Changing seed would rewrite historical values. Use a new, empty output directory")
    return anchored_as_of, anchored_seed


def generate_demo_data(output_dir: Path, as_of: date | None = None, seed: int | None = None, check_only: bool = False) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    anchored_as_of, anchored_seed = resolve_anchor(output_dir, as_of, seed)
    payloads, manifest = build_dataset(anchored_as_of, anchored_seed)
    payloads[MANIFEST_NAME] = manifest_bytes(manifest)
    existing_csv = {path.name for path in output_dir.glob("*.csv")}
    unknown = existing_csv - set(FILE_NAMES)
    if unknown:
        raise ValueError(f"Unexpected CSV files in demo directory: {sorted(unknown)}")
    # Check every existing artifact BEFORE creating anything.  This prevents a
    # partial rewrite if an instructor or student modified a historical CSV.
    for filename, payload in payloads.items():
        path = output_dir / filename
        if path.exists() and path.read_bytes() != payload:
            raise ValueError(f"Existing artifact differs from deterministic bytes: {filename}; no files were overwritten")
        if check_only and not path.is_file():
            raise ValueError(f"Missing artifact: {filename}")
    if not check_only:
        output_dir.mkdir(parents=True, exist_ok=True)
        for filename, payload in payloads.items():
            path = output_dir / filename
            if not path.exists():
                temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
                temporary.write_bytes(payload)
                temporary.replace(path)
    if len(list(output_dir.glob("*.csv"))) != 10:
        raise AssertionError("The demo directory must contain exactly ten CSV files")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[1] / "data_demo")
    parser.add_argument("--as-of", type=iso_day, help="Final complete date; defaults to yesterday in Sao Paulo only on first generation")
    parser.add_argument("--seed", type=int, help=f"Deterministic seed; defaults to {DEFAULT_SEED} only on first generation")
    parser.add_argument("--check", action="store_true", help="Verify all existing bytes, without writing files")
    args = parser.parse_args()
    try:
        manifest = generate_demo_data(args.output_dir, args.as_of, args.seed, args.check)
    except (ValueError, OSError, AssertionError, KeyError) as error:
        parser.exit(2, f"Error: {error}\n")
    print(json.dumps({
        "status": "VERIFIED" if args.check else "READY",
        "synthetic": True,
        "manifest": str(args.output_dir.resolve() / MANIFEST_NAME),
        "csv_count": len(manifest["files"]),
        "as_of": manifest["as_of"],
        "pre_start": manifest["pre_start"],
        "pre_end": manifest["pre_end"],
        "intervention_date": manifest["intervention_date"],
        "expected_accepted_rows_by_run": [item["accepted_row_count"] for item in manifest["run_plan"]],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
