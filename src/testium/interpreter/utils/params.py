import interpreter.utils.globdict as globdict
from interpreter.utils.tum_except import ETUMSyntaxError, ETUMRuntimeError

glob_eval_func = None

class TestItemParams:

    def __init__(self, dict_item={}, parent=None):
        self._dicoparam = dict_item
        self._parent = parent

    def expanse(self, param_value):
        return expanse(param_value, self._parent)

    def getParam(self, parameter, default=None, required=False, processed=False):
        """Returns a parameter value from the test item dictionnary.

        :param parameter:   list or string which are the parameter name(s).
        :type parameter:    list or string
        :param default:     default value if no param and not required.
        :type default:      string
        :param required:    if True, the function raises an Exception in case of missing param.
        :type required:     bool
        :param processed:   if True, variable substitution is applied.
        :type processed:    bool
        :return:            a parameter value or default
        """
        result = default

        if not isinstance(parameter, (tuple, list)):
            if not isinstance(parameter, str):
                raise ETUMSyntaxError('"%s" parameter syntax error' % (parameter))
            parameter = [parameter]

        has_parameter = False
        for para in parameter:
            if (
                (not (self._dicoparam is None))
                and (isinstance(self._dicoparam, dict))
                and (para in self._dicoparam)
            ):
                result = self._dicoparam[para]
                if processed:
                    result = self.expanse(result)
                has_parameter = True
                break

        if (not has_parameter) and required:
            raise ETUMSyntaxError('"%s" parameter must exist' % (parameter[0]))
        return result

    def getParamAll(self, parameter, default=[], required=False, processed=False):
        """Returns a parameter list (if any) from the test item dictionnary.

        :param parameter:   list or string giving the parameter name.
        :type parameter:    list or string
        :param default:     default value if no param and not required.
        :type default:      list
        :param required:    if True, the function raises an Exception in case of missing param.
        :type required:     bool
        :param processed:   if True, variable substitution is applied.
        :type processed:    bool
        :return:            a parameter list or default
        """
        results = default

        if not isinstance(parameter, (tuple, list)):
            if not isinstance(parameter, str):
                raise ETUMSyntaxError('"%s" parameter syntax error' % (parameter))
            parameter = [parameter]

        has_parameter = False
        for para in parameter:
            if para in self._dicoparam:
                has_parameter = True
                results = []
                if isinstance(self._dicoparam[para], (tuple, list)):
                    list_params = self._dicoparam[para]
                else:
                    list_params = [self._dicoparam[para]]

                for p in list_params:
                    if processed:
                        p = self.expanse(p)
                    results.append(p)

        if (not has_parameter) and required:
            raise ETUMSyntaxError('"%s" parameter must exist' % (parameter[0]))

        return results

    def getParamFromList(self, params):
        results = []

        for param in params:
            if "$(loop_param)" == param:
                result = getLoopParam(self._parent)
                if result is None:
                    raise ETUMSyntaxError("parent sequence is not a loop")
            elif "$(loop_index)" == param:
                result = getLoopIndex(self._parent)
                if result is None:
                    raise ETUMSyntaxError("parent sequence is not a loop")
            else:
                # If not in global, try in local
                result = param

            results.append(result)
        return results

    def getData(self):
        return self._dicoparam


def getLoopParam(parent):
    """This function is returning the first found loop_param value.
    The loop_param is searched recursively into the upper layers of tests
    items.
    It returns the loop_param or 'None'.
    """
    res = None
    if hasattr(parent, "_currentLoop"):
        res = parent._currentLoop
    else:
        # Parent is None in case of a root item
        if parent._parent is not None:
            res = getLoopParam(parent._parent)
    return res


def getLoopIndex(parent):
    """This function is returning the first found loop_index value.
    The loop_index is searched recursively into the upper layers of tests
    items.
    It returns the loop_index or 'None'.
    """
    res = None
    try:
        res = parent._currentIter
    except AttributeError:
        # Parent is None in case of a root item
        if parent._parent is not None:
            res = getLoopIndex(parent._parent)
    return res

def getLoopCount(parent):
    """This function is returning the first found loop_count value.
    The loop_count is searched recursively into the upper layers of tests
    items.
    It returns the loop_index or 'None'.
    """
    res = None
    try:
        res = parent._niter
    except AttributeError:
        # Parent is None in case of a root item
        if parent._parent is not None:
            res = getLoopCount(parent._parent)
    return res

def getInverseLoopIndex(parent):
    """This function is returning the first found loop_index_inverse value.
    The loop_index_inverse is searched recursively into the upper layers of tests
    items.
    It returns the loop_index_inverse or 'None'.
    """
    res = None
    try:
        res = parent._currentInverseIter
    except AttributeError:
        # Parent is None in case of a root item
        if parent._parent is not None:
            res = getInverseLoopIndex(parent._parent)
    return res


