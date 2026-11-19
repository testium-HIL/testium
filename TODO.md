# TODO

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
