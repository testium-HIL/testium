import api.testium as tm
from interpreter.utils.py_eval import eval_exec
from runtime.tum_except import ETUMRuntimeError


def escape_hint(error_text):
    """Remedy for the SyntaxError raised when a substituted Windows path
    puts \\U... sequences in a string literal."""
    if "unicodeescape" in error_text:
        return ('A substituted Windows path breaks the string: '
                'write it as r"$(var)".')
    return None


def evaluate(val, _warn_on_failure=False, **replacement_dict):
    """Evaluate *val* in the eval subprocess.

    _warn_on_failure is set only for real ``<| ... |>`` constructs: other
    callers (expected_result, process_result) evaluate speculatively and
    failing is their normal outcome.
    """
    v2 = val
    evaluated = False
    if isinstance(val, str):

        for key, replacement in replacement_dict.items():
            val = val.replace(f"$({key})", str(replacement))
        try:
            v2 = eval_exec(val)
        except Exception as e:
            # eval can crash; the value is kept as-is (some expressions
            # only become evaluable later in the run).
            if _warn_on_failure:
                from interpreter.utils.params import warn_once, \
                    unresolved_names
                # An unresolved $(...) in the expression is the root cause;
                # otherwise report the evaluation error itself.
                unres = unresolved_names(val)
                if unres:
                    detail = (f"'<| {val} |>' evaluation failed: unresolved "
                              + ", ".join(f"$({n})" for n in unres))
                else:
                    # ETUM errors already carry a full message; avoid nesting.
                    detail = (getattr(e, "_message", None)
                              or f"{type(e).__name__}: {e}")
                warn_once(("eval", val), f"{detail} — left as-is.",
                          debug_hint=escape_hint(str(e))
                          or "Fix the expression, or set the "
                             "variable before it is evaluated.")
            elif tm.debug_enabled():
                tm.print_debug(
                    f"Evaluation of '{val}' failed with message:\n  {e}")
            v2 = val
        evaluated = val != v2
    return evaluated, v2


def to_bool_strict(value, origin):
    """Single boolean contract: a real bool (or 0/1), or a <| |>
    expression producing one. Any other string raises with a message
    naming *origin* — evaluation is never implicit."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    raise ETUMRuntimeError(
        f"{origin}: expected a boolean or a <| |> expression producing "
        f"one, got {type(value).__name__}: {value!r}. Wrap an expression "
        f"with <| |>.")


def unwrap_expression(raw, origin):
    """Attribute contract for expression-valued attributes: the raw value
    must be one <| |> block. Returns the inner expression text."""
    if isinstance(raw, str):
        expr = raw.strip()
        if expr.startswith("<|") and expr.endswith("|>"):
            return expr[2:-2]
    raise ETUMRuntimeError(
        f"{origin} must be a <| |> expression, got: {raw!r}. "
        f"Wrap it with <| |>.")


def post_evaluate(post_eval, res):
    """Evaluate a result post-processing expression (inner text of the
    <| |> block); it must reference $(result)."""
    if (post_eval is None) or (post_eval == ""):
        return res
    if (not isinstance(post_eval, str)) or ("$(result)" not in post_eval):
        raise ETUMRuntimeError(
            f"'{post_eval}' must contain the '$(result)' "
            f"substitution keyword.")
    substituted = post_eval.replace("$(result)", str(res))
    is_evaluated, res = evaluate(post_eval, result=res)
    if not is_evaluated:
        raise ETUMRuntimeError(
            f"Result evaluation failed: '{post_eval}' "
            f"(after substitution: '{substituted}') is not a valid "
            f"expression."
        )
    return res
