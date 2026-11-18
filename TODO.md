# TODO

Found while running the cam_ha reliability campaign (2026-11-06, testium 0.6.1).

- HTML export: a row whose log or data holds a control character (ESC, BEL)
  is dropped with "All strings must be XML compatible" (`report_export_html.py`,
  `add_row`). Sources: the terminal console's bash prompt (title `ESC ] 0 ; ... BEL`,
  bracketed paste `ESC [ ?2004h/l`) and the Zephyr shell cursor codes
  (`ESC [ 8D`, `ESC [ J`, colours). Strip ANSI sequences and the remaining
  C0 characters before `rh.text = ...` / `p.text = ...` so the row renders.
  Campaign-side workaround for the terminal part: `shell: /usr/bin/env TERM=dumb bash --norc`.

Found while reworking the cam_ha cycle campaign (2026-11-15, testium 0.6.2).

- `exec` has no dialect for a device shell (Zephyr shell: no `;`, no `printf`).
  `writeln` + `read_until "OK"` is the only way, and every command answers
  `OK`: an unread `OK` ends the next command too early, the campaign runs
  ahead of the board and the board drops characters. Wanted: a dialect that
  sends the marker as a second line through a command the user names
  (`marker_cmd: "sync {id}"`, expected `@SYNC:{id}@` at line start).
  Workaround: firmware command `sync <token>`, and a
  `writeln: sync sNN` / `read_until: "@SYNC:sNN@"` pair after every command.
- `read_until` matches text received before the action started. Wanted: a
  `flush` console action (the API has `flush()`), or `read_until` with
  `from: now`. Workaround: the same marker pair.
- Console log lines carry the time they were read by a step, not the time
  they arrived (`[18:21:32 ser]` on thirty seconds of board output). Wanted:
  the reception time, taken in the reader thread.

Found while building the validation suite (2026-11-18).

