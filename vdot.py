"""VDOT calculator TUI app.

This is a TUI application that implements a VDOT calculator.
It uses an embedded pre-computed table (a base64-encoded gzipped SQLite dump)
with values ranging from 30.0 to 85.0.
This is the same range used by Daniels for his VDOT tables
(Daniels' Running Formula, 3rd edition).

I chose to go the table route instead of computing values on the fly
to limit the package dependencies to the TUI framework.
While it (hopefully) results in a faster application,
I'm pretty confident that most of the perceived performance improvement
comes from avoiding importing SciPy on startup and not from "runtime" computation costs.
"""
import base64
import datetime
import gzip
import math
import sqlite3
from typing import Optional

from rich import box
from rich.table import Table
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.validation import Regex
from textual.widget import Widget
from textual.widgets import Input, Select, Static

__version__ = "0.1.0"

magic = """\
H4sIAGHeumQC/52dW48tx3me7/UrNnxlA3PRda6CrmiFcIhIZEBtxfCVENgMIgROgkDQ78/7vFW9Zs2QZnUvA9ub
W7PmWd1V3+Gtr07/+O0/fff9l68/fvP9H7/53dfvfvj+t7/53Y/ffvP12y9fv/nH33/75W//9n/++uXvf/Ply9++
vP/fd99//fafvv3xy3/98bs/fPPjv3z5L9/+y5s+8j/+8ref/vy//vzXv/z7T4+PfP/D1y/f/+n3v+fnf/3pf58/
/sWf/89/Xz/88ss/f/rxL/78pz//3//+rz/9OWx+Hv9jPj//j/l/3fz8L5uf/79f+flv/uHLP3/39T//8KevX378
4Z+/+09vX/749cfvfvf1t7/57vs/fvvjV37hhy9/R3f83Zf/9s3v//TtH/8+Hcdb6Dm8pR7HW8+tvYWW+njLo73l
HN9yiPpZfktFf1L+h1+HBcFS1S+ELph+RbCcBKuCBcH4onQRFoHxCwcw/VdokacaRbBDsIOnFkzAlDawJFjUkzUR
ehZRsKLXG3q6pNc9Bk8tmIApbmAZmD7cumCpF2AHTyZg6m/g9dSC6TMpbGD67R54slYFq3rrFipPpvZKggqspxZM
wHRsYBUYT1aB6cUECzyZ2ksdkw++SE+XBYxjA5MtdP9CKYIFTONoai/MI2XBCk8tmICxb2AdGE+WBYsD0zhkcllN
mJOgalQ9tWACxraB8V6DJ0vAmtqsDnVD7nrFpLZTd+upBdNnYv11mMxIMJ4sAlMzC4axApTV5fnUggkYywaGlXZ6
LACLeuvah0xCLpSTOkH+pqcWTMC48YCALWDh7QBG59ZeeE21l9oujXEDJg9o9FaV/8g/MzB9Q5bVZz1n0lOqCd7w
1xQ37hToPj6s5xGsil1bpTf1ilFfMtwEgukzceNOAf+p+vbagKnpBZOvZll9xmfd02o3wlTcuJM8STC9Qq3AIr1Z
aXxZfVYHJ729mkAwAePGnWzyhSfDA45Bb1aCotoxRzW6zDjx5HK0FDbuFIg5BL4qq+wHkbZWmUOW1eeoJx48tdpN
EUQf3sDwAJy4JmAF0yh60ixDzVGNPuiceg1GI+GWCj6KZ4d8SjCiBs5OnMM71JxJ4UhtsoHhATRuDcCwlOpXlLlk
fVMa/Iz4r6cLG9+MeAAfrIofbQzsLOv5ciOZjAUj/uvpwsY3Ix5AQikDWANGD+ZGMiFk057Efz1d2LhTxAOw9KLf
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
oX73wx/+8N3X3/7m/wPg+z6nc6UAAA=="""


