"""Run the full analysis on the downloaded data and write tables to results/."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dfx import analysis, config, events  # noqa: E402
from dfx.panel import Panel  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "results"


def main(n_boot: int = 1000):
    OUT.mkdir(exist_ok=True)
    panel = Panel.load()
    summary = {}
    for season in ("winter", "year"):
        d = config.Definition(season=season)
        nao = analysis.load_nao(season)
        cf = panel.regional_cf(d)
        ev, m, thr = events.run(cf, d)
        ev.to_csv(OUT / f"events_{season}.csv", index=False)
        m.to_csv(OUT / f"metrics_{season}.csv")
        h = analysis.headline(m, nao)
        h.to_csv(OUT / f"headline_{season}.csv")
        analysis.robustness(panel, d, nao=nao).to_csv(OUT / f"robustness_{season}.csv", index=False)
        analysis.per_cell(panel, d).to_csv(OUT / f"per_cell_{season}.csv", index=False)
        tab, att, cfs = analysis.drivers_and_attribution(panel, d, nao=nao, n_boot=n_boot)
        tab.to_csv(OUT / f"drivers_{season}.csv")
        att.to_csv(OUT / f"attribution_{season}.csv")
        cfs.to_csv(OUT / f"counterfactual_{season}.csv")
        panel.drivers(season, nao).to_csv(OUT / f"drivers_yearly_{season}.csv")
        summary[season] = {"threshold_cf": thr, "n_events": int(len(ev))}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
