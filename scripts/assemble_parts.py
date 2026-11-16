"""Rebuild data/power_<var>.csv.gz from the base64 parts uploaded through the browser.

The parts exist only because the data were moved into the repo in chunks; scripts/fetch_data.py writes the
same .csv.gz files directly when run on a machine with internet access.

AI disclosure: this file was generated with the assistance of Claude (Anthropic), a generative AI
model, as part of the Dunkelflaute Explorer for NASA Space Apps 2026. The team directed the work and
reviewed and tested the code.
"""
import base64
import re
from collections import defaultdict
from pathlib import Path

__ai_generated__ = True
__ai_tool__ = "Claude (Anthropic)"
__ai_disclosure__ = "Code generated with AI assistance; directed, reviewed and tested by the team."

DATA = Path(__file__).resolve().parent.parent / "data"


def main():
    groups = defaultdict(list)
    for p in DATA.glob("*.b64part*"):
        m = re.match(r"(.+)\.b64part(\d+)$", p.name)
        groups[m.group(1)].append((int(m.group(2)), p))
    for name, parts in groups.items():
        text = "".join(p.read_text().strip() for _, p in sorted(parts))
        (DATA / name).write_bytes(base64.b64decode(text))
        print("rebuilt", name, len(parts), "parts")


if __name__ == "__main__":
    main()
