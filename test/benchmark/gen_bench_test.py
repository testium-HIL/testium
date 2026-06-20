#!/usr/bin/env python3
"""Generate synthetic ``.tum`` test trees to benchmark *load* time.

The generated trees are deliberately cheap to *build* (only ``let`` leaves and
``group`` containers — no subprocess, no runtime side effect) so the load
benchmark measures the parse / template / tree-build pipeline and nothing else.

Profiles, each targeting a specific cost in the loader:

  flat      one main file, N inline ``let`` steps, no include, no jinja.
            Baseline: YAML parse of a big document + linear object build.

  includes  main ``!include``s N *distinct* sub-files (a few steps each).
            Stresses the per-include template+YAML+tempfile round-trip and the
            ``sequence`` splice in test_set.load_test_recursively.

  repeat    main ``!include``s the *same* parametrised leaf file N times.
            Stresses jinja *recompilation*: the compiled template is identical
            every time, only the render params (idx) differ -> the case a
            template cache collapses.

  jinja     one main file whose ``{% for %}`` loop emits N steps.
            Stresses a single large jinja render + a single large YAML parse.

  deep      nested includes, depth N (main -> d0 -> d1 -> ...).
            Stresses include recursion and per-level template+YAML.

  mix       a realistic blend: groups, a jinja loop, distinct includes and a
            repeated parametrised include.

Usage:
    gen_bench_test.py --profile repeat --size 1000 --out cases/repeat_1000
    -> writes <out>/main.tum (+ includes, + param.yaml) and prints the path.
"""
import argparse
import os
import shutil


def _let(indent, i, name=None):
    name = name if name is not None else f"s{i}"
    pad = " " * indent
    return (
        f"{pad}- let:\n"
        f"{pad}    name: {name}\n"
        f"{pad}    values:\n"
        f"{pad}        - k{i}: {i}\n"
    )


def gen_flat(out, n):
    body = "".join(_let(8, i) for i in range(n))
    main = f"main:\n    name: bench flat {n}\n    steps:\n{body}"
    _write(out, "main.tum", main)


def gen_includes(out, n):
    steps = "".join(f"        - !include inc_{i}.tum\n" for i in range(n))
    main = f"main:\n    name: bench includes {n}\n    steps:\n{steps}"
    _write(out, "main.tum", main)
    for i in range(n):
        # each include is a YAML *sequence* (list of steps)
        seq = "".join(_let(0, i * 3 + j, name=f"inc{i}_{j}") for j in range(3))
        _write(out, f"inc_{i}.tum", seq)


def gen_repeat(out, n):
    steps = "".join(
        f"        - !include {{file: leaf.tum, idx: {i}}}\n" for i in range(n)
    )
    main = f"main:\n    name: bench repeat {n}\n    steps:\n{steps}"
    _write(out, "main.tum", main)
    leaf = (
        "- let:\n"
        "    name: leaf_{{ idx }}\n"
        "    values:\n"
        "        - leaf_{{ idx }}: {{ idx }}\n"
    )
    _write(out, "leaf.tum", leaf)


def gen_jinja(out, n):
    main = (
        f"main:\n    name: bench jinja {n}\n    steps:\n"
        "{% for i in range(" + str(n) + ") %}\n"
        "        - let:\n"
        "            name: j{{ i }}\n"
        "            values:\n"
        "                - k{{ i }}: {{ i }}\n"
        "{% endfor %}\n"
    )
    _write(out, "main.tum", main)


def gen_deep(out, n):
    main = (
        f"main:\n    name: bench deep {n}\n    steps:\n"
        "        - let:\n            name: top\n            values:\n                - a: 0\n"
        "        - !include d_0.tum\n"
    )
    _write(out, "main.tum", main)
    for i in range(n):
        seq = _let(0, i, name=f"d{i}")
        if i < n - 1:
            seq += f"- !include d_{i + 1}.tum\n"
        _write(out, f"d_{i}.tum", seq)


def gen_mix(out, n):
    # n groups, each: 2 inline lets, one distinct include, one repeated include,
    # plus a small jinja loop. Roughly ~6*n steps.
    per = max(1, n)
    parts = [f"main:\n    name: bench mix {n}\n    steps:\n"]
    for g in range(per):
        parts.append(
            f"        - group:\n"
            f"            name: grp{g}\n"
            f"            steps:\n"
        )
        parts.append(_let(16, g * 2, name=f"g{g}_a"))
        parts.append(_let(16, g * 2 + 1, name=f"g{g}_b"))
        parts.append(f"                - !include inc_{g}.tum\n")
        parts.append(f"                - !include {{file: leaf.tum, idx: {g}}}\n")
        parts.append(
            "{% for i in range(3) %}\n"
            f"                - let:\n"
            f"                    name: g{g}_j{{{{ i }}}}\n"
            f"                    values:\n"
            f"                        - g{g}_k{{{{ i }}}}: {{{{ i }}}}\n"
            "{% endfor %}\n"
        )
    _write(out, "main.tum", "".join(parts))
    for g in range(per):
        _write(out, f"inc_{g}.tum", _let(0, g, name=f"mixinc{g}"))
    _write(
        out,
        "leaf.tum",
        "- let:\n    name: mixleaf_{{ idx }}\n    values:\n        - mixleaf_{{ idx }}: {{ idx }}\n",
    )


PROFILES = {
    "flat": gen_flat,
    "includes": gen_includes,
    "repeat": gen_repeat,
    "jinja": gen_jinja,
    "deep": gen_deep,
    "mix": gen_mix,
}


def _write(out, name, content):
    with open(os.path.join(out, name), "w") as f:
        f.write(content)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", required=True, choices=sorted(PROFILES))
    ap.add_argument("--size", type=int, default=1000,
                    help="profile-specific count (steps / includes / depth)")
    ap.add_argument("--out", required=True, help="output directory (recreated)")
    args = ap.parse_args()

    out = os.path.abspath(args.out)
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)

    # minimal config file so the loader does not emit "no param file" noise
    _write(out, "param.yaml", "bench_dummy: 1\n")

    PROFILES[args.profile](out, args.size)
    print(os.path.join(out, "main.tum"))


if __name__ == "__main__":
    main()
