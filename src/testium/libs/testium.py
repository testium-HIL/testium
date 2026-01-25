import os
import platform
import sys
import textwrap
from time import monotonic
import interpreter.utils.globdict as globdict
from interpreter.utils.tum_except import (ETUMSyntaxError)

###############################################################################
# Console helper functions


def add_console(console):
    ''' Function which adds a ``Console`` class instance to *testium*

    :param console: The ``Console`` instance.
    :type console: ``libs.console.Console`` or child class instance
    :return: No returned value

    '''
    console_instances = globdict.gd('console_instances', [])
    console_instances.append(console)
    globdict.setgd('console_instances', console_instances)


def remove_console(name):
    ''' Function which removes a ``Console`` class instance from *testium*

    :param name: The name of the ``Console`` object to be removed.
    :type name: str
    :return: No returned value
    '''
    console_instances = globdict.gd('console_instances', [])
    cons = None
    for c in console_instances:
        if c.name == name:
            cons = c
            break
    if cons is not None:
        console_instances.remove(cons)
    globdict.setgd('console_instances', console_instances)


def console(name):
    """
    Function which removes a ``Console`` instance from *testium*

    :param name: The name of the ``Console`` instance.
    :type name: str
    :return: The ``Console`` or child class object
    :rtype: ``libs.console.Console`` or child class instance
    """
    cons = None
    for c in globdict.gd('console_instances', []):
        if c.name == name:
            cons = c
            break
    return cons

###############################################################################
# Plot helper functions


def add_plot(plot: object) -> None:
    ''' Function which adds a ``RuntimePlot`` class instance to *testium*

    :param plot: The ``RuntimePlot`` instance.
    :type plot: ``libs.runtime_plot.RuntimePlot`` or child class instance
    :return: No returned value

    '''
    plot_instances = globdict.gd('plot_instances', [])
    plot_instances.append(plot)
    globdict.setgd('plot_instances', plot_instances)


def remove_plot(name: str) -> None:
    ''' Function which removes a ``RuntimePlot`` class instance from *testium*

    :param name: The name of the ``RuntimePlot`` object to be removed.
    :type name: str
    :return: No returned value
    '''
    plot_instances = globdict.gd('plot_instances', [])
    plot = None
    for g in plot_instances:
        if g.name == name:
            plot = g
            break
    if plot is not None:
        plot_instances.remove(plot)
    globdict.setgd('plot_instances', plot_instances)


def plot(name: str) -> object:
    """
    Function which removes a ``RuntimePlot`` instance from *testium*

    :param name: The name of the ``RuntimePlot`` instance.
    :type name: str
    :return: The ``RuntimePlot`` or child class object
    :rtype: ``libs.runtime_plot.RuntimePlot`` or child class instance
    """
    plot = None
    for g in globdict.gd('plot_instances', []):
        if g.name == name:
            plot = g
            break
    return plot


def add_plot_values(name: str, values: dict) -> None:
    """
    Function which add values in a runing plot.

    The ``values`` param is the dictionnary of points to add to the plot.
    Each of its keys correspond to a plot line variable name.

    :param name: The name of the ``RuntimePlot`` instance.
    :type name: str
    :param values: a dictionnary of numbers which keys are plot line names
    :rtype: dict
    """
    p = plot(name)
    if p is None:
        raise ETUMSyntaxError('plot with name "{}" was not found'.format(name))
    p.add(values)


def last_plot_value(name: str) -> dict:
    """
    Function which returns the last values acquired in a runing plot.

    :param name: The name of the ``RuntimePlot`` instance.
    :type name: str
    :return: a dictionnary of numbers which keys are plot line names
    :rtype: dict
    """
    p = plot(name)
    if p is None:
        raise ETUMSyntaxError('plot with name "{}" was not found'.format(name))
    return p.last_values()


###############################################################################
# class FunctionItem():
#     """Class allowing extended capabilities of function."""
#     module_count = 0

