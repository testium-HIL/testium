# Contributing to testium

Thank you for your interest in contributing to testium.

## License of contributions

testium is licensed under the **European Union Public Licence v. 1.2 (EUPL-1.2)** —
see the [LICENSE](LICENSE) file at the repository root.

By submitting a contribution to this project (pull request, patch, issue
attachment, or any other form of code, documentation or media), you agree
that your contribution is licensed to the project and to the public under the
**same EUPL-1.2** terms (or any later version of the EUPL approved by the
European Commission), and you certify that:

- you are the author of the contribution, or you have the right to submit it
  under the EUPL-1.2;
- to the best of your knowledge, the contribution does not infringe any
  third-party intellectual-property rights;
- the contribution may be redistributed by the project under the EUPL-1.2 and
  any compatible licence listed in the EUPL-1.2 Appendix.

This is the **inbound = outbound** rule: contributions come in under the same
licence the project ships under.

You retain copyright on your contribution. The project does **not** ask you
to sign a CLA or assign your copyright.

## SPDX header in new source files

When creating a new source file, please include the following header at the
top of the file (adjust the comment marker to the file's language):

```python
# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) <year> <your name>
```

For existing files, keep the header that is already there.

## How to contribute

1. Open an issue describing the change you want to make (bug, feature, doc).
2. Fork the repository, create a topic branch.
3. Commit with a clear message (one logical change per commit).
4. Make sure the validation suite still passes:
   ```
   ./run.sh -b -l mon_log.log -- test/validation/main.tum
   ```
5. Open a pull request against `main`.

## Coding conventions

- Python ≥ 3.11
- Follow existing style in the file you are modifying
- Add or update tests in `test/validation/` for new test items or behaviours
- Update `CLAUDE.md` and the Sphinx manual for user-visible changes

## Reporting security issues

Please do **not** report security vulnerabilities through public GitHub
issues. Instead, send an email to the project maintainer directly.

## Questions

Open a GitHub Discussion or an issue tagged `question`.
