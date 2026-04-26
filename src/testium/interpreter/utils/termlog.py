import os
import re
import sys

import colorama
from colorama import Fore, Style


def _detect_dark_background() -> bool:
    """Detect whether the terminal has a dark background.

    Tries the following methods in order:
    1. ``COLORFGBG`` environment variable (Konsole, rxvt, …)
    2. OSC 11 terminal query — reads the actual background colour from the
       terminal emulator (xterm, VTE, kitty, WezTerm, …)
    3. ``darkdetect`` module — OS-level dark-mode preference (optional dep)

    Returns ``True`` for a dark background (default assumption).
    """
    # --- Method 1: COLORFGBG ---
    colorfgbg = os.environ.get("COLORFGBG", "")
    if colorfgbg:
        try:
            bg = int(colorfgbg.split(";")[-1])
            # 0-6: dark palette entries, 7-15: light palette entries
            return bg < 7
        except (ValueError, IndexError):
            pass

    # --- Method 2: OSC 11 terminal query ---
    if sys.stdin.isatty() and sys.stdout.isatty():
        try:
            import select
            import termios
            import tty

            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                # Query background colour
                sys.stdout.write("\033]11;?\007")
                sys.stdout.flush()
                ready, _, _ = select.select([sys.stdin], [], [], 0.2)
                if ready:
                    response = ""
                    while True:
                        r2, _, _ = select.select([sys.stdin], [], [], 0.05)
                        if not r2:
                            break
                        chunk = os.read(fd, 64).decode("latin-1", errors="replace")
                        response += chunk
                        # Terminal answers with ESC]11;rgb:RR../GG../BB..<BEL|ST>
                        if response.endswith("\007") or response.endswith("\033\\"):
                            break
                    m = re.search(
                        r"rgb:([0-9a-fA-F]+)/([0-9a-fA-F]+)/([0-9a-fA-F]+)",
                        response,
                    )
                    if m:
                        # Components are 8- or 16-bit hex; normalise to 0-255
                        def _norm(h: str) -> float:
                            return int(h[:2], 16)

                        r_v = _norm(m.group(1))
                        g_v = _norm(m.group(2))
                        b_v = _norm(m.group(3))
                        luminance = 0.299 * r_v + 0.587 * g_v + 0.114 * b_v
                        return luminance < 128
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
        except Exception:
            pass

    # Default: assume dark terminal
    return True


def _colored_string(string: str, inputs: list, color_default: str, color_reset: str) -> str:
    """Return *string* with ANSI colour codes applied according to *inputs*.

    *inputs* is a list of ``[[start, end], color_code]`` pairs.
    Overlapping layers are handled: the last listed colour wins.
    """
    cols = [color_default for _ in range(len(string))]
    for span, color in inputs:
        for i in range(span[0], span[1]):
            cols[i] = color

    s = ""
    ilast = 0
    last_col = color_default
    for i in range(len(string)):
        if last_col != cols[i]:
            s = s + string[ilast:i] + color_reset + cols[i]
            ilast = i
            last_col = cols[i]

    return s + string[ilast:] + color_reset


class TermLog:
    PASS =  ["PASS", "Success", "SUCCESS"]
    FAIL =  ["FAIL", "Fail", "fail", "Error", "ERROR", "error"]
    WARN =  ["Warning", "warning", "WARNING", "Warn", "WARN"]
    INFO =  ["INFO"]
    DEBUG = ["DEBUG"]
    BOOL =  ["False", "True", "false", "true", "FALSE", "TRUE"]

    def __init__(self, out, dark_bg: bool = None) -> None:
        """Class used to colour the stdout in batch and terminal mode.

        :param out: Underlying output stream.
        :param dark_bg: ``True`` for dark background, ``False`` for light.
                        ``None`` (default) triggers auto-detection.
        """
        colorama.init()
        self.out = out
        self.residue = ""

        if dark_bg is None:
            dark_bg = _detect_dark_background()

        if dark_bg:
            color_default = Fore.WHITE
            color_string  = Fore.LIGHTBLUE_EX + Style.BRIGHT
            color_number  = Fore.MAGENTA
            color_bool    = Fore.MAGENTA
            color_step    = Fore.BLUE
            color_marker  = Fore.BLACK
            color_warn    = Fore.YELLOW
            color_info    = Style.BRIGHT
            color_debug   = Fore.BLUE + Style.BRIGHT
            color_pass    = Fore.GREEN + Style.BRIGHT
            color_fail    = Fore.RED + Style.BRIGHT
        else:
            color_default = Fore.RESET
            color_string  = Fore.BLUE
            color_number  = Fore.MAGENTA
            color_bool    = Fore.MAGENTA
            color_step    = Fore.BLUE
            color_marker  = Fore.RESET
            color_warn    = Fore.YELLOW + Style.BRIGHT
            color_info    = Fore.CYAN
            color_debug   = Fore.BLUE
            color_pass    = Fore.GREEN
            color_fail    = Fore.RED + Style.BRIGHT

        self._color_default = color_default
        self._color_reset   = Fore.RESET + Style.RESET_ALL + color_default

        self.pats = [
            [re.compile(r'("(?:[^"]+)")'),   color_string],
            [re.compile(r"('(?:[^']+)')"),   color_string],
            [re.compile(r"(<-----|----->) step"), color_step],
            [re.compile(r"([\d\.]+)"),        color_number],
            [re.compile(r"(@@\d+@@)"),        color_marker],
        ]
        for word in self.BOOL:
            self.pats.append([re.compile(r"({})".format(word)), color_bool])
        for word in self.WARN:
            self.pats.append([re.compile(r"({})".format(word)), color_warn])
        for word in self.INFO:
            self.pats.append([re.compile(r"({})".format(word)), color_info])
        for word in self.DEBUG:
            self.pats.append([re.compile(r"({})".format(word)), color_debug])
        for word in self.PASS:
            self.pats.append([re.compile(r"({})".format(word)), color_pass])
        for word in self.FAIL:
            self.pats.append([re.compile(r"({})".format(word)), color_fail])

    def find_pats(self, line):
        spans = []
        for p, color in self.pats:
            for m in p.finditer(line):
                if m:
                    spans.append([m.span(), color])
        return spans

    def write(self, s: str) -> None:
        if s == "":
            return
        s = self.residue + s
        self.residue = ""
        if s[-1:] != "\n":
            pos = s.rfind("\n")
            if pos >= 0:
                self.residue = s[pos + 1:]
                s = s[:pos + 1]
            else:
                # single incomplete line — output immediately
                self.out.write(_colored_string(s, self.find_pats(s),
                                               self._color_default, self._color_reset))
                return
        # one or more complete lines
        for line in s.splitlines():
            self.out.write(
                _colored_string(line, self.find_pats(line),
                                self._color_default, self._color_reset) + "\n"
            )

    def flush(self):
        if self.residue != "":
            self.out.write(self.residue)
            self.residue = ""
        self.out.flush()
