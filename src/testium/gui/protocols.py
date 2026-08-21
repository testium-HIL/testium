# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""View and scheduler protocols implemented by the Qt layer (main_win).
Presenters only ever talk to these; they never import a toolkit."""

from dataclasses import dataclass
from typing import Callable, Protocol


class Scheduler(Protocol):
    """Named repeating/one-shot timers (Qt: QTimer; tests: manual ticks)."""

    def every(self, name: str, interval_ms: int,
              tick: Callable[[], None]) -> None: ...

    def once(self, name: str, delay_ms: int,
             fire: Callable[[], None]) -> None: ...

    def cancel(self, name: str) -> None: ...


@dataclass(frozen=True)
class RunUiState:
    """What the run lifecycle needs from the interface, in one push."""
    running: bool
    steps_enabled: bool


class RunView(Protocol):
    """Interface surface driven by the run presenter."""

    def apply_run_ui(self, state: RunUiState) -> None: ...

    def set_start_action(self, text, icon: str) -> None:
        """text None keeps the current text; icon is a theme icon name."""

    def set_status_light(self, color: str) -> None:
        """'green', 'red' or 'gray'."""

    def set_elapsed(self, text: str) -> None: ...

    def append_log(self, text: str) -> None: ...

    def clear_log(self) -> None: ...

    def show_transient_message(self, text: str) -> None: ...

    def can_start(self) -> bool: ...

    def test_file(self) -> str: ...

    def log_config(self) -> tuple:
        """(path text, save-to-file enabled)."""

    def set_log_file_name(self, path: str) -> None: ...

    def report_config(self) -> tuple:
        """(report file, report type, report pattern)."""

    def attach_log_sink(self, handle) -> None: ...

    def detach_log_sink(self) -> None: ...

    def read_captured(self) -> str: ...

    def reset_run_marks(self) -> None:
        """Clear per-item statuses and the run verdict."""

    def clear_current_marks(self) -> None:
        """Drop the current-item highlights."""

    def run_succeeded(self) -> bool: ...

    def close_window(self) -> None: ...
