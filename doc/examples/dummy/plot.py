import random
import py_func.tm as tm
from py_func.tm import FunctionItem

def random_value():
    return random.random()

class LastValues(FunctionItem):
    def exec(self, name):
        res = tm.last_plot_value(name)
        self.reportValue('my_reported_value', res)
        print("Last plot value: {}".format(res))
        return res
