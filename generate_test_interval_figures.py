"""Sukuria skaitinę keturių 24 val. galutinio testo intervalų peržiūrą.

Naudojamos tik jau išsaugotos galutinio testo prognozės; šis scenarijus nieko
nemoko ir nekeičia modelio ar jo hiperparametrų.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(Path.cwd() / ".matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


METHODS = ["last", "hour_mean", "RF", "SVR", "SVR_W"]
LABELS = {
    "last": "Paskutinė reikšmė",
    "hour_mean": "Paros valandos vidurkis",
    "RF": "RF",
    "SVR": "SVR",
    "SVR_W": "Svertinė SVR (w=5)",
}
COLORS = {
    "last": "#777777", "hour_mean": "#9c755f", "RF": "#1f77b4",
    "SVR": "#ff7f0e", "SVR_W": "#d62728",
}


def per_block(predictions: pd.DataFrame) -> pd.DataFrame:
    """Apskaičiuoja vienodas blokines metrikas kiekvienam 24 val. testui."""
    key = ["scenario", "length", "mask_seed", "block_id"]
    rows = []
    for values, frame in predictions.groupby(key, sort=False):
        pivot = frame.pivot(index="timestamp", columns="source", values="co_hat_mg_m3")
        truth = frame.drop_duplicates("timestamp").set_index("timestamp")["y_true"].reindex(pivot.index)
        row = dict(zip(key, values))
        row["n"] = len(truth)
        row["max_true"] = truth.max()
        for method in METHODS:
            row[method] = (pivot[method] - truth).abs().mean()
        row["weighted_gain_vs_svr"] = row["SVR"] - row["SVR_W"]
        rows.append(row)
    return pd.DataFrame(rows)


def choose_blocks(stats: pd.DataFrame, threshold: float) -> list[tuple[str, pd.Series]]:
    """Parenka blokus pagal iš anksto aprašytus skaitinius kriterijus."""
    primary = stats[stats["scenario"].eq("A")].copy()
    typical = primary[primary["max_true"] < threshold].copy()
    typical["distance_from_rf_median"] = (typical["RF"] - primary["RF"].median()).abs()
    typical = typical.sort_values(["distance_from_rf_median", "scenario", "mask_seed", "block_id"]).iloc[0]
    worst_rf = stats.sort_values(["RF", "scenario", "mask_seed", "block_id"], ascending=[False, True, True, True]).iloc[0]
    extreme = stats.sort_values(["max_true", "scenario", "mask_seed", "block_id"], ascending=[False, True, True, True]).iloc[0]
    improved = primary.sort_values(["weighted_gain_vs_svr", "mask_seed", "block_id"], ascending=[False, True, True]).iloc[0]
    return [
        ("tipinis_geras", typical),
        ("blogiausias_rf", worst_rf),
        ("tikras_ekstremumas", extreme),
        ("weighted_svr_pagerėjimas", improved),
    ]


def interval_data(predictions: pd.DataFrame, row: pd.Series) -> tuple[pd.DataFrame, pd.Series]:
    key = (predictions["scenario"].eq(row.scenario) & predictions["length"].eq(row.length)
           & predictions["mask_seed"].eq(row.mask_seed) & predictions["block_id"].eq(row.block_id))
    part = predictions[key].copy()
    curves = part.pivot(index="timestamp", columns="source", values="co_hat_mg_m3").reindex(columns=METHODS)
    truth = part.drop_duplicates("timestamp").set_index("timestamp")["y_true"].reindex(curves.index)
    return curves, truth


def block_metrics(curves: pd.DataFrame, truth: pd.Series, threshold: float) -> pd.DataFrame:
    rows = []
    actual_extreme = truth >= threshold
    for method in METHODS:
        error = curves[method] - truth
        warnings = curves[method] >= threshold
        tp = int((warnings & actual_extreme).sum())
        fn = int((~warnings & actual_extreme).sum())
        fp = int((warnings & ~actual_extreme).sum())
        recall = tp / (tp + fn) if tp + fn else float("nan")
        precision = tp / (tp + fp) if tp + fp else float("nan")
        rows.append(dict(source=method, mae=error.abs().mean(), rmse=(error.pow(2).mean()) ** .5,
                         signed_error=error.mean(), peak_prediction=curves[method].max(),
                         recall=recall, precision=precision, tp=tp, fn=fn, fp=fp))
    return pd.DataFrame(rows).set_index("source")


def conclusions(kind: str, row: pd.Series, measures: pd.DataFrame, truth: pd.Series, threshold: float) -> list[str]:
    best = measures["mae"].idxmin()
    n_extreme = int((truth >= threshold).sum())
    common = [
        f"Tikros CO maksimumas: {truth.max():.2f} mg/m³; virš q95={threshold:.2f} yra {n_extreme}/{len(truth)} val.",
        f"Mažiausias bloko MAE: {LABELS[best]} = {measures.loc[best, 'mae']:.3f} mg/m³.",
    ]
    if kind == "tipinis_geras":
        common.append(f"RF MAE={measures.loc['RF','mae']:.3f}; pasirinktas neekstremalus A/24 blokas, artimiausias A/24 blokų RF MAE medianai.")
    elif kind == "blogiausias_rf":
        common.append(f"RF MAE={measures.loc['RF','mae']:.3f}; tai didžiausia reikšmė tarp {int(row.total_blocks)} 24 val. blokų.")
    elif kind == "tikras_ekstremumas":
        common.append(f"RF/SVR/weighted SVR prognozuoti pikai: {measures.loc['RF','peak_prediction']:.2f} / {measures.loc['SVR','peak_prediction']:.2f} / {measures.loc['SVR_W','peak_prediction']:.2f} mg/m³.")
    else:
        gain = measures.loc["SVR", "mae"] - measures.loc["SVR_W", "mae"]
        pct = 100 * gain / measures.loc["SVR", "mae"]
        common.append(f"Weighted SVR MAE={measures.loc['SVR_W','mae']:.3f}, SVR={measures.loc['SVR','mae']:.3f}: pagerėjimas {gain:.3f} mg/m³ ({pct:.1f} %).")
    return common


def make_plot(kind: str, row: pd.Series, predictions: pd.DataFrame, threshold: float, output: Path) -> tuple[Path, list[str], pd.DataFrame]:
    curves, truth = interval_data(predictions, row)
    measures = block_metrics(curves, truth, threshold)
    notes = conclusions(kind, row, measures, truth, threshold)
    title = (f"{kind.replace('_', ' ').capitalize()}: {row.scenario}, "
             f"kaukė {int(row.mask_seed)}, blokas {int(row.block_id)}")

    fig = plt.figure(figsize=(13, 7.3), constrained_layout=True)
    grid = fig.add_gridspec(2, 1, height_ratios=[4.5, 1.35])
    ax = fig.add_subplot(grid[0])
    ax.axvspan(truth.index.min(), truth.index.max(), color="#ffe699", alpha=.36, label="Paslėptas 24 val. intervalas")
    ax.plot(truth.index, truth, color="#111111", linewidth=2.8, marker="o", markersize=3.5, label="Tikras CO")
    for method in METHODS:
        ax.plot(curves.index, curves[method], color=COLORS[method], linewidth=1.8,
                marker=".", markersize=4, alpha=.93, label=LABELS[method])
    ax.axhline(threshold, color="#b22222", linestyle="--", linewidth=1.2, label=f"q95 = {threshold:.2f}")
    ax.set_title(title, loc="left", fontweight="bold")
    ax.set_ylabel("CO, mg/m³")
    ax.set_xlabel("Laikas")
    ax.grid(alpha=.25)
    ax.legend(ncols=3, loc="upper left", fontsize=8.5)
    ax.tick_params(axis="x", rotation=25)

    caption = fig.add_subplot(grid[1])
    caption.axis("off")
    caption.text(.01, .90, "Automatinės skaitinės išvados", fontsize=11, fontweight="bold", va="top")
    for i, note in enumerate(notes, 1):
        caption.text(.02, .66 - (i - 1) * .27, f"{i}. {note}", fontsize=9.4, va="top")
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return output, notes, measures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default="results_final_locked")
    args = parser.parse_args()
    root = Path(args.results)
    predictions = pd.read_csv(root / "predictions.csv.gz", parse_dates=["timestamp"])
    predictions = predictions[(predictions["length"] == 24) & predictions["source"].isin(METHODS)].copy()
    selection = json.loads((root / "selection.json").read_text(encoding="utf-8"))
    threshold = float(selection["threshold_q95"])
    stats = per_block(predictions)
    stats["total_blocks"] = len(stats)
    out = root / "interval_figures"
    report = []
    for kind, row in choose_blocks(stats, threshold):
        path, notes, measures = make_plot(kind, row, predictions, threshold, out / f"{kind}.png")
        report.append(dict(kind=kind, scenario=row.scenario, mask_seed=int(row.mask_seed), block_id=int(row.block_id),
                           start=str(interval_data(predictions, row)[1].index.min()), end=str(interval_data(predictions, row)[1].index.max()),
                           notes=notes, metrics=measures.reset_index().to_dict(orient="records"), image=path.name))
    (out / "selected_intervals.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    html = ["<!doctype html><meta charset='utf-8'><title>Galutinio testo intervalų grafikai</title>",
            "<style>body{font-family:Arial,sans-serif;max-width:1280px;margin:28px auto;line-height:1.45}img{max-width:100%;border:1px solid #ddd}h1{margin-bottom:4px}p{color:#333}</style>",
            "<h1>Galutinio testo 24 val. intervalų analizė</h1>",
            "<p>Grafikai sukurti iš užfiksuoto vienkartinio testo prognozių. Geltonas plotas žymi CO etalono slėpimo intervalą.</p>"]
    for item in report:
        html += [f"<h2>{item['kind'].replace('_', ' ').capitalize()}</h2>", f"<img src='{item['image']}' alt='{item['kind']}'>",
                 "<ol>" + "".join(f"<li>{note}</li>" for note in item["notes"]) + "</ol>"]
    (out / "ataskaita_intervalai.html").write_text("\n".join(html), encoding="utf-8")
    print(f"Sukurta {len(report)} grafikų: {out}")


if __name__ == "__main__":
    main()

