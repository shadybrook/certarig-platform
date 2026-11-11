# CR-EXT-R1 deliverable

Open `index.html` directly. The PDF and `ORDER_LIST.md` contain the full63-line list and contracts. Stock/prices are not assumed.

Offline verification (Python3.10+):

    python3 validate.py verify .

Re-solve electrical matrix (ngspice47):

    python3 validate.py run /absolute/path/to/new-evidence

`cases/` contains exact netlists, logs, compressed CSV and criteria; `hydraulic/` contains RK4 traces; `safety.json` contains temporal state samples. `summary.json` is the index. The manifest must be regenerated only when intentionally rebuilding the pack; do not use that operation to hide altered evidence.

Models do not authorize physical commissioning. Q01 supplier compliance is the next gate. No purchases made.
