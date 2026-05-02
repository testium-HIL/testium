import yaml
import os.path
import api.testium as tm
from interpreter.utils.params import expanse
from runtime.tum_except import ETUMFileError
from interpreter.utils.template import template_to_test
from copy import copy
from interpreter.utils.globdict import global_dict
from interpreter.utils.yaml_load import yaml_load


class TUMLoaderNoIncludes(yaml.Loader):

    def __init__(self, stream):

        if hasattr(stream, "root"):
            self._root = stream.root
        else:
            self._root = os.path.split(stream.name)[0]

        super().__init__(stream)

    def include_none(self, node):
        return None


class TUMLoaderRawIncludes(TUMLoaderNoIncludes):
    """Class used to preload the test files.
    When this class is used, the files are not included
    recursively."""

    def _include(self, node, is_raw: bool = False):
        data = None
        try:
            # Check if templating used on the include file
            # {file: <filename>, ...} dictionnary required.
            p = self.construct_mapping(node, deep=True)
            filename = expanse(p["file"])
            p.pop("file")
        except:
            # Only file parameter
            p = self.construct_scalar(node)
            filename = expanse(p)

        if not os.path.isabs(filename):
            filename = os.path.join(self._root, filename)

        if not os.path.isfile(filename):
            raise ETUMFileError('File "{}" not found'.format(filename))

        # Copy of the global dict content to be passed as parameter
        gd_copy = copy(global_dict)

        if not isinstance(p, str):
            # Case where there are template explicit params
            for k, v in p.items():
                gd_copy.update({k: expanse(v)})

        # Processes eventual jinja2 template
        tmpf = template_to_test(filename, gd_copy)

        # load the yaml test file (with potential includes)
        data = yaml_load(tmpf, filename, TUMLoader)

        if not is_raw:
            # This part allows to define include with no "sequence: " before
            if (
                isinstance(data, dict)
                and (len(data) == 1)
                and "sequence" in data.keys()
            ):
                data = {"sequence": {"filename": filename, "data": data["sequence"]}}
            else:
                data = {"sequence": {"filename": filename, "data": data}}

        return data

    def raw_include(self, node):
        return self._include(node, True)


class TUMLoader(TUMLoaderRawIncludes):
    """Class used to include sub-sequences recursively.
    A jinja2 based templating of included files is supported."""

    def include(self, node):
        return self._include(node, False)


TUMLoaderNoIncludes.add_constructor("!include", TUMLoaderRawIncludes.include_none)
TUMLoaderNoIncludes.add_constructor("!raw_include", TUMLoaderRawIncludes.include_none)
TUMLoaderRawIncludes.add_constructor("!include", TUMLoaderRawIncludes.include_none)
TUMLoaderRawIncludes.add_constructor("!raw_include", TUMLoaderRawIncludes.raw_include)
TUMLoader.add_constructor("!include", TUMLoader.include)
TUMLoader.add_constructor("!raw_include", TUMLoader.raw_include)