#     def __init__(self):
#         self._reported_value = {}

#     def reportValue(self, key, value):
#         self._reported_value[key] = value

#     def reportedValues(self):
#         return self._reported_value

#     def exec(self):
#         pass


def get_main_dir():
    return os.path.abspath(os.path.dirname(sys.argv[0]))


def init_timestamp():
    globdict.setgd('test_items_tinit', monotonic())


def timestamp():
    """*testium* timestamp value.

    The ``timestamp`` is started at the beginning of the test, and it is monotonic:
    it is guaranteed that it will always increase, even if the PC time is changed.

    :return: *testium* timestamp in 10th of milliseconds.
    :rtype: float
    """
    return int((monotonic()-globdict.gd('test_items_tinit'))*10000)


def timestamp_as_sec(val=None):
    """*testium* timestamp value.

    If the argument ``val`` is provided, this function converts the timestamp in seconds.

    If ``val`` is not provided, it returns *testium* timestamp.
    The ``timestamp`` is started at the beginning of the test, and it is monotonic:
    it is guaranteed that it will always increase, even if the PC time is changed.

    :param val: Value to be converted. If not provided, the *testium* timestamp is returned.
    :type val: float
    :return: Timestamp returned as seconds.
    :rtype: float
    """
    if val is not None:
        return val/10000.0
    else:
        return monotonic()-globdict.gd('test_items_tinit')


def OS():
    """OS on which *testium* is running.

    :return: "Linux" or "Windows"
    :rtype: str
    """
    return platform.system()


def sys_encoding():
    if OS() == "Windows":
        enc = "oem"
    else:
        enc = "utf-8"
    return enc


def line_number(phrase, filename):
    with open(filename, 'r') as f:
        for (i, line) in enumerate(f):
            if phrase in line:
                return i
    return -1


def cleanup_instances(instances):
    """Cleanup remaining instances of plot and consoles.

    Must be called after a test is finished, to ensure everything's clean.

    :return: nothing returned
    """
    inst = globdict.gd(instances + '_instances', None)
    if inst is not None:
        for i in inst:
            print('closing {} {}'.format(instances, i.name))
            i.close()
        # all element of the list shall be closed now, we can empty the list
        globdict.delgd(instances + '_instances')


setgd = globdict.setgd
delgd = globdict.delgd
gd = globdict.gd

# Keep backward compatibility
addConsole = add_console
removeConsole = remove_console


###############################################################################
def debug_enabled():
    ''' Function which checks is debug mode is activated.

    :return: bool
    '''
    return gd("test_debug", False)


def enable_debug(enabled=True):
    ''' Function which enables the debug mode.

    :param enabled: Set debug mode active if ``True``.

    :return: No returned value
    '''
    setgd("test_debug", enabled)


def _custom_print(pref: str, *vargs, lf_first: bool = False):
    to_print = ""
    for varg in vargs:
        to_print += f"{varg}"
    if lf_first:
        print("\n")
    print(textwrap.indent(to_print, pref))


def print_debug(*vargs, lf_first: bool = False):
    ''' Function which prints debug only if the debug mode is activated.

    :param *vargs: values to be printed.
    :param lf_first: Adds a line feed first if ``True``.

    :return: No returned value
    '''
    if gd("test_debug", False):
        _custom_print("DEBUG ", *vargs, lf_first=lf_first)


def print_info(*vargs, lf_first: bool = False):
    ''' Function which prints an information for the user.

    :param *vargs: values to be printed.
    :param lf_first: Adds a line feed first if ``True``.

    :return: No returned value
    '''
    _custom_print("INFO  ", *vargs, lf_first=lf_first)


def print_warn(*vargs, lf_first: bool = False):
    ''' Function which prints a warning for the user.

    :param *vargs: values to be printed.
    :param lf_first: Adds a line feed first if ``True``.

    :return: No returned value
    '''
    _custom_print("WARN  ", *vargs, lf_first=lf_first)
