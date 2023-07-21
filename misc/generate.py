"""VDOT table generating script with a SQLite dump as output.

This script aims to create VDOT tables and produce _embeddable_ output
to a main Python program. The format decided on is a base64-encoded gzipped
SQLite dump.

The tables are created for VDOT values between 30.0 and 85.0
based on the findings of the notebooks accompanying this project.
To simplify the table's primary key, VDOTs are stored as integers obtained
by multiplying the original value by 10.
Times are stored in total seconds and paces are stored in seconds/km.
"""
import base64
import gzip
import io
import math
import sqlite3
import textwrap

from scipy import optimize

create_stmt = """\
CREATE TABLE vdot (
  v           INTEGER PRIMARY KEY,
  five_k_time INTEGER NOT NULL,
  ten_k_time  INTEGER NOT NULL,
  hm_time     INTEGER NOT NULL,
  m_time      INTEGER NOT NULL,
  e_pace_1    INTEGER NOT NULL,
  e_pace_2    INTEGER NOT NULL,
  m_pace      INTEGER NOT NULL,
  t_pace      INTEGER NOT NULL,
  i_pace      INTEGER NOT NULL,
  r_pace      INTEGER NOT NULL
) WITHOUT ROWID, STRICT;
"""


def f(x, vdot, d):
    """Estimate race times based on vdot and distance."""
    return (-4.6 + 0.182258 * d * x ** (-1) + 0.000104 * d**2 * x ** (-2)) / (
        0.8 + 0.1894393 * math.exp(-0.012778 * x) + 0.2989558 * math.exp(-0.1932605 * x)
    ) - vdot


def g(x, p):
    """Estimate paces based on vdot and pct of VO2max."""
    return (-0.182258 + math.sqrt(0.033218 - 0.000416 * (-4.6 - (x * p)))) / 0.000208


def main():
    conn = sqlite3.connect(":memory:")
    conn.executescript(create_stmt)

    for v in range(300, 851):
        vdot = v / 10

        times = []
        for d in [5000, 10000, 21097.5, 42195]:
            root = optimize.bisect(f, 1, 600, args=(vdot, d))
            time_in_seconds = round(root * 60)
            times.append(time_in_seconds)

        paces = []
        for pct in [0.6304, 0.7346, 0.8799, 0.9743]:
            p_in_seconds = (1000 / g(vdot, pct)) * 60
            p_rounded = round(p_in_seconds)
            paces.append(p_rounded)

        m_pace = round(times[-1] / 42.195)
        r_pace = paces[-1] - (20 if vdot < 50.0 else 15)

        conn.execute(
            "INSERT INTO vdot VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (v, *times, *paces[:2], m_pace, *paces[2:], r_pace),
        )

    dump = io.BytesIO()
    for line in conn.iterdump():
        raw_line = bytes(line, "utf-8") + b"\n"
        dump.write(raw_line)

    raw_compressed64 = base64.b64encode(gzip.compress(dump.getvalue()))
    compressed64 = raw_compressed64.decode("utf-8")
    final = "\n".join(textwrap.wrap(compressed64, 88))

    print(final)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
