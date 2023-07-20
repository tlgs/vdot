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


def _f(x, vdot, d):
    return (-4.6 + 0.182258 * d * x ** (-1) + 0.000104 * d**2 * x ** (-2)) / (
        0.8 + 0.1894393 * math.exp(-0.012778 * x) + 0.2989558 * math.exp(-0.1932605 * x)
    ) - vdot


def _g(x, p):
    return (-0.182258 + math.sqrt(0.033218 - 0.000416 * (-4.6 - (x * p)))) / 0.000208


def main():
    conn = sqlite3.connect(":memory:")
    conn.executescript(create_stmt)

    for vdot in (x / 10 for x in range(300, 851)):
        times = []
        for d in [5000, 10000, 21097.5, 42195]:
            root = optimize.bisect(_f, 1, 600, args=(vdot, d))
            time_in_seconds = int(root * 60)
            times.append(time_in_seconds)

        paces = []
        for pct in [0.6304, 0.7346, 0.8799, 0.9743]:
            p_in_seconds = (1000 / _g(vdot, pct)) * 60
            p_rounded = round(p_in_seconds)
            paces.append(p_rounded)

        m_pace = round(times[-1] / 42.195)
        r_pace = paces[-1] - (20 if vdot < 50.0 else 15)

        paces.insert(2, m_pace)
        paces.append(r_pace)

        conn.execute(
            "INSERT INTO vdot VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (int(vdot * 10), *times, *paces),
        )

    dump = io.BytesIO()
    for line in conn.iterdump():
        dump.write(bytes(line, "utf-8") + b"\n")

    compressed_dump = base64.b64encode(gzip.compress(dump.getvalue()))
    wrapped_dump = "\n".join(textwrap.wrap(compressed_dump.decode("utf-8"), 88))

    print(wrapped_dump)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
