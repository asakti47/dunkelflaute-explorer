"""Download NASA POWER daily data for the study grid and the NOAA monthly NAO index into data/."""
import sys
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dfx import config, power_api  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data"
NAO_URL = "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/norm.nao.monthly.b5001.current.ascii"


def main():
    DATA.mkdir(exist_ok=True)
    grid = power_api.fetch_grid()
    grid["pid"] = grid["lat"].map("{:.1f}".format) + "_" + grid["lon"].map("{:.1f}".format)
    grid["date"] = grid["date"].dt.strftime("%Y%m%d")
    for var in ("wind_50m", "ghi", "t2m", "ps", "cloud"):
        wide = grid.pivot(index="date", columns="pid", values=var).fillna(-999.0).round(2)
        wide.to_csv(DATA / f"power_{var}.csv.gz", compression="gzip")
    print("points:", grid["pid"].nunique(), "days:", grid["date"].nunique())
    try:
        txt = requests.get(NAO_URL, timeout=60).text
        nao = pd.read_csv(StringIO(txt), sep=r"\s+", header=None, names=["year", "month", "nao"])
        nao.to_csv(DATA / "nao_monthly.csv", index=False)
        print("nao rows:", len(nao))
    except Exception as e:  # noqa: BLE001 - NAO is optional
        print("NAO download failed, continuing without it:", e)


if __name__ == "__main__":
    main()
