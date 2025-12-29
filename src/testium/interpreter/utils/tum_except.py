import traceback
import textwrap


class ETUMError(Exception):
    def __init__(self, message: str, file: str):
        self._message = message
        self._file = file

    def str_lines(self):
        return [self._message, self._file]

    def __str__(self):
        return "\n".join(self.str_lines())


class ETUMRuntimeError(ETUMError):
    def __init__(self, message: str, file: str = ""):
        super().__init__(message, file)

    def str_lines(self):
        lines = ["TUM runtime error:"]
        if self._file != "":
            lines += [f"In \"{self._file}\""]
        lines += [f"{self._message}"]
        return lines


class ETUMFileError(ETUMError):
    def __init__(self, message, file: str = ""):
        super().__init__(message, file)

    def str_lines(self):
        lines = ["TUM I/O error:"]
        if self._file != "":
            lines += [f"In \"{self._file}\""]
        lines += [f"{self._message}"]
        return lines


class ETUMSyntaxError(ETUMError):
    def __init__(self, message: str, file: str = ""):
        super().__init__(message, file)

    def str_lines(self):
        lines = ["TUM file syntax error:"]
        if self._file != "":
            lines += [f"  In File \"{self._file}\""]
        lines += textwrap.indent(f"{self._message}", "   |").splitlines()
        return lines


class ETUMParamError(ETUMError):
    def __init__(self, message: str, param: str = "", item: str = "", item_name: str = "", file: str = ""):
        super().__init__(message, file)
        self._item_name=item_name
        self._item = item
        self._param = param

    def str_lines(self):
        lines = ["TUM Item parameter missing:"]
        if self._file != "":
            lines += [f"In \"{self._file}\""]
        lines += [f"Item of type {self._item} with name \"{self._item_name}\""]
        lines += [f"Concerning parameter \"{self._param}\""]
        lines += [f"{self._message}"]
        return lines


def print_exception(exc: ETUMError):
    if not isinstance(exc, ETUMError):
        print(traceback.format_exc(4))

    print("\n" + "*"*80)
    print(exc)
    print("*"*80)
