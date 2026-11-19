# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Script sandbox panel logic: language and session choice, run, stop,
reset, script files, completion. No toolkit import; the view implements
gui.protocols.SandboxView."""

import base64
import json
import os

from gui import sandbox_syntax as syntax
from gui.variables_presenter import error_text
from runtime.tum_except import ETUMError

OWN_SESSION = "Sandbox"

_LABELS = {"python": "Python", "lua": "Lua", "tcl": "Tcl"}


def encode_state(lang, buffers):
    """Panel state as one ASCII line for the settings file."""
    raw = json.dumps({"lang": lang, "buffers": buffers})
    return base64.b64encode(raw.encode("utf-8")).decode("ascii")


def decode_state(text):
    """(language, buffers) from encode_state output, defaults if invalid."""
    try:
        data = json.loads(base64.b64decode(text).decode("utf-8"))
        lang = data["lang"]
        buffers = {k: str(v) for k, v in data["buffers"].items()
                   if k in syntax.LANGUAGES}
        if lang in syntax.LANGUAGES:
            return lang, buffers
    except Exception:  # noqa: BLE001
        pass
    return "python", {}


class SandboxPresenter:
    def __init__(self, view, service, load_state=None, save_state=None):
        """service: callable returning the controller service or None.
        load_state/save_state: read and write the persisted panel state."""
        self._view = view
        self._service = service
        self._save_state = save_state
        self._lang, self._buffers = decode_state(
            load_state() if load_state else "")
        self._session = None
        self._running = False
        # Per language: path of the open file, and its text when read or
        # written last.
        self._files = {}
        self._saved = {}

    # ----- state pushed to the view -----

    def start(self):
        self._view.set_language(self._lang)
        self._view.set_code(self._buffers.get(self._lang, ""))
        self._show_file()
        self.set_loaded(self._service() is not None)

    def set_loaded(self, loaded):
        """A test was loaded or unloaded."""
        self._running = False
        self._session = None
        self._view.set_sandbox_state(enabled=loaded, running=False)
        self._view.set_sessions([OWN_SESSION], OWN_SESSION)

    def language(self):
        return self._lang

    def session(self):
        return self._session

    def _show_file(self):
        path = self._files.get(self._lang)
        self._view.set_file_label(
            os.path.basename(path) if path else "", path or "")

    def _keep_buffer(self):
        self._buffers[self._lang] = self._view.code()

    def persist(self):
        self._keep_buffer()
        if self._save_state:
            self._save_state(encode_state(self._lang, self._buffers))

    # ----- language and session -----

    def on_language_changed(self, lang):
        if lang == self._lang or lang not in syntax.LANGUAGES:
            return
        self._keep_buffer()
        self._lang = lang
        self._session = None
        self._view.set_language(lang)
        self._view.set_code(self._buffers.get(lang, ""))
        self._show_file()
        self.refresh_sessions()

    def refresh_sessions(self):
        """Read the active contexts of the language from the test process."""
        service = self._service()
        names = []
        if service is not None:
            try:
                names = list(service.sandbox_sessions(self._lang))
            except ETUMError:
                names = []
        if self._session not in names:
            self._session = None
        self._view.set_sessions([OWN_SESSION] + names,
                                self._session or OWN_SESSION)

    def on_session_changed(self, name):
        self._session = None if name == OWN_SESSION else name

    # ----- run -----

    def run(self):
        service = self._service()
        code = self._view.code()
        if service is None or self._running or not code.strip():
            return
        self.persist()
        target = _LABELS[self._lang]
        if self._session:
            target += f", context {self._session}"
        self._view.append_output(f"--- {target}\n", "info")
        try:
            service.sandbox_run(self._lang, code, self._session)
        except ETUMError as e:
            self._view.append_output(error_text(e) + "\n", "error")
            self.refresh_sessions()
            return
        self._running = True
        self._view.set_sandbox_state(enabled=True, running=True)

    def on_event(self, message):
        """Sandbox message of the status queue."""
        event = message.get("event")
        if event == "output":
            self._view.append_output(message.get("text", ""), "output")
        elif event == "finished":
            self._running = False
            if message.get("error") is not None:
                self._view.append_output(
                    str(message["error"]).rstrip() + "\n", "error")
            elif message.get("result") is not None:
                self._view.append_output(
                    repr(message["result"]) + "\n", "result")
            self._view.set_sandbox_state(
                enabled=self._service() is not None, running=False)

    def stop(self):
        service = self._service()
        if service is None or not self._running:
            return
        if self._session and not self._view.confirm(
                f"Stop kills the process of the context '{self._session}'. "
                "Its state is lost. Continue?"):
            return
        try:
            service.sandbox_stop()
        except ETUMError as e:
            self._view.append_output(error_text(e) + "\n", "error")

    def reset(self):
        service = self._service()
        if service is None or self._running:
            return
        if self._session and not self._view.confirm(
                f"Reset restarts the process of the context "
                f"'{self._session}'. The state left by the test items is "
                "lost. Continue?"):
            return
        try:
            service.sandbox_reset(self._lang, self._session)
        except ETUMError as e:
            self._view.append_output(error_text(e) + "\n", "error")
            return
        self._view.append_output("--- process restarted\n", "info")
        self.refresh_sessions()

    # ----- script files -----

    def is_modified(self):
        """The open file differs from the editor content."""
        if self._files.get(self._lang) is None:
            return False
        return self._view.code() != self._saved.get(self._lang, "")

    def _may_replace(self):
        return (not self.is_modified()) or self._view.confirm(
            "The script has unsaved changes. Discard them?")

    def test_scripts(self):
        """[(language, path)] of the script files used by the test."""
        service = self._service()
        if service is None:
            return []
        try:
            by_lang = service.sandbox_scripts()
        except ETUMError:
            return []
        return [(lang, path) for lang in syntax.LANGUAGES
                for path in by_lang.get(lang, [])]

    def open_file(self, path=None):
        """Load a script file in the editor. Without path, ask the view."""
        if not self._may_replace():
            return
        if path is None:
            current = self._files.get(self._lang)
            path = self._view.ask_open_path(
                os.path.dirname(current) if current else "")
            if not path:
                return
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except (OSError, UnicodeDecodeError) as e:
            self._view.append_output(f"Cannot open '{path}': {e}\n", "error")
            return
        lang = syntax.language_of(path) or self._lang
        if lang != self._lang:
            self._keep_buffer()
            self._lang = lang
            self._session = None
            self._view.set_language(lang)
            self.refresh_sessions()
        self._files[lang] = path
        self._saved[lang] = text
        self._buffers[lang] = text
        self._view.set_code(text)
        self._show_file()

    def close_file(self):
        """Detach the editor from its file, keeping the text."""
        self._files.pop(self._lang, None)
        self._saved.pop(self._lang, None)
        self._show_file()

    def _write(self, path):
        text = self._view.code()
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(text)
        except OSError as e:
            self._view.append_output(f"Cannot write '{path}': {e}\n", "error")
            return False
        self._files[self._lang] = path
        self._saved[self._lang] = text
        self._show_file()
        return True

    def save(self):
        path = self._files.get(self._lang)
        if path is None:
            return self.save_as()
        used = any(p == path for _, p in self.test_scripts())
        if used and not self._view.confirm(
                f"'{os.path.basename(path)}' is used by the test. "
                "Overwrite it?"):
            return False
        return self._write(path)

    def save_as(self):
        current = self._files.get(self._lang)
        ext = next(e for e, l in syntax.EXTENSIONS.items() if l == self._lang)
        path = self._view.ask_save_path(current or "", ext)
        if not path:
            return False
        if not os.path.splitext(path)[1]:
            path += ext
        return self._write(path)

    # ----- item of the tree -----

    def send_item(self, item_id):
        """Fill the editor with the script of a function item and its
        call. Returns True when the panel has something to show."""
        service = self._service()
        if service is None:
            return False
        try:
            call = service.sandbox_item_call(item_id)
        except ETUMError as e:
            self._view.append_output(error_text(e) + "\n", "error")
            return False
        if call.get("unresolved"):
            # The call cannot run: the editor is left as it is.
            names = ", ".join(f"$({n})" for n in call["unresolved"])
            self._view.append_output(
                f"Not sent, not defined yet: {names}. These variables are "
                "set while the test runs: pause the run on this item, then "
                "send it again.\n", "error")
            return True
        if not self._may_replace():
            return False
        self._keep_buffer()
        self._lang = call["lang"]
        self._files.pop(self._lang, None)
        self._saved.pop(self._lang, None)
        self._buffers[self._lang] = call["code"]
        self._view.set_language(self._lang)
        self._view.set_code(call["code"])
        self._show_file()
        self.refresh_sessions()
        if call.get("session"):
            self._session = call["session"]
            self.refresh_sessions()
        return True

    # ----- completion -----

    def complete(self, before_cursor):
        """Propose completions for the text before the cursor."""
        service = self._service()
        gd_start = syntax.gd_prefix(self._lang, before_cursor)
        if gd_start is not None:
            names = []
            if service is not None:
                try:
                    names = list(service.get_gd_vars())
                except ETUMError:
                    names = []
            self._view.show_completions(
                gd_start, syntax.merge_completions(gd_start, names))
            return
        prefix = syntax.completion_prefix(self._lang, before_cursor)
        if not prefix:
            self._view.show_completions("", [])
            return
        live = []
        if service is not None and not self._running:
            try:
                live = service.sandbox_complete(
                    self._lang, prefix, self._session)
            except Exception:  # noqa: BLE001
                live = []
        self._view.show_completions(prefix, syntax.merge_completions(
            prefix, syntax.static_words(self._lang), live))
