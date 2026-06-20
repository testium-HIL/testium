import io
import os
from sys import exc_info
from jinja2 import Environment
from jinja2.exceptions import TemplateSyntaxError, TemplateError, UndefinedError
from interpreter.utils.yaml_load import print_yaml
from runtime.tum_except import ETUMSyntaxError


# One Environment reused for every render (default settings, i.e. identical
# behaviour to jinja2.Template), plus a compiled-template cache so a file that
# is included many times — or a test that is reloaded — is compiled only once.
# Jinja compilation is the expensive step; render (variable substitution) stays
# per-call. Cache is keyed on path + mtime + size so an edited file recompiles.
_ENV = Environment()
_template_cache = {}  # abspath -> (mtime_ns, size, compiled_template)


class _RenderedStream(io.StringIO):
    """A rendered template kept in memory.

    Carries ``root`` (and ``name``) so the YAML loader resolves ``!include``
    paths exactly as it did from the on-disk temp file this replaces — without
    the write + seek + read round-trip (one temp file per included file). That
    round-trip is pure overhead, and especially costly on slow storage.
    """


def _compiled_template(filename: str):
    """Return the compiled jinja template for *filename*, reusing the cached
    one when the file is unchanged (path + mtime + size)."""
    key = os.path.abspath(filename)
    try:
        st = os.stat(filename)
    except OSError:
        st = None
    if st is not None:
        cached = _template_cache.get(key)
        if (cached is not None
                and cached[0] == st.st_mtime_ns
                and cached[1] == st.st_size):
            return cached[2]
    with open(filename, "r") as f:
        source = f.read()
    template = _ENV.from_string(source)  # compile (may raise TemplateSyntaxError)
    if st is not None:
        _template_cache[key] = (st.st_mtime_ns, st.st_size, template)
    return template


def template_to_test(filename: str, params: list):
    """ Function which processes an eventual jinja2 template to a test file
    """
    # Compile (cached) — a syntax error in the template surfaces here.
    try:
        j2_template = _compiled_template(filename)
    except TemplateError as e:
        with open(filename, "r") as f:
            print_yaml(f, filename)
        type, value, tb = exc_info()
        msg = "Template error"
        if hasattr(value, 'lineno'):
            msg = msg + f" on line {value.lineno}: "
        else:
            msg += ": "
        raise ETUMSyntaxError(msg + str(e), filename)

    # Render into memory (no temp file).
    try:
        params["include_directory"] = os.path.dirname(os.path.abspath(filename))
        rendered = j2_template.render(params)
    except TemplateSyntaxError as e:
        raise ETUMSyntaxError(f"""Template loading of file '{filename}' with following parameters '{str(params)}'
Syntax error in template: {e.message}""")
    except UndefinedError as e:
        raise ETUMSyntaxError(f"""Template loading of file '{filename}' with following parameters '{str(params)}'
Undefined variable error: {e.message}""")
    except TemplateError as e:
        raise ETUMSyntaxError(f"""Template loading of file '{filename}' with following parameters '{str(params)}'
Template rendering error: {e.message}""")
    except Exception as e:
    # Catch any other unexpected errors
        raise ETUMSyntaxError(f"""Template loading of file '{filename}' with following parameters '{str(params)}'
Unexpected error: {str(e)}""")

    stream = _RenderedStream(rendered)
    stream.root = os.path.dirname(filename)
    stream.name = filename
    return stream
