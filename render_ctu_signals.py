#!/usr/bin/env python3
"""Render user-acquired CTU-UHB signals without reading outcome metadata."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from ctg_llm.rendering import (
    RenderSettings,
    discover_signal_files,
    load_csv_trace,
    load_wfdb_trace,
    render_trace,
    safe_output_stem,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        description=(
            "Create static CTG images from public CTU-UHB WFDB records or the "
            "documented signal-only CSV schema."
        )
    )
    command.add_argument("--input-directory", required=True, type=Path)
    command.add_argument("--output-directory", required=True, type=Path)
    command.add_argument("--manifest", type=Path)
    command.add_argument(
        "--source-format",
        choices=["auto", "wfdb", "csv"],
        default="auto",
    )
    command.add_argument(
        "--record-list",
        type=Path,
        help="Optional text file containing one de-identified record ID per line.",
    )
    command.add_argument("--window-minutes", type=float, default=60.0)
    command.add_argument("--fallback-sample-period-ms", type=float, default=250.0)
    command.add_argument("--min-segment-samples", type=int, default=40)
    command.add_argument("--dpi", type=int, default=100)
    command.add_argument("--overwrite", action="store_true")
    return command


def selected_record_ids(path: Path | None) -> set[str] | None:
    if path is None:
        return None
    values = {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    if not values:
        raise ValueError("The record list contains no identifiers.")
    return values


def atomic_json_write(path: Path, payload: dict, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Manifest already exists: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> None:
    args = parser().parse_args()
    input_directory = args.input_directory.resolve()
    if not input_directory.is_dir():
        raise NotADirectoryError("The input directory does not exist.")
    output_directory = args.output_directory.resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    manifest_path = (
        args.manifest.resolve()
        if args.manifest is not None
        else output_directory / "ctu_render_manifest.json"
    )
    if manifest_path.exists() and not args.overwrite:
        raise FileExistsError(f"Manifest already exists: {manifest_path.name}")

    settings = RenderSettings(
        window_minutes=args.window_minutes,
        fallback_sample_period_ms=args.fallback_sample_period_ms,
        min_segment_samples=args.min_segment_samples,
        dpi=args.dpi,
    ).validate()
    source_paths = discover_signal_files(input_directory, args.source_format)
    requested = selected_record_ids(args.record_list)
    available_ids = [path.stem for path in source_paths]
    if len(set(available_ids)) != len(available_ids):
        raise ValueError("Discovered record identifiers are not unique.")
    if requested is not None:
        missing = sorted(requested - set(available_ids))
        if missing:
            raise ValueError(f"Requested record IDs were not found: {missing}")
        source_paths = [path for path in source_paths if path.stem in requested]

    output_stems = [safe_output_stem(path.stem) for path in source_paths]
    if len(set(output_stems)) != len(output_stems):
        raise ValueError("Record identifiers collide after filename normalisation.")
    existing_outputs = [
        f"{stem}.png"
        for stem in output_stems
        if (output_directory / f"{stem}.png").exists()
    ]
    if existing_outputs and not args.overwrite:
        raise FileExistsError(
            f"Rendered images already exist: {existing_outputs[:5]}"
        )

    records = []
    for source_path, output_stem in zip(source_paths, output_stems):
        if source_path.suffix.lower() == ".hea":
            trace = load_wfdb_trace(source_path, input_directory)
        else:
            trace = load_csv_trace(
                source_path,
                fallback_sample_period_ms=settings.fallback_sample_period_ms,
            )
        output_path = output_directory / f"{output_stem}.png"
        counts = render_trace(trace, output_path, settings)
        source_entries = []
        for path in trace.source_files:
            relative = path.resolve().relative_to(input_directory).as_posix()
            source_entries.append(
                {"relative_path": relative, "sha256": sha256_file(path)}
            )
        records.append(
            {
                "record_id": trace.record_id,
                "source_format": trace.source_format,
                "source_files": source_entries,
                "output_file": output_path.relative_to(output_directory).as_posix(),
                "output_sha256": sha256_file(output_path),
                **counts,
            }
        )

    manifest = {
        "manifest_version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": "CTU-UHB raw signals (user-acquired from the official host)",
        "outcome_fields_loaded": False,
        "absolute_paths_recorded": False,
        "parameters": settings.to_dict(),
        "record_count": len(records),
        "records": records,
    }
    atomic_json_write(manifest_path, manifest, args.overwrite)
    print(f"Rendered {len(records)} CTU-UHB record(s).")
    print(f"Manifest: {manifest_path.name}")


if __name__ == "__main__":
    main()
