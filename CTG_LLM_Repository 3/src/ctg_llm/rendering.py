"""Outcome-blinded rendering of public CTU-UHB signal records.

The functions in this module implement the non-proprietary display operations
used by the public rendering command. They do not extract signals from vendor
systems, derive model features, or read clinical outcome fields.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
from scipy.interpolate import UnivariateSpline


@dataclass(frozen=True)
class RenderSettings:
    """Fixed display and cleaning parameters for the study rendering workflow."""

    window_minutes: float = 60.0
    fallback_sample_period_ms: float = 250.0
    fhr_lower_bpm: float = 50.0
    fhr_upper_bpm: float = 210.0
    fhr_jump_bpm: float = 30.0
    min_segment_samples: int = 40
    toco_mode_value: float = 9.0
    toco_interpolation_limit: int = 10
    toco_rolling_window: int = 3
    dpi: int = 100

    def validate(self) -> "RenderSettings":
        if self.window_minutes <= 0:
            raise ValueError("window_minutes must be positive.")
        if self.fallback_sample_period_ms <= 0:
            raise ValueError("fallback_sample_period_ms must be positive.")
        if self.fhr_lower_bpm >= self.fhr_upper_bpm:
            raise ValueError("The lower FHR bound must be below the upper bound.")
        if self.fhr_jump_bpm <= 0:
            raise ValueError("fhr_jump_bpm must be positive.")
        if self.min_segment_samples < 1:
            raise ValueError("min_segment_samples must be at least one.")
        if self.toco_interpolation_limit < 0:
            raise ValueError("toco_interpolation_limit cannot be negative.")
        if self.toco_rolling_window < 1:
            raise ValueError("toco_rolling_window must be at least one.")
        if self.dpi < 72:
            raise ValueError("dpi must be at least 72.")
        return self

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


@dataclass(frozen=True)
class LoadedTrace:
    """Signal-only record returned by a supported public input reader."""

    record_id: str
    frame: pd.DataFrame
    sample_period_ms: float
    source_files: tuple[Path, ...]
    source_format: str


def _numeric_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        return pd.Series(np.nan, index=frame.index, dtype="float64")
    return pd.to_numeric(frame[column], errors="coerce").astype("float64")


def mask_short_segments(
    series: pd.Series,
    *,
    min_len_samples: int = 40,
) -> pd.Series:
    """Mask contiguous non-missing segments shorter than the stated minimum."""

    if min_len_samples < 1:
        raise ValueError("min_len_samples must be at least one.")
    values = pd.to_numeric(series, errors="coerce").to_numpy(dtype="float64")
    valid = np.isfinite(values)
    if not valid.any():
        return pd.Series(values, index=series.index, dtype="float64")

    changes = np.flatnonzero(np.diff(valid.astype(np.int8)) != 0) + 1
    for indices in np.split(np.arange(values.size), changes):
        if valid[indices[0]] and indices.size < min_len_samples:
            values[indices] = np.nan
    return pd.Series(values, index=series.index, dtype="float64")


def clean_fhr(
    series: pd.Series,
    *,
    lower_bpm: float = 50.0,
    upper_bpm: float = 210.0,
    jump_bpm: float = 30.0,
) -> pd.Series:
    """Apply the disclosed physiologic bounds and adjacent-jump screen."""

    values = pd.to_numeric(series, errors="coerce").to_numpy(dtype="float64")
    outside = (values < lower_bpm) | (values > upper_bpm)
    values[outside] = np.nan
    adjacent_jump = np.abs(np.diff(values)) > jump_bpm
    affected = np.zeros(values.size, dtype=bool)
    affected[:-1] |= adjacent_jump
    affected[1:] |= adjacent_jump
    values[affected] = np.nan
    return pd.Series(values, index=series.index, dtype="float64")


def interpolate_fhr_segments(
    series: pd.Series,
    *,
    lower_bpm: float = 50.0,
    upper_bpm: float = 210.0,
    min_len_samples: int = 40,
) -> pd.Series:
    """Apply cubic interpolation within, but never across, valid FHR segments."""

    values = pd.to_numeric(series, errors="coerce").to_numpy(dtype="float64")
    valid = np.isfinite(values)
    interpolated = np.full(values.shape, np.nan, dtype="float64")
    if valid.any():
        changes = np.flatnonzero(np.diff(valid.astype(np.int8)) != 0) + 1
        for indices in np.split(np.arange(values.size), changes):
            if not valid[indices[0]] or indices.size < 5:
                continue
            x = np.arange(indices.size, dtype="float64")
            spline = UnivariateSpline(x, values[indices], k=3, s=0)
            segment = spline(x)
            segment[(segment < lower_bpm) | (segment > upper_bpm)] = np.nan
            interpolated[indices] = segment
    return mask_short_segments(
        pd.Series(interpolated, index=series.index, dtype="float64"),
        min_len_samples=min_len_samples,
    )


def time_from_trace_end_minutes(
    n_samples: int,
    sample_period_ms: float,
) -> np.ndarray:
    """Return a time axis whose final sample is T=0."""

    if n_samples < 1:
        raise ValueError("At least one sample is required.")
    if sample_period_ms <= 0:
        raise ValueError("sample_period_ms must be positive.")
    return (
        np.arange(n_samples, dtype="float64") - float(n_samples - 1)
    ) * sample_period_ms / 60_000.0


def _normalise_columns(frame: pd.DataFrame) -> pd.DataFrame:
    normalised = frame.copy()
    normalised.columns = [
        re.sub(r"^\[|\]$", "", str(column)).strip()
        for column in normalised.columns
    ]
    return normalised


def load_csv_trace(path: Path, fallback_sample_period_ms: float) -> LoadedTrace:
    """Read the documented TM/FHR1/FHR2/TOCO/TOCOMODE signal-only schema."""

    frame = _normalise_columns(pd.read_csv(path))
    if frame.empty:
        raise ValueError(f"Signal file is empty: {path.name}")
    if not ({"FHR1", "FHR2"} & set(frame.columns)):
        raise ValueError(f"Signal file has no FHR1 or FHR2 column: {path.name}")
    if "TOCO" not in frame:
        raise ValueError(f"Signal file has no TOCO column: {path.name}")

    sample_period_ms = float(fallback_sample_period_ms)
    if "TM" in frame:
        periods = pd.to_numeric(frame["TM"], errors="coerce").dropna()
        if not periods.empty:
            sample_period_ms = float(periods.iloc[0])
    if not np.isfinite(sample_period_ms) or sample_period_ms <= 0:
        raise ValueError(f"Invalid sample period in {path.name}.")

    signals = pd.DataFrame(index=frame.index)
    for column in ("FHR1", "FHR2", "TOCO", "TOCOMODE"):
        signals[column] = _numeric_series(frame, column)
    return LoadedTrace(
        record_id=path.stem,
        frame=signals,
        sample_period_ms=sample_period_ms,
        source_files=(path,),
        source_format="csv",
    )


def _normalised_signal_name(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def _signal_index(names: Iterable[str], aliases: set[str]) -> int | None:
    normalised_aliases = {_normalised_signal_name(value) for value in aliases}
    for index, name in enumerate(names):
        if _normalised_signal_name(name) in normalised_aliases:
            return index
    return None


def load_wfdb_trace(path: Path, input_root: Path) -> LoadedTrace:
    """Read only FHR and uterine-contraction channels from a WFDB record."""

    try:
        import wfdb
    except ImportError as exc:
        raise RuntimeError(
            "WFDB input requires environment/requirements-rendering.txt."
        ) from exc

    stem = path.with_suffix("")
    header = wfdb.rdheader(str(stem))
    record = wfdb.rdrecord(str(stem), physical=True)
    if record.p_signal is None or record.sig_name is None:
        raise ValueError(f"WFDB record has no physical signal matrix: {path.name}")
    fhr_index = _signal_index(record.sig_name, {"FHR", "FHR1"})
    toco_index = _signal_index(record.sig_name, {"UC", "TOCO", "UA"})
    if fhr_index is None or toco_index is None:
        raise ValueError(
            f"WFDB record must contain FHR and UC/TOCO channels: {path.name}"
        )
    if record.fs is None or float(record.fs) <= 0:
        raise ValueError(f"WFDB record has an invalid sampling frequency: {path.name}")

    frame = pd.DataFrame(
        {
            "FHR1": record.p_signal[:, fhr_index],
            "FHR2": np.nan,
            "TOCO": record.p_signal[:, toco_index],
            "TOCOMODE": np.nan,
        }
    )
    source_files = [path]
    for file_name in sorted(set(getattr(header, "file_name", []) or [])):
        candidate = (path.parent / file_name).resolve()
        if not candidate.is_relative_to(input_root.resolve()):
            raise ValueError("A WFDB signal file resolves outside the input directory.")
        if not candidate.is_file():
            raise FileNotFoundError(f"Missing WFDB signal file: {file_name}")
        source_files.append(candidate)
    return LoadedTrace(
        record_id=path.stem,
        frame=frame,
        sample_period_ms=1000.0 / float(record.fs),
        source_files=tuple(dict.fromkeys(source_files)),
        source_format="wfdb",
    )


def discover_signal_files(input_directory: Path, source_format: str) -> list[Path]:
    """Discover one supported source type without mixing input conventions."""

    if source_format not in {"auto", "wfdb", "csv"}:
        raise ValueError("source_format must be auto, wfdb, or csv.")
    headers = sorted(
        path
        for path in input_directory.rglob("*.hea")
        if "__MACOSX" not in path.parts
    )
    csv_files = sorted(
        path
        for path in input_directory.rglob("*.csv")
        if "__MACOSX" not in path.parts
    )
    if source_format == "auto":
        if headers and csv_files:
            raise ValueError(
                "Both WFDB and CSV records were found; select --source-format explicitly."
            )
        files = headers or csv_files
    else:
        files = headers if source_format == "wfdb" else csv_files
    if not files:
        raise FileNotFoundError(
            f"No {source_format if source_format != 'auto' else 'supported'} signal records found."
        )
    return files


def safe_output_stem(record_id: str) -> str:
    """Return a filesystem-safe, non-empty record stem."""

    value = re.sub(r"[^A-Za-z0-9._-]+", "_", record_id).strip("._-")
    if not value:
        raise ValueError("Record identifier cannot be converted to a safe filename.")
    return value


def render_trace(
    trace: LoadedTrace,
    output_path: Path,
    settings: RenderSettings = RenderSettings(),
) -> dict[str, int | float]:
    """Render the final signal window and return non-identifying run counts."""

    settings.validate()
    if trace.frame.empty:
        raise ValueError("The trace contains no samples.")
    sample_count = max(
        1,
        int(round(settings.window_minutes * 60_000 / trace.sample_period_ms)),
    )
    frame = trace.frame.iloc[-sample_count:].reset_index(drop=True)

    fhr1 = interpolate_fhr_segments(
        clean_fhr(
            _numeric_series(frame, "FHR1"),
            lower_bpm=settings.fhr_lower_bpm,
            upper_bpm=settings.fhr_upper_bpm,
            jump_bpm=settings.fhr_jump_bpm,
        ),
        lower_bpm=settings.fhr_lower_bpm,
        upper_bpm=settings.fhr_upper_bpm,
        min_len_samples=settings.min_segment_samples,
    )
    fhr2 = interpolate_fhr_segments(
        clean_fhr(
            _numeric_series(frame, "FHR2"),
            lower_bpm=settings.fhr_lower_bpm,
            upper_bpm=settings.fhr_upper_bpm,
            jump_bpm=settings.fhr_jump_bpm,
        ),
        lower_bpm=settings.fhr_lower_bpm,
        upper_bpm=settings.fhr_upper_bpm,
        min_len_samples=settings.min_segment_samples,
    )
    toco = _numeric_series(frame, "TOCO")
    toco_mode = _numeric_series(frame, "TOCOMODE")
    if toco_mode.notna().any():
        toco = toco.where(toco_mode == settings.toco_mode_value)
    if settings.toco_interpolation_limit:
        toco = toco.interpolate(
            limit=settings.toco_interpolation_limit,
            limit_direction="both",
        )
    toco = toco.rolling(
        window=settings.toco_rolling_window,
        center=True,
    ).mean()
    time_minutes = time_from_trace_end_minutes(
        len(frame),
        trace.sample_period_ms,
    )

    figure, (fhr_axis, toco_axis) = plt.subplots(
        2,
        1,
        figsize=(22, 8),
        sharex=True,
        gridspec_kw={"height_ratios": [2, 1]},
    )
    figure.suptitle(trace.record_id, fontsize=14)

    fhr_axis.set_facecolor("#f4fbf4")
    fhr_axis.axhspan(120, 160, facecolor="#e5f5e0", zorder=0)
    fhr_axis.set_ylim(40, 220)
    fhr_axis.set_ylabel("FHR (bpm)")
    fhr_axis.grid(True, which="major", linestyle="--", linewidth=0.4)
    fhr_axis.grid(True, which="minor", linestyle=":", linewidth=0.25)
    fhr_axis.minorticks_on()
    fhr_axis.yaxis.set_major_locator(ticker.MultipleLocator(20))
    fhr_axis.yaxis.set_minor_locator(ticker.MultipleLocator(5))
    if fhr1.notna().any():
        fhr_axis.plot(
            time_minutes,
            fhr1,
            color="red",
            linewidth=1.0,
            label="FHR (US/FHR1)",
        )
    if fhr2.notna().any():
        fhr_axis.plot(
            time_minutes,
            fhr2,
            color="blue",
            linewidth=1.0,
            label="FHR (ECG/FHR2)",
        )
    if fhr_axis.lines:
        fhr_axis.legend(loc="upper right")

    toco_axis.set_facecolor("#f4fbf4")
    toco_axis.set_ylim(0, 100)
    toco_axis.set_ylabel("TOCO")
    toco_axis.plot(time_minutes, toco, color="black", linewidth=1.0)
    toco_axis.grid(True, which="major", linestyle="--", linewidth=0.4)
    toco_axis.grid(True, which="minor", linestyle=":", linewidth=0.25)
    toco_axis.minorticks_on()
    toco_axis.yaxis.set_major_locator(ticker.MultipleLocator(10))
    toco_axis.yaxis.set_minor_locator(ticker.MultipleLocator(5))

    def format_tminus(value: float, _position: int) -> str:
        minutes = int(round(value))
        return "T=0" if minutes == 0 else f"T-{abs(minutes)}"

    toco_axis.xaxis.set_major_locator(ticker.MultipleLocator(10))
    toco_axis.xaxis.set_minor_locator(ticker.MultipleLocator(1))
    toco_axis.xaxis.set_major_formatter(ticker.FuncFormatter(format_tminus))
    toco_axis.set_xlabel("Time from end of trace (minutes)")
    toco_axis.set_xlim(-settings.window_minutes, 0)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_name(f".{output_path.stem}.tmp.png")
    try:
        figure.tight_layout()
        figure.savefig(temporary_path, dpi=settings.dpi)
        temporary_path.replace(output_path)
    finally:
        plt.close(figure)
        if temporary_path.exists():
            temporary_path.unlink()

    return {
        "input_samples": int(len(trace.frame)),
        "rendered_samples": int(len(frame)),
        "sample_period_ms": float(trace.sample_period_ms),
        "fhr1_rendered_samples": int(fhr1.notna().sum()),
        "fhr2_rendered_samples": int(fhr2.notna().sum()),
        "toco_rendered_samples": int(toco.notna().sum()),
    }