def find_matches(string, left_patt, right_patt):
    """ The object of this function is to identify the expandable
        parts of a string.
        The returned values are tables of doublets corresponding to
        the index of extractable sub-strings.
    """
    result = []

    # find all left pattern
    l = len(string)
    i = 0
    while i < l:
        # first we are looking for the first left pattern
        leftind = string.find(left_patt, i)
        if leftind >= 0:
            leftind += len(left_patt)
            # Second we are looking for the first right pattern
            # (on the right of the first left pattern)
            rightind = string.find(right_patt, leftind)
            if rightind >= 0:
                # Right pattern found
                next_left = leftind
                while next_left < rightind:
                    # third we are looking for the last left pattern
                    # before the right pattern
                    j = string.find(left_patt, next_left)
                    if j > 0 and j < rightind:
                        next_left = j + len(left_patt)
                    else:
                        break
                if (next_left >= 0) and next_left < rightind:
                    result.append([next_left, rightind])
                    i = rightind + len(right_patt)
                else:
                    i = next_left
            else:
                # right pattern not found on the right of the first left pattern
                # No match then
                break
        else:
            # left pattern not found
            # No match then
            break

    return result


def _parse_and_process(left_patt, right_patt, value, func, *fparam):
    """This function parses a string value to check if patterns corresponding
    to expr exist.
    syntax_weight is the size of the syntax around the extracted variable name.
        for ex: $(toto) syntax weight is len("$()")
    When this kind of pattern is found, operation on the extracted value is
    performed. this is the object of func and fparam (fparam: func
    params as table).
    """
    result = value
    cont = True
    while cont and (isinstance(result, str)):
        cont = False
        o = 0
        tmp_res = ""
        matches = find_matches(result, left_patt, right_patt)
        for s in matches:
            len_left = len(left_patt)
            len_right = len(right_patt)
            # Get the positions of the match
            r = s[0] - len_left
            tmp_res = tmp_res + result[o : r]
            o = s[1] + len_right
            # Get the global value to search
            extract = result[s[0] : s[1]]
            # Try to access to the global value
            treated, g = func(extract, *fparam)
            if not treated:
                # No result found in globals
                tmp_res = tmp_res + result[r : o]
            else:
                # Results found, we continue to loop
                cont = True
                if isinstance(g, str):
                    tmp_res = tmp_res + g
                else:
                    if len(result.strip()) == (
                        len(extract) + len_left + len_right
                    ):
                        tmp_res = g
                    else:
                        tmp_res = tmp_res + str(g)

        # if something has been replaced
        if isinstance(tmp_res, str) and cont:
            tmp_res = tmp_res + result[o:]
            result = tmp_res
        elif cont:
            result = tmp_res

    return result


def _operate_param(glob, parent):
    """This function checks if glog exists in the global dict or
    if it is a loop variable.
    """
    treated = True
    if (glob == "loop_param") and (parent is not None):
        g = getLoopParam(parent)
    elif (glob == "loop_index") and (parent is not None):
        g = getLoopIndex(parent)
    elif (glob == "loop_index_inverse") and (parent is not None):
        g = getInverseLoopIndex(parent)
    elif (glob == "loop_count") and (parent is not None):
        g = getLoopCount(parent)
    else:
        g = globdict.gd(glob)
    if g is None:
        treated = False
        g = glob
    return treated, g


def _preprocess_string(value, parent=None):
    """This function parses a string value to check if patterns corresponding
    to $(xxx) exists.
    When this kind of pattern is found, an attempt to replace the variable
    by its value in the global dict is performed.
    If it can't be found in the global dict, not replaced.
    """
    return _parse_and_process("$(", ")", value, _operate_param, parent)


def _eval_param(value):
    """This function parses a string value to check if patterns corresponding
    to $|xxx| exists.
    When this kind of pattern is found, an attempt to evaluate its
    content is done.
    If it is not evaluable, not replaced.
    """
    global glob_eval_func
    return _parse_and_process("$|", "|", value, glob_eval_func)


def _process_recursively(func, param_value, *fparams):
    """This function is scaning recursively param_value to expand it with
    global variables or loop variables.
    """
    result = None
    if isinstance(param_value, str):
        # If a string --> direct expansion
        result = func(param_value, *fparams)
    elif isinstance(param_value, dict):
        # If a dictionary --> check all elements
        result = {}
        for key, val in param_value.items():
            k = key
            if isinstance(key, str):
                k = func(key, *fparams)
            v = _process_recursively(func, val, *fparams)
            result.update({k: v})
    elif isinstance(param_value, list):
        # If a list --> check all elements
        result = []
        for val in param_value:
            result.append(_process_recursively(func, val, *fparams))
    else:
        result = param_value

    return result

def ProcessParam(param_value, parent=None):
    """This function is scaning recursively param_value to expand it with
    global variables or loop variables.
    """
    return _process_recursively(_preprocess_string, param_value, parent)


def ProcessEval(param_value):
    """This function is scaning recursively param_value to expand it with
    global variables or loop variables.
    """
    return _process_recursively(_eval_param, param_value)


def expanse(param_value, parent=None):
    """This function is scaning recursively param_value to expand it:
    - with global variables or loop variables when $() pattern is found.
    - with evaluation of the content of %() pattern when found.
    """
    n = 0
    result = param_value
    while n < 10:
        tmp_res = ProcessParam(result, parent)
        tmp_res = ProcessEval(tmp_res)
        if tmp_res == result:
            break
        result = tmp_res
        n += 1
    return result


def eval_func_init(eval_func):
    global glob_eval_func

    glob_eval_func = eval_func
