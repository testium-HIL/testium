# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Variables table presenter: row bookkeeping, value formatting, filter
matching, edition parsing and the expression tester."""

import ast
import json
import re

from runtime.tum_except import ETUMRuntimeError


def is_complex(value):
    return isinstance(value, (dict, list))


def display_value(value):
    if is_complex(value):
        text = repr(value)
        return (text[:60] + "…") if len(text) > 60 else text
    return repr(value)


def full_tooltip(value):
    try:
        text = json.dumps(value, indent=2)
    except (TypeError, ValueError):
        text = repr(value)
    escaped = (text.replace("&", "&amp;")
               .replace("<", "&lt;").replace(">", "&gt;"))
    return f"<pre>{escaped}</pre>"


def parse_value(text):
    """A Python literal when it parses, the raw string otherwise."""
    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return text


def error_text(e):
    """Keep the cause only: drop the control-command wrapper and the
    ETUM banner line."""
    text = str(e)
    m = re.search(r"failed: '(.*)'$", text, re.S)
    if m:
        text = m.group(1)
    lines = [l for l in text.splitlines()
             if l.strip() != "TUM runtime error:"]
    return "\n".join(lines).strip()


class VariablesPresenter:
    def __init__(self, view, service) -> None:
        """service: zero-argument callable returning the current
        TestControllerService (None when no test is loaded)."""
        self._view = view
        self._service = service
        self._rows = {}
        self._filter_text = ""
        self._filter_values = False

    # --- rows ---

    def set_available(self, available):
        self._view.set_enabled(available)
        if not available:
            self._view.clear_rows()
            self._rows.clear()

    def load_initial_vars(self, vars_dict):
        for key, value in vars_dict.items():
            self.var_updated(key, value)

    def var_updated(self, key, value):
        if key not in self._rows:
            self._rows[key] = len(self._rows)
            self._view.insert_row(self._rows[key])
        row = self._rows[key]
        self._view.set_row(row, key, display_value(value),
                           full_tooltip(value), value,
                           editable=not is_complex(value))
        self._view.set_row_hidden(row, not self._row_matches(key, value))

    def var_deleted(self, key):
        if key not in self._rows:
            return
        row = self._rows.pop(key)
        self._view.remove_row(row)
        self._rows = {k: (r - 1 if r > row else r)
                      for k, r in self._rows.items()}

    # --- filter ---

    def set_filter(self, text, match_values=None):
        self._filter_text = (text or "").strip().lower()
        if match_values is not None:
            self._filter_values = bool(match_values)
        for key, row in self._rows.items():
            self._view.set_row_hidden(
                row, not self._key_matches(key, row))

    def _key_matches(self, key, row):
        if not self._filter_text:
            return True
        hay = key.lower()
        if self._filter_values:
            hay += "\n" + self._view.row_display(row).lower()
        return self._filter_text in hay

    def _row_matches(self, key, value):
        if not self._filter_text:
            return True
        hay = key.lower()
        if self._filter_values:
            hay += "\n" + display_value(value).lower()
        return self._filter_text in hay

    # --- edition ---

    def edit_value(self, key, text):
        service = self._service()
        if service is not None:
            service.set_gd_var(key, parse_value(text))

    def set_value(self, key, value):
        service = self._service()
        if service is not None:
            service.set_gd_var(key, value)

    def add_var(self, key, value_text):
        key = key.strip()
        service = self._service()
        if not key or service is None:
            return False
        service.set_gd_var(key, parse_value(value_text.strip()))
        return True

    def delete_var(self, key):
        service = self._service()
        if service is not None:
            service.del_gd_var(key)

    # --- expression tester ---

    def evaluate(self, expr):
        expr = expr.strip()
        service = self._service()
        if not expr or service is None:
            return
        try:
            result = service.eval_expr(expr)
        except ETUMRuntimeError as e:
            self._view.show_expr_result(error_text(e), is_error=True)
            return
        self._view.show_expr_result(repr(result), is_error=False)
