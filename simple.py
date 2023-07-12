import datetime
import math
from typing import Optional

from rich import box
from rich.table import Table
from scipy import optimize
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.validation import Regex
from textual.widgets import Input, Select, Static

distance_options = {
    "Marathon": 42195,
    "Half-Marathon": 21097.5,
    "10K": 10000,
    "5K": 5000,
}

pace_types = {
    "Easy": (0.59, 0.74),
    "Marathon": (0.75, 0.84),
    "Threshold": (0.83, 0.88),
    "Interval": (0.95, 1),
    "Repetition": (1.05, 1.2),
}

valid_duration = r"^(?:([0-9]{1,2}:[0-9]{2}:[0-9]{2})|([0-9]{1,2}:[0-9]{2}))$"


def parse_duration(s: str) -> datetime.timedelta:
    for f in ["%H:%M:%S", "%M:%S"]:
        try:
            return datetime.datetime.strptime(s, f) - datetime.datetime(1900, 1, 1)
        except ValueError:
            continue

    raise ValueError


class CalculatorApp(App):
    CSS_PATH = "styles.css"

    vdot_value = reactive(None, init=False)

    races_table = reactive(None)
    training_table = reactive(None)

    def __init__(self) -> None:
        self.distance = None
        self.duration = None

        super().__init__()

    def compose(self) -> ComposeResult:
        with Vertical():
            with Horizontal(id="vdot-container"):
                yield Container()

                vdot_widget = Static("?", id="vdot", classes="default")
                vdot_widget.border_title = "VDOT"
                yield vdot_widget

            yield Select(
                distance_options.items(), prompt="Event distance", allow_blank=False
            )
            yield Input(placeholder="Time (hh:mm:ss)", validators=Regex(valid_duration))

        with Vertical(id="results"):
            yield Static(id="equivalent-races")
            yield Static(id="training-paces")

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
        return vo2 / pct

    def on_select_changed(self, event: Select.Changed) -> None:
        self.distance = event.value
        if self.duration:
            self.vdot_value = self._vdot(self.distance, self.duration)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.validation_result.is_valid is False:
            self.duration = None
            self.vdot_value = None
            return

        self.duration = parse_duration(event.value)
        if self.distance:
            self.vdot_value = self._vdot(self.distance, self.duration)

    def validate_vdot_value(self, v: Optional[float]) -> Optional[float]:
        widget = self.query_one("#vdot")
        if v is None:
            widget.set_classes("default")
            return None

        widget.set_classes("good" if 25 <= v <= 85 else "bad")
        return v

    def watch_vdot_value(self, v: Optional[float]) -> None:
        display = "?" if v is None else f"{v:.1f}"
        self.query_one("#vdot").update(display)

    @staticmethod
    def _format_duration(td: datetime.timedelta) -> str:
        s = int(td.total_seconds())
        hh, mm, ss = s // 3600, s // 60 % 60, s % 60

        if hh > 0:
            return f"{hh:02}:{mm:02}:{ss:02}"

        return f"{mm:02}:{ss:02}"

    @staticmethod
    def _f(x: float, vdot: float, d: float) -> float:
        return (-4.6 + 0.182258 * d * x ** (-1) + 0.000104 * d**2 * x ** (-2)) / (
            0.8
            + 0.1894393 * math.exp(-0.012778 * x)
            + 0.2989558 * math.exp(-0.1932605 * x)
        ) - vdot

    def compute_races_table(self) -> Table:
        table = Table(
            "Race",
            "Time",
            "Pace (min/km)",
            title="Equivalent race performances",
            box=box.SIMPLE_HEAD,
            expand=True,
            title_justify="left",
        )
        if self.vdot_value is None or not (25 <= self.vdot_value <= 85):
            for race in distance_options:
                table.add_row(race, "-", "-")
            return table

        for race, d in distance_options.items():
            try:
                root = optimize.bisect(self._f, 0.1, 600, args=(self.vdot_value, d))
            except ValueError:
                table.add_row(race, "-", "-")
                continue

            duration_s = self._format_duration(datetime.timedelta(minutes=root))
            pace_s = self._format_duration(datetime.timedelta(minutes=root / d * 1000))

            table.add_row(race, duration_s, pace_s)

        return table

    def watch_races_table(self, t: Table) -> None:
        self.query_one("#equivalent-races").update(t)

    @staticmethod
    def _g(vdot: float, pct: float) -> float:
        return (
            -0.182258 + math.sqrt(0.033218 - 0.000416 * (-4.6 - (vdot * pct)))
        ) / 0.000208

    def compute_training_table(self) -> Table:
        table = Table(
            "Type",
            "Pace range (min/km)",
            title="Training paces",
            box=box.SIMPLE_HEAD,
            expand=True,
            title_justify="left",
        )

        if self.vdot_value is None or not (25 <= self.vdot_value <= 85):
            for t in pace_types:
                table.add_row(t, "-")
            return table

        for t, pcts in pace_types.items():
            p = [self._g(self.vdot_value, pct) for pct in pcts]
            p = [1000 / pace for pace in p]
            p = [self._format_duration(datetime.timedelta(minutes=pace)) for pace in p]

            slower, faster = p
            table.add_row(t, f"{faster} ~ {slower}")

        return table

    def watch_training_table(self, t: Table) -> None:
        self.query_one("#training-paces").update(t)


if __name__ == "__main__":
    app = CalculatorApp()
    app.run()