- The report sqlite is committed only in `open()` (schema + initial header)
  and `close()` (final header + all rows): every `addTest` INSERT runs in one
  long open transaction. After a crash (kill, power loss) the whole run is
  rolled back — a long campaign that dies in its last hours leaves an empty
  `tests` table — and an external process cannot read the file mid-run (the
  open write transaction blocks readers in rollback journal mode; the
  suite's cross-item checks had to parse the per-item JUnit instead).
  In-process consumers are unaffected (GUI and the built-in exporters use
  the live connection), and `_db_snapshot` (the `plugin`/`command`
  out-of-process exporters) already commits the open transaction mid-run —
  "nothing relies on rollback" — so the transaction has no semantic role.
  Wanted: commit after each `addTest` INSERT (inside the existing
  `self._lock`); the `close()` final header remains the completion marker
  (crashed run = rows present, final header absent). Priority: below the
  console points — hardening, not a bug blocking the campaign. Open
  question: enable WAL for file-backed reports so external readers are
  never blocked (cost: `-wal`/`-shm` sidecars, and a mid-run copy of the
  `.sqlite` alone is incomplete) or keep the default journal (the file is
  always a valid standalone DB; readers may rarely hit "database is locked"
  and should set a busy timeout).

---

## Analysis & proposals (code review, 2026-11-17)

### 1. HTML export — confirmed, and the scope is wider than stated

**Confirmed, now executed.** `report_export_html.py` `add_row` (L26-43):
lxml rejects C0 control characters on `.text` assignment and raises
`ValueError` ("All strings must be XML compatible: Unicode or ASCII, no NULL
bytes or control characters" — executed: identical message to the live-run
warning); the `except` prints a warning and the log section is lost *from the
failed line on* (verified: `CTRLLOG start` survives, `CTRLLOG title`/`end`
dropped). Additionally `trow` is created *before* the `try`, so a failure
mid-cell leaves a partial `<tr>` in the table. Note: lxml accepts DEL and C1
(`0x80-0x9F`) — only C0 (except `\t\n\r`) raises.

Scope is wider than the entry states:
- **Double-escape in the same function (now executed, not inferred):**
  `p.text = html.escape(l)` (L40) — lxml escapes `.text` at serialization, so
  `a < b` renders as `a &lt; b` in the browser (`html.escape` + `.text`
  serializes to `&amp;lt;`). 380 such traces across the 34 HTML files in
  `test/tmp/`. Fix: `p.text = sanitize(l)`, no `html.escape`.
- **`create_base` (L46-82) has no `try/except`:** one C0 in the report name
  (`-n`) or a header field aborts the whole export with an uncaught
  `ValueError` and no file written. Low probability, total loss.
- **JUnit export: NOT broken — correcting the 2026-11-17 claim.** `junit_xml`
  already sanitizes: its `clean_str` strips C0 (except `\t\n\r`) plus DEL
  before serialization. Executed: log `a\x1bb\x07c\td\ne` →
  `abc&#9;d&#10;e`, output reparses; the campaign's `py_func_PASS.junit` /
  `validation-source-py_func.xml` reparse with all log markers present.
  Nit only: C1 (`0x80-0x9F`) passes `junit_xml` through, so a C1-laden log
  yields XML that is not strictly XML 1.0 legal (expat-family parsers accept
  it anyway). No change needed.
- **json/txt exporters: unaffected** (json escapes C0 as `\uXXXX`; txt is raw).
- **The `log:` file log is already clean**: `LoggedConsole.read_thread`
  (`api/console.py` L706) filters through `_is_valid_character` (keeps
  `0x20-0x7E` + `\n\r\t`), so only the report/GUI paths carry the ANSI garbage.

Proposal (HTML exporter only — see the JUnit correction above):
- Module-level sanitizer in `report_export_html.py`:
  `re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\x80-\x9f]').sub('', s)`,
  applied to every text sink:
  - C0 except `\t\n\r`: what makes lxml raise (the crash);
  - DEL + C1: XML 1.0 legality + parity with `junit_xml` (which strips DEL);
    never crash lxml, but keep the output strictly valid XML 1.0.
- Apply in `add_row` to the 4 `<td>` cells, the log `<h3>` title and each log
  line (drop `html.escape` → fixes the double-escape); move the `trow`
  creation *inside* the `try` (no partial rows); keep the `except ValueError`
  as a last-resort guard. Apply in `create_base` to the report name
  (`<title>`, `h1`) and the header fields.
- End-to-end regression test already exists and is red: the `py_func`
  validation item emits `CTRLLOG start` / ESC-BEL-CSI lines / `CTRLLOG end`
  and `items/report.tum` asserts the three markers in `py_func_PASS.html`
  (fails today, will pass with this fix). Optional hardening: emit one line
  with a `<` (e.g. `CTRLLOG lt: a < b`) and assert the single-escaped form
  `a &lt; b` in the HTML to lock the double-escape fix.

Questions:
- Stray C0 characters: strip (silent) or replace with a visible placeholder
  (U+FFFD)? I'd strip — a lone `0x01` in a report has no display value, and
  silent strip is exactly what `junit_xml` already does for JUnit, so the HTML
  and JUnit reports of the same log stay consistent. (Stripping whole ANSI
  sequences — `ESC]0;…BEL` → nothing — would be cosmetically cleaner but
  diverges from the JUnit output and adds regex surface; not in this fix.)
  (For the *file* log, stripping already exists.)
- Phase 2 (optional, bigger behavior change): strip ANSI at console ingestion
  (e.g. `open: {ansi_strip: true}`) so the GUI log and the `cn_<name>` globals
  are clean too. Note this changes what `read_until`/`check` see, so it must
  stay opt-in. Worth doing at all, or is the report-side fix enough?

### 2. exec / Zephyr shell — confirmed, proposal fits the existing marker architecture

**Confirmed.** `api/console_sync.py`: `DIALECTS = ("sh", "cmd", "powershell")`;
all three `wrap_command` variants append the marker **on the same line** using
shell features (`;`+`printf`, `&`+`echo`, `;`+string concatenation) — none
works on the Zephyr shell (no `;`, no `printf`). The per-call unique marker
(`new_marker_id`, 12 hex chars) and the line-start anchor already exist and can
be reused unchanged.

Proposal (additive, mirrors the existing contract):
- `open` gains `dialect: custom` plus two templates, both expanding `{id}` per
  call (required when `dialect: custom`):
  - `marker_cmd: "sync {id}"` — sent as a **second line** after the command;
  - `marker: "@SYNC:{id}@"` — `re.escape`d, anchored at line start (same
    `(?:^|[\r\n])` anchor as `completion_regex`).
- `exec` with `custom`: `writeln(cmd)`; `writeln(marker_cmd_fmt)`;
  `read_until` with the anchored escaped marker; strip the marker line from the
  result. Result contract unchanged (`cn_<name>`, reported `data`).
- Docs + schema: `open` PARAMS docstrings, `console_test_item.rst`, and
  `schema/tum.json` regenerated (`testium schema > schema/tum.json` —
  `test/validation/schema_check.py` enforces the sync).

Caveats / questions:
- **Missing trailing newline**: if the command's last output line has no `\n`,
  the marker glues to it and the line-start anchor fails → timeout. The current
  workaround evidently lives with this; I'd *document* "the marker must arrive
  on its own line" (the firmware prints `@SYNC:id@\n`) rather than adding a
  `marker_anchor` knob. OK?
- The echoed `sync <id>` command line cannot false-match: the pattern is the
  `@…@` marker, not the command text (same guarantee the current dialects have).
- Should `dialect: custom` also be allowed on `terminal`/`ssh` consoles (harmless
  generalization) or restricted to the device protocols? I'd allow it anywhere
  — the dialect is a property of the shell on the far end, not of the transport.

### 3. read_until matching pre-buffered text — confirmed; I'd pick the `flush` action, not `from: now`

**Confirmed, now executed (2026-11-18).** Buffered transports run a reader thread that decouples arrival
from consumption — `SerialConsole` (bufferize, the default) and the
`LoggedConsole` variants feed `rx_queue`, `TermConsole` feeds `self.q`
(`enqueue_output`) — so the `read_until` loop drains whatever is already
buffered, and a stale `OK` from the previous command satisfies the next
`read_until "OK"` instantly.

The two options in the entry are **not** equivalent:
- **`flush` action — recommended.** Semantics: discard everything in the buffer
  *before the next command is written*. Usage: `flush` → `writeln cmd` →
  `read_until`. No race: bytes arriving after the flush are response data and
  are kept.
- **`read_until from: now` — race hazard.** It discards whatever is buffered at
  action start, i.e. it must be used *after* the write. Any response bytes that
  arrived in the gap between the write and the read start are thrown away — at
  115200 baud the board can already have sent its whole `OK` in that gap →
  guaranteed timeout. A `flush` action placed before the write has no such
  window.

**Regression tests (stage A + stage B) are in place; GREEN since the
action landed (full-suite runs of 2026-11-18).**
`test/validation/items/console/test.tum`, the `Console stale OK *` items:
dedicated terminal console, `writeln: echo OK` whose answer is left unread,
a settle, then the "second command" item: `flush`,
`writeln: echo STALE_SECOND_OUT; echo OK` +
`read_until: {expected: OK, timeout: 5}`, and a `check` asserting the
captured data contains `STALE_SECOND_OUT`. Stage A (action not yet
implemented, committed `046bc687`): the `read_until` step itself PASSed
(it matched the *stale* `OK`, with the wrong data) and the `check` was
the red item of the full suite — exactly the bug. Stage B (the `flush`
step, first step of the "second command" item, before the `writeln`): the
flush discards the stale answer, the `read_until` matches the new
command's own answer (captured data = `STALE_SECOND_OUT` + `OK`), and the
`check` is GREEN — the full-suite verdict now carries only the point-4 red
row. (While the action was missing it must not appear in any `.tum`: an
unknown action is a load-time `ETUMSyntaxError` that kills the whole run.)

Implementation notes for the `flush` action (verified against the code,
2026-11-18):
- **Every concrete console already drains its receive buffer in
  `read_nowait`** — the base `Console.read_nowait` is `pass` (console.py
  L117-118), but it is never the one that runs:
  - `TermConsole.read_nowait` (`api/termconsole.py` L136-153):
    `self.q.getAll()` on the `BytesStore` fed by the reader thread; the last
    incomplete line is pushed back. Complete drain — `TermConsole._push_back`
    also goes to `self.q`, so nothing hides in `self._pending`.
  - `SerialConsole.read_nowait` (`api/console.py` L612-629):
    `rx_queue.getAll()` when bufferize; `_pending_text()` +
    `port.read(in_waiting)` otherwise.
  - `LoggedConsole.read_nowait` (L754-765): `_pending_text()` + `rx_queue`
    drain.
  - `TelnetConsole` (L406-410): `_pending_text()` + `read_very_eager()`;
    `SshConsole` (`console_ssh.py` L574+): already-arrived data;
    `RawTCPConsole` (`raw_tcp_console.py` L72+): timeout-0 recv.
- **The one broken link: `SerialConsole.flush` is overridden to
  `self.port.flush()`** (L609-610) — the OS input buffer only, which does
  *not* touch `rx_queue` where the reader thread already parked the stale
  bytes. Every other transport inherits `Console.flush()` =
  `read_nowait(mute=True)`, which is correct. One-line fix: make
  `SerialConsole.flush` call `self.read_nowait(mute=True)` (optionally after
  `self.port.flush()`, to also clear the OS buffer).
- **The action itself is then trivial**: new `TestItemConsoleFlush`
  (modeled on `TestItemConsoleClose`, `test_item_console.py` L308-338):
  resolve `console_name`, `cons = tm.console(cname)`, call
  `cons.read_nowait(mute=True)` (or `cons.flush()` after the serial fix),
  `SUCCESS`; register `"flush"` in `TestItemConsole.ACTIONS` (L608-615).
  No caller of `Console.flush()` exists today (grep: the `.flush()` hits are
  all file/stdout flushes) — the action is its first user. `mute=True` by
  design: the discarded bytes are the stale noise, echoing them back to the
  stream would defeat the point.
- Docs + schema: `console_test_item.rst`, `testium schema > schema/tum.json`
  (`schema_check.py` enforces the sync).
- `flush` is also the right tool for the terminal-protocol ANSI noise in item
  1 (discard the prompt garbage before reading).

Question: should the action also flush the *write* side (`port.flushOutput`)?
I'd say no — testium writes are synchronous and there is no pending output;
keeping it input-only is simpler and matches the need.

### 4. Log line timestamps — confirmed; one design decision to make

**Confirmed, with a useful asymmetry.** The *file* log (`log:` parameter) already
carries the **reception** time — `LoggedConsole.read_thread` stamps the first
character of each line (`api/console.py` L711-713). Only the stream log
(`[HH:MM:SS name]` in the GUI log, the per-step report `log` column and the
HTML export) is stamped at **display** time, by `Console._emit_line` (L179-184)
at the moment `read_until`/`read_nowait` consumes the line. So the goal is to
make the stream log match the file log's existing contract.

Mechanics — the timestamp must travel with the data:
- Today the reader threads queue **raw bytes** (`rx_queue`), and line assembly
  happens in the display path (`Console._display` splits on `\n`). A chunk can
  hold many lines; a single `datetime.now()` per chunk is exactly today's bug
  (one burst drained = one stamp for thirty seconds of output).
- Sketch: reader threads queue `(timestamp, bytes)` items instead of bare bytes
  (the thread already sees every arrival — `SerialConsole.read_thread` L551-555,
  `LoggedConsole.read_thread` L695-703); the display path uses the timestamp of
  the chunk holding the line's **first character** (same rule as the file log).
  `BytesStore` (serial) and the `queue.Queue` (LoggedConsole) paths both need
  the tuple; `readchar`/`read_available`/`read_nowait`/`_pending` adjust with
  it. Non-threaded transports (telnet, rawtcp) have no reader thread: stamp at
  `read_available` — there arrival ≈ read, which is accurate to the poll
  interval.

Questions:
- Scope: stream log only, or also the `cn_<name>` data stored by `read_until`?
  I'd keep `cn_<name>` raw (stamps in data would pollute `check` comparisons).
  Confirm?
- Granularity: per-line first-character time (file-log parity, my default)
  or per-line last-character time (the time the line completed)? I'd take the
  first character — it matches the existing file log.
- `read_nowait`/`flush` display (L620-628, L762-764) and the telnet `open`
  login banner (L387-391) also stamp at display time — bring them to reception
  time as well, or leave them? (I'd bring them, for consistency.)

**Regression test (stage A) is in place and RED (full suite, 2026-11-18).**
`test/validation/items/console/test.tum`, the `Console timestamp *` items:
dedicated terminal console, a shell loop emits `tsline_1/2/3` two seconds
apart, the answers are left unread so they pile up in the console buffer
(a 6 s settle), then ONE `read_until tsline_3` drains them in a burst. The
cross-item check `Console log stamps keep the reception spacing`
(`items/report.tum`, helper `items/console/tscheck.py`) asserts
`tsline_3 - tsline_1 >= 3 s` on the `[HH:MM:SS name]` stamps of the drain
step's log: RED today (the three stamps collapse onto the drain time —
verified in the run: `19:11:39` on all three lines for output produced
at ~33/35/37), GREEN once the stream log stamps at reception time.
The check runs only for the `console` item (`condition` gate) and reads
the per-item `console_PASS.junit` (the report items export it right after
the console test, and `junit_xml` puts each step's full log in the
`testcase` `log` attribute). Two design constraints locked by this run:
- the campaign sqlite is **uncommitted mid-run** (commits only at
  `open()`/`close()`), so a mid-run check cannot read it — the per-step
  JUnit log is the source of truth; do not regress to the sqlite; the
  per-item `*.txt` is a status table without logs, not a log source either;
- the `Console timestamp *` console items themselves all PASS today — the
  RED signal lives only in the cross-item check, like the point-3 check.

### Cross-cutting

- Manual + schema for items 2 and 3 (new `open` parameters `marker_cmd` /
  `marker`, new `flush` action, optional `ansi_strip`): `console_test_item.rst`,
  PARAMS docstrings, `testium schema > schema/tum.json` (`schema_check.py`
  enforces), and the validation suite needs a `console` fixture per new action
  (`test/validation/items/console/test.tum`).
- Item 1 is independent and small; items 2-4 are console-side and could land
  as one "device shell ergonomics" change or three separate ones. My
  suggested order: **1** (bug fix, no behavior change) → **3** (flush, additive,
  unblocks the campaign) → **2** (custom dialect) → **4** (timestamps, the
  biggest refactor).
