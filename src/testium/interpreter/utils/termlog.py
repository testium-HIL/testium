import colorama
import re

from colorama import Fore, Style

COLOR_DEFAULT = Fore.WHITE
COLOR_RESET = Fore.RESET + Style.RESET_ALL + COLOR_DEFAULT


def colored_string(string: str, inputs: list) -> None:
    """Function which calculate the coloring of strings with many layers.
    Overlap of layers and inner layers are managed.
    """
    cols = [COLOR_DEFAULT for i in range(len(string))]
    for input in inputs:
        for i in range(input[0][0], input[0][1]):
            cols[i] = input[1]

    # construction of the string
    s = ""
    ilast = 0
    last_col = COLOR_DEFAULT
    for i in range(len(string)):
        if last_col != cols[i]:
            s = s + string[ilast:i] + COLOR_RESET + cols[i]
            ilast = i
            last_col = cols[i]

    return s + string[ilast:] + COLOR_RESET


class TermLog:
    PASS =  ["PASS", "Success", "SUCCESS"]
    FAIL =  ["FAIL", "Fail", "fail", "Error", "ERROR", "error"]
    WARN =  ["Warning", "warning", "WARNING", "Warn", "WARN"]
    INFO =  ["INFO"]
    DEBUG = ["DEBUG"]
    BOOL =  ["False", "True", "false", "true", "FALSE", "TRUE"]

    def __init__(self, out) -> None:
        """Class used to color the stdout in batch and terminal mode."""
        colorama.init()
        self.out = out
        self.pats = []
        self.pats = self.pats + [
            [re.compile('(\\"[^\\"]+\\")'), Fore.LIGHTBLUE_EX + Style.BRIGHT],
            [re.compile("(\\'[^\\']+\\')"), Fore.LIGHTBLUE_EX + Style.BRIGHT],
            [re.compile("(<-----|----->) step"), Fore.BLUE],
            [
                re.compile(
                    r"([\d\.]+)",
                ),
                Fore.MAGENTA,
            ],
            [re.compile(r"(@@\d+@@)"), Fore.BLACK],
        ]
        for word in self.BOOL:
            self.pats.append([re.compile("({})".format(word)), Fore.MAGENTA])
        for word in self.WARN:
            self.pats.append([re.compile("({})".format(word)), Fore.YELLOW])
        for word in self.INFO:
            self.pats.append([re.compile("({})".format(word)), Style.BRIGHT])
        for word in self.DEBUG:
            self.pats.append([re.compile("({})".format(word)), Fore.BLUE + Style.BRIGHT])
        for word in self.PASS:
            self.pats.append(
                [re.compile("({})".format(word)), Fore.GREEN + Style.BRIGHT]
            )
        for word in self.FAIL:
            self.pats.append([re.compile("({})".format(word)), Fore.RED + Style.BRIGHT])
        self.residue = ""

    def find_pats(self, line):
        spans = []
        for p in self.pats:
            it = p[0].finditer(line)
            for m in it:
                if m:
                    spans.append([m.span(), p[1]])
        return spans

    def write(self, s: str) -> None:
        if s == "":
            return
        s = self.residue + s
        self.residue = ""
        if s[-1:] != "\n":
            pos = s.rfind("\n")
            if pos >= 0:
                self.residue = s[pos:]
                s = s[:pos]
            else:
                # only one line
                self.out.write(colored_string(s, self.find_pats(s)))
                return
        # multiline case
        for l in s.splitlines():
            self.out.write(colored_string(l, self.find_pats(l)) + "\n")

    def flush(self):
        if self.residue != "":
            self.out.write(self.residue)
            self.residue = ""
        self.out.flush()
