# CTU-UHB signal rendering

`scripts/render_ctu_signals.py` provides the executable CTU-UHB signal-to-image interface. The supporting functions are in `src/ctg_llm/rendering.py`. These files retain the earlier public renderer's operations and default settings; the command's package import has been updated for this repository.

## Inputs and output

The renderer accepts locally held CTU-UHB WFDB records or the documented signal-only CSV format. WFDB input selects the FHR and UC/TOCO channels and derives the sample interval from the recording frequency. Clinical header comments and outcome fields are not used to construct the rendering frame. CSV input supports `TM`, `FHR1`, `FHR2`, `TOCO` and `TOCOMODE`; `TM` represents the sample interval in milliseconds, with a 250-ms fallback.

The command accepts `--input-directory`, `--output-directory` and `--source-format`; the source format is `wfdb`, `csv` or `auto`. The `rendering` optional dependency group provides the WFDB reader. An optional `--record-list` selects de-identified record identifiers. No input signals, images or completed outputs are distributed.

## Rendering operations

The default window is the final 60 minutes. A shorter recording is displayed over its available interval. The final sample is anchored at T=0. Display axes and dimensions are fixed across records.

FHR values outside 50–210 bpm are masked. An adjacent change exceeding 30 bpm masks both bordering samples. A cubic interpolating spline (`UnivariateSpline`, degree 3, `s=0`) is evaluated within each contiguous valid FHR segment containing at least five samples. It is evaluated at the original sample positions and does not fill missing FHR intervals. Values outside the configured FHR range are masked again, and segments shorter than the configured minimum of 40 samples are removed by default.

When `TOCOMODE` is available, mode 9 is retained. TOCO processing uses linear interpolation with a limit of 10 samples in each direction, followed by a centred three-sample rolling mean. This can fill missing TOCO samples, including eligible values at recording boundaries. At 4 Hz, the interpolation limit corresponds to 2.5 seconds from either direction; a bounded gap of up to 20 samples can therefore be filled. FHR and TOCO do not use the same missing-signal rule. Unfilled intervals remain missing, and the centred rolling mean also requires its neighbouring samples.

The display uses a 40–220 bpm FHR panel with a shaded 120–160 bpm band and a 0–100 TOCO panel. The shaded band is a display feature, separate from the five guideline definitions. Default image dimensions are 22 by 8 inches at 100 dpi. The command exposes the window length, CSV sampling fallback, minimum segment size and resolution; the complete parameter values are retained in the output manifest.

## Traceability and eligibility

The outputs are one PNG per record and a JSON manifest containing parameters, source-file and image checksums, source format, sample interval and input/rendered sample counts. The manifest schema is in `src/ctg_llm/resources/schemas/render_manifest.schema.json`. Output records contain relative paths rather than institutional absolute paths.

The processing uses fixed numerical operations without generative signal reconstruction. Human technical review determines eligibility independently of rendering and LLM quality assessment. The exact configuration used for a study is identified by its retained manifest; the public defaults do not establish the configuration of a historical run.

The underlying CTU-UHB database is available through [PhysioNet](https://doi.org/10.13026/C22013). Study-specific images, labels and linked inputs follow [Code and data availability](../CODE_AND_DATA_AVAILABILITY.md).
