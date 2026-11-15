"""Command interfaces for the public analysis package."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
import hashlib
import json
import platform
import pandas as pd
from . import __version__
from .categories import GUIDELINES, OUTCOME, BENCHMARK, SEED
from .cohorts import select
from .analysis import analyse_table, select_by_guideline, transport, benchmark
from .parsing import parse_response


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def environment():
    return {"python": platform.python_version(), **{name: version(name) for name in
            ("numpy", "pandas", "scipy", "scikit-learn", "matplotlib", "openpyxl")}}


def read_table(path):
    path = Path(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, dtype={"identifier": "string"})
    if path.suffix.lower() == ".xlsx":
        return pd.read_excel(path, dtype={"identifier": "string"})
    raise ValueError("Input tables must be CSV or XLSX")


def output_directory(path):
    path = Path(path)
    if path.exists() and any(path.iterdir()):
        raise ValueError("Output directory is not empty")
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_run(directory, tables, inputs, details, make_figures=True):
    for name, table in tables.items():
        if not table.empty:
            table.to_csv(directory / (name + ".csv"), index=False)
    if make_figures and "raw_roc_points" in tables:
        from .plots import figures
        figures(tables["raw_roc_points"], tables["raw_associations"], directory,
                tables.get("clinician_benchmark"))
    manifest = {"package_version": __version__, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "environment": environment(), "seed": SEED,
                "inputs": [{"name": Path(p).name, "sha256": sha256(p)} for p in inputs],
                **details}
    (directory / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def record_analysis(args):
    au, flow = select(read_table(args.australian), args.cohort)
    if args.cohort == "component":
        offset, benchmark_offset = 100, 600
    elif args.cohort.startswith("duration"):
        offset, benchmark_offset = 1000, 1500
    else:
        offset, benchmark_offset = 0, 500
    tables = {"cohort_flow": flow.assign(Dataset="Australian dataset")}
    au_raw = analyse_table(au, "Australian dataset", seed_offset=offset, reps=args.bootstrap_reps)
    for name, value in au_raw.items():
        tables["raw_" + name] = value
    tables["Australian_selected_thresholds"] = select_by_guideline(au_raw["thresholds"])
    if args.cohort != "component":
        tiers = analyse_table(au, "Australian dataset", tier=True, seed_offset=offset + 200,
                              reps=args.bootstrap_reps)
        tables["tier3_associations"], tables["tier3_counts"] = tiers["associations"], tiers["counts"]
    if "restricted" not in args.cohort:
        tables["clinician_benchmark"], tables["clinician_discordance"] = benchmark(
            au, args.bootstrap_reps, benchmark_offset)
    inputs = [args.australian]
    if args.ctu:
        if args.cohort not in ("full", "restricted"):
            raise ValueError("CTU transport is defined for the full and restricted analyses")
        ctu, ctu_flow = select(read_table(args.ctu))
        ctu_raw = analyse_table(ctu, "CTU-UHB", seed_offset=100, reps=args.bootstrap_reps)
        for name, value in ctu_raw.items():
            tables["raw_"+name] = pd.concat([tables["raw_"+name], value], ignore_index=True)
        ctu_tier = analyse_table(ctu, "CTU-UHB", tier=True, seed_offset=300, reps=args.bootstrap_reps)
        for name in ("associations", "counts"):
            tables["tier3_"+name] = pd.concat([tables["tier3_"+name], ctu_tier[name]], ignore_index=True)
        tables["cohort_flow"] = pd.concat([tables["cohort_flow"], ctu_flow.assign(Dataset="CTU-UHB")], ignore_index=True)
        tables["transported_thresholds"] = transport(tables["Australian_selected_thresholds"], ctu)
        inputs.append(args.ctu)
    directory = output_directory(args.output)
    write_run(directory, tables, inputs, {"cohort": args.cohort, "bootstrap_reps": args.bootstrap_reps,
              "input_stage": "authorised image-eligible category tables",
              "benchmark_available": BENCHMARK in au,
              "historical_inference_reexecuted": False}, not args.no_figures)


def parse_records(args):
    rows, seen = [], set()
    with open(args.input) as stream:
        for line in stream:
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("task") == "quality":
                continue
            identifier = record["study_id"]
            if not isinstance(identifier, str) or not identifier.strip():
                raise ValueError("Non-empty study_id is required")
            key = (identifier, record["guideline"])
            if key in seen:
                raise ValueError("Duplicate study_id and guideline")
            seen.add(key)
            parsed = parse_response(record["response"], record["guideline"])
            row = {"study_id": identifier, **asdict(parsed)}
            row.pop("features")
            if "status" in record and record["status"] not in ("parsed", "missing_category"):
                row.update(raw_category=None, common_tier=None, status=record["status"])
            rows.append(row)
    output = Path(args.output)
    wide_output = Path(args.wide_output) if args.wide_output else None
    if output.exists() or (wide_output and wide_output.exists()):
        raise FileExistsError("Parser output already exists")
    if wide_output and wide_output.resolve() == output.resolve():
        raise ValueError("Long and wide parser outputs must have different paths")
    frame = pd.DataFrame(rows, columns=["study_id", "guideline", "raw_category", "common_tier", "status"])
    with output.open("x") as stream:
        frame.to_csv(stream, index=False)
    if wide_output:
        wide = frame.pivot(index="study_id", columns="guideline", values="raw_category")
        wide = wide.reindex(columns=GUIDELINES).rename(columns={k: v["column"] for k, v in GUIDELINES.items()})
        wide = wide.astype("Int64").rename_axis("identifier").reset_index()
        with wide_output.open("x") as stream:
            wide.to_csv(stream, index=False)


def prepare_secondary(args):
    from .secondary import (engineer_features, engineer_external_features,
                            make_four_way_split, CLINICAL_FEATURES, LABEL_SPECS)
    data, flow = select(read_table(args.australian), args.cohort)
    if "identifier" not in data:
        raise ValueError("Secondary preparation requires study identifiers")
    frame = engineer_features(data)
    splits = make_four_way_split(frame, OUTCOME, seed=args.seed)
    partition = pd.Series(index=frame.index, dtype="string")
    for name, indices in splits.items():
        partition.loc[indices] = name
    columns = ["identifier", OUTCOME, *CLINICAL_FEATURES,
               *[spec["encoded"] for spec in LABEL_SPECS.values()]]
    prepared = frame.loc[:, columns].copy()
    prepared["partition"] = partition
    tables = {"development_predictors": prepared,
              "partition_assignments": prepared[["identifier", "partition"]],
              "cohort_flow": flow.assign(Dataset="Australian dataset")}
    inputs = [args.australian]
    if args.ctu:
        external, external_flow = select(read_table(args.ctu))
        if "identifier" not in external or external["identifier"].isna().any():
            raise ValueError("External preparation requires non-missing study identifiers")
        tables["external_predictors"] = engineer_external_features(external).loc[:, columns]
        tables["cohort_flow"] = pd.concat([
            tables["cohort_flow"], external_flow.assign(Dataset="CTU-UHB")], ignore_index=True)
        inputs.append(args.ctu)
    directory = output_directory(args.output)
    write_run(directory, tables, inputs, {"cohort": args.cohort, "seed": args.seed,
              "split_seed": args.seed, "split_fractions": {"train": 0.60, "stack": 0.15,
              "calibration": 0.10, "test": 0.15}, "model_fitting": False}, False)


def evaluate_predictions(args):
    from .probability_metrics import evaluate_probabilities
    data = read_table(args.input)
    columns = [OUTCOME, args.probability_column]
    if args.reference_column:
        columns.append(args.reference_column)
    if any(column not in data for column in columns):
        raise ValueError("Prediction input is missing a declared column")
    values = {column: pd.to_numeric(data[column], errors="raise").to_numpy()
              for column in columns}
    result = evaluate_probabilities(values[OUTCOME], values[args.probability_column],
              stage=args.stage, seed=args.seed, reps=args.bootstrap_reps,
              reference_seed=args.reference_seed,
              reference=values[args.reference_column] if args.reference_column else None)
    directory = output_directory(args.output)
    write_run(directory, {"probability_metrics": pd.DataFrame([result])}, [args.input],
              {"stage": args.stage, "seed": args.seed, "bootstrap_seed": args.seed,
               "reference_seed": args.reference_seed if args.reference_seed is not None else args.seed,
               "bootstrap_reps": args.bootstrap_reps,
               "probability_column": args.probability_column,
               "reference_column": args.reference_column,
               "model_fitting": False}, False)


def main():
    parser = argparse.ArgumentParser(description="CTG LLM public analysis components")
    sub = parser.add_subparsers(dest="command", required=True)
    record = sub.add_parser("analyse", help="Analysis of authorised category tables")
    record.add_argument("--australian", required=True)
    record.add_argument("--ctu")
    record.add_argument("--cohort", choices=("full", "restricted", "duration_full", "duration_restricted", "component"), default="full")
    record.set_defaults(function=record_analysis)
    record.add_argument("--output", required=True)
    record.add_argument("--bootstrap-reps", type=int, default=10000)
    record.add_argument("--no-figures", action="store_true")
    parse = sub.add_parser("parse", help="Parsing of the public reference response contract")
    parse.add_argument("--input", required=True)
    parse.add_argument("--output", required=True)
    parse.add_argument("--wide-output", help="Optional original-category table for an authorised join")
    parse.set_defaults(function=parse_records)
    secondary = sub.add_parser("prepare-secondary", help="Predictor preparation and four-way partitioning")
    secondary.add_argument("--australian", required=True)
    secondary.add_argument("--ctu")
    secondary.add_argument("--cohort", choices=("full", "restricted"), default="full")
    secondary.add_argument("--seed", type=int, default=42)
    secondary.add_argument("--output", required=True)
    secondary.set_defaults(function=prepare_secondary)
    probability = sub.add_parser("evaluate-probabilities", help="Evaluation of existing probability predictions")
    probability.add_argument("--input", required=True)
    probability.add_argument("--probability-column", required=True)
    probability.add_argument("--reference-column")
    probability.add_argument("--stage", choices=("heldout", "external"), default="external")
    probability.add_argument("--seed", type=int, default=42)
    probability.add_argument("--reference-seed", type=int)
    probability.add_argument("--bootstrap-reps", type=int, default=2000)
    probability.add_argument("--output", required=True)
    probability.set_defaults(function=evaluate_predictions)
    args = parser.parse_args()
    if getattr(args, "bootstrap_reps", 1) < 1:
        parser.error("bootstrap-reps must be positive")
    try:
        args.function(args)
    except (ValueError, KeyError, FileExistsError, FileNotFoundError) as error:
        parser.exit(2, f"{error}\n")


if __name__ == "__main__":
    main()
