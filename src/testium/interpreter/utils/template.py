import os
from sys import exc_info
from jinja2 import Template
from jinja2.exceptions import TemplateSyntaxError, TemplateError, UndefinedError
from tempfile import TemporaryFile
from interpreter.utils.yaml_load import print_yaml
from interpreter.utils.tum_except import ETUMSyntaxError


def template_to_test(filename: str, params: list):
    """ Function which processes an eventual jinja2 template to a test file
    """
    # Temporary file created to receive the processed include
    # file
    tmpf = TemporaryFile('w+t')
    with open(filename, 'r') as f:
        try:
            j2_template = Template(f.read())
        except TemplateError as e:
            print_yaml(f, filename)
            type, value, tb = exc_info()
            msg = "Template error"
            if hasattr(value, 'lineno'):
                msg = msg + f" on line {value.lineno}: "
            else:
                msg += ": "
            raise ETUMSyntaxError(msg + str(e), filename)
    try:
        params["include_directory"] = os.path.dirname(os.path.abspath(filename))
        tmpf.write(j2_template.render(params))
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

    # return to begining of the temp file
    tmpf.seek(0, os.SEEK_SET)
    tmpf.root = os.path.dirname(filename)

    return tmpf