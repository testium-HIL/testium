import api.testium as tm
from interpreter.utils.py_eval import eval_exec
from runtime.tum_except import ETUMSyntaxError, ETUMRuntimeError


def evaluate(val, **replacement_dict):
    v2 = val
    evaluated = False
    if isinstance(val, str):

        for key, replacement in replacement_dict.items():
            val = val.replace(f"$({key})", str(replacement))
        try:
            v2 = eval_exec(val)
        except Exception as e:
            # eval can crash
            if tm.debug_enabled():
                s = f"Evaluation of '{val}' failed with message:\n  " + str(e)
                tm.print_debug(s)
            v2 = val
        evaluated = val != v2
    return evaluated, v2


def eval_to_boolean(c):
    if isinstance(c, bool):
        condition = c
    elif isinstance(c, (str, bytes)):
        if c.lower() in [
            "true",
            "t",
            "y",
            "yes",
            "ok",
        ]:
            condition = True
        elif c.lower() in [
            "f",
            "n",
            "nok",
            "ko",
            "false",
            "no",
        ]:
            condition = False
        else:
            try:
                cond = eval_exec(c)
                condition = eval_to_boolean(cond)
            except Exception as e:
                print("eval with c: {}".format(c))
                raise e
    elif type(c) is int:
        condition = c > 0
    else:
        raise ETUMSyntaxError(
            f"Condition must evaluate to a string, int or bool, "
            f"got {type(c).__name__}: {c!r}.")
    return condition


def post_evaluate(post_eval, res):
    """This function is evaluating the result of a test,
    therefore it may include a $(result) parameter.
    """
    if (not post_eval is None) and (post_eval != ""):
        if (not isinstance(post_eval, str)) or (not ("$(result)" in post_eval)):
            raise ETUMRuntimeError(
                f"'eval' ({post_eval}) must be a string and have the '$(result)' substitution keyword."
            )

        substituted = post_eval.replace("$(result)", str(res))
        is_evaluated, res = evaluate(post_eval, result=res)
        if not is_evaluated:
            raise ETUMRuntimeError(
                f"Result evaluation failed: '{post_eval}' "
                f"(after substitution: '{substituted}') is not a valid "
                f"expression."
            )
    return res