class InputPanel(Widget):
    DEFAULT_CSS = """
    InputPanel {
        layout: vertical;
        width: 40%;
    }

    InputPanel > Horizontal {
        height: 3;
        padding: 0 4 0 0;
        margin: 0 0 1 0;
    }

    #indicator {
        width: 10;
        content-align: center middle;
    }

    .default { border: round $accent;  }
    .good    { border: round $success; }
    .bad     { border: round $error;   }

    InputPanel > Select { margin-bottom: 1; }
    """

    class Changed(Message):
        def __init__(self, vdot_value: Optional[float]) -> None:
            self.vdot_value = vdot_value
            super().__init__()

    vdot_value = reactive(None, init=False)

    def __init__(self) -> None:
        self.distance = None
        self.duration = None

        super().__init__()

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Container()

            indicator = Static("?", id="indicator", classes="default")
            indicator.border_title = "VDOT"
            yield indicator

        yield Select(
            [
                ("5K", 5000),
                ("10K", 10000),
                ("Half-Marathon", 21097.5),
                ("Marathon", 42195),
            ],
            prompt="Event distance",
            allow_blank=False,
        )
        yield Input(
            placeholder="Time (hh:mm:ss)",
            validators=Regex(r"^(?:(?:\d+:)?[0-5]\d:[0-5]\d)|(?:[0-5]?\d:[0-5]\d)$"),
        )

    @staticmethod
    def _parse_duration(s: str) -> datetime.timedelta:
        for f in ["%H:%M:%S", "%M:%S"]:
            try:
                return datetime.datetime.strptime(s, f) - datetime.datetime(1900, 1, 1)
            except ValueError:
                continue

        raise ValueError

    @staticmethod
    def _vdot(distance: float, duration: datetime.timedelta) -> float:
        t = duration.total_seconds() / 60
        v = distance / t

        vo2 = -4.6 + 0.182258 * v + 0.000104 * v**2
        pct = (
            0.8
            + 0.1894393 * math.exp(-0.012778 * t)
            + 0.2989558 * math.exp(-0.1932605 * t)
        )
        return round(vo2 / pct, 1)

    def on_select_changed(self, event: Select.Changed) -> None:
        self.distance = event.value
        if self.duration:
            self.vdot_value = self._vdot(self.distance, self.duration)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.validation_result.is_valid is False:
            self.duration = None
            self.vdot_value = None
            return

        self.duration = self._parse_duration(event.value)
        if self.distance:
            self.vdot_value = self._vdot(self.distance, self.duration)

    def watch_vdot_value(self, v: Optional[float]) -> None:
        indicator = self.query_one("#indicator")
        if v is None:
            indicator.set_classes("default")
            indicator.update("?")
        else:
            indicator.set_classes("good" if 30 <= v <= 85 else "bad")
            indicator.update(str(v))

        self.post_message(self.Changed(self.vdot_value))


class ResultsPanel(Widget):
    DEFAULT_CSS = """
    ResultsPanel {
        layout: vertical;
        padding: 1 4;
        width: 60%;
    }

    #races { margin-bottom: 1; }
    """

    vdot_value = reactive(None)

    def __init__(self) -> None:
        self.db = sqlite3.connect(":memory:")
        restore = gzip.decompress(base64.b64decode(magic)).decode("utf-8")
        self.db.executescript(restore)

        super().__init__()

    def compose(self) -> ComposeResult:
        yield Static(id="races")
        yield Static(id="paces")

    @staticmethod
    def _format_duration(s):
        hh, mm, ss = s // 3600, s // 60 % 60, s % 60

        if hh > 0:
            return f"{hh}:{mm:02}:{ss:02}"

        return f"{mm}:{ss:02}"

    def _generate_races_table(self) -> Table:
        table = Table(
            "Race",
            "Time",
            title="Equivalent race performances",
            box=box.SIMPLE_HEAD,
            expand=True,
            title_justify="left",
        )

        races = ["5K", "10K", "Half-Marathon", "Marathon"]
        if self.vdot_value is None or not (30 <= self.vdot_value <= 85):
            for r in races:
                table.add_row(r, "-")
            return table

        pk = int(self.vdot_value * 10)
        row = self.db.execute("SELECT * FROM vdot WHERE v = ?", (pk,)).fetchone()
        for r, t in zip(races, row[1:5]):
            table.add_row(r, self._format_duration(t))

        return table

    def _generate_paces_table(self) -> Table:
        table = Table(
            "Type",
            "Pace (min/km)",
            title="Training paces",
            box=box.SIMPLE_HEAD,
            expand=True,
            title_justify="left",
        )

        pace_types = ["Easy", "Marathon", "Threshold", "Interval", "Repetitions"]
        if self.vdot_value is None or not (30 <= self.vdot_value <= 85):
            for t in pace_types:
                table.add_row(t, "-")
            return table

        pk = int(self.vdot_value * 10)
        row = self.db.execute("SELECT * FROM vdot WHERE v = ?", (pk,)).fetchone()

        paces = [self._format_duration(p) for p in row[5:]]
        easy2 = paces.pop(1)
        paces[0] = easy2 + " - " + paces[0]

        for r, p in zip(pace_types, paces):
            table.add_row(r, p)

        return table

    def watch_vdot_value(self, v: Optional[float]) -> None:
        races_table = self._generate_races_table()
        paces_table = self._generate_paces_table()

        self.query_one("#races").update(races_table)
        self.query_one("#paces").update(paces_table)


class CalculatorApp(App):
    CSS = """
    Screen {
        layout: horizontal;
    }
    """

    def compose(self) -> ComposeResult:
        yield InputPanel()
        yield ResultsPanel()

    def on_input_panel_changed(self, message: InputPanel.Changed) -> None:
        self.query_one("ResultsPanel").vdot_value = message.vdot_value


def main() -> int:
    app = CalculatorApp()
    app.run()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
