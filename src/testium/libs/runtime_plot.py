import sys
import os
import multiprocessing as mp
from threading import Timer
from time import sleep, monotonic

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PySide6.QtCore import Signal, QThread
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

import numpy as np

import matplotlib.dates as mdates
from datetime import datetime, timedelta, timezone

from interpreter.test_items.test_result import TestValue
from interpreter.utils.tum_except import ETUMRuntimeError
from interpreter.utils.py_func_exec import py_func_exec
from interpreter.utils.eval import post_evaluate
from interpreter.utils.periodic_timer import PeriodicTimer
from interpreter.utils.paths import abs_path_from_file, prepare_file_to_save


class ThreadMsgDispatch(QThread):
    message_received = Signal(dict)

    def __init__(self, queue, parent=None):
        super().__init__(parent)
        self.__to_be_stopped = False
        self._queue = queue

    def run(self):
        stopping = False
        while True:
            if self._queue is None:
                sleep(1)
                continue
            while not self._queue.empty():
                m = self._queue.get()
                self.message_received.emit(m)
            if stopping:
                break
            if self.__to_be_stopped:
                stopping = True
            sleep(0.1)

    def stop(self):
        self.__to_be_stopped = True


class RealTimePlotCurve:
    def __init__(
        self, name, init_value: float, date0: datetime, t0: float, log_path: str
    ) -> None:
        self.name = name
        self.data = np.array([init_value])
        self.date0 = date0
        self.t0 = t0
        self.basetime = datetime.fromtimestamp(0)
        sec = monotonic() - self.t0
        self.time = np.array([self.date0 + timedelta(seconds=sec)])
        self.timestamp = np.array([sec])
        self.file_path = log_path
        if self.file_path != "":
            self.file_path = os.path.join(
                self.file_path, "plot_line-" + self.name + ".csv"
            )
            try:
                prepare_file_to_save(self.file_path)
                with open(self.file_path, "x") as f:
                    f.write("time; timestamp; {}\n".format(self.name))
            except:
                pass

    def __str__(self) -> str:
        return self.name

    def add(self, value):
        self.data = np.append(self.data, value)
        secs = monotonic() - self.t0
        self.timestamp = np.append(self.timestamp, secs)
        time_value = self.date0 + timedelta(seconds=secs)
        self.time = np.append(self.time, time_value)
        if self.file_path != "":
            try:
                with open(self.file_path, "a") as f:
                    f.write("{};{};{}\n".format(str(time_value), secs, value))
            except:
                pass

    def values(self):
        return self.time, self.timestamp, self.data

    def last_value(self):
        return self.time[-1], self.timestamp[-1], self.data[-1]


class DialogRealTimePlot(QMainWindow):
    MARGINS = {"left": 70, "right": 10, "top": 10, "bottom": 80}

    def __init__(
        self, name: str, msg_queue: mp.Queue, msg_out: mp.Queue, log_path: str
    ):
        super().__init__()
        self.lines = []
        self.name = name
        self.msg_queue = msg_queue
        self.msg_out = msg_out
        self.log_path = log_path

        self.setWindowFlag(Qt.WindowCloseButtonHint, False)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # Creation of the matplotlib figure
        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)
        self.toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)

        # Plot creation
        self.ax = self.fig.add_subplot()
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
        self.ax.grid(True, which='both')
        self.ax.grid('on', which='minor', linestyle='--')
        self.ax.minorticks_on()
        self.t0 = monotonic()
        self.date0 = datetime.now()

        # Command queue instantiation
        self.thr_dispatch = ThreadMsgDispatch(self.msg_queue)
        self.thr_dispatch.message_received.connect(self.compute_message)
        self.thr_dispatch.start()

        # Connects resizeEvent to the margin resizing function
        self.canvas.mpl_connect("resize_event", self.adjust_margins)

        self.adjust_margins()

    def __val_to_json(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)

    def adjust_margins(self, event=None):
        # adjusts margins according to the actual canvas size
        width, height = self.canvas.get_width_height()

        left_margin = self.MARGINS["left"] / width  # value in pixels
        right_margin = self.MARGINS["right"] / width  # value in pixels
        top_margin = self.MARGINS["top"] / height  # value in pixels
        bottom_margin = self.MARGINS["bottom"] / height  # value in pixels

        # Adjusts the figure size space
        self.fig.subplots_adjust(
            left=left_margin,
            right=1.0 - right_margin,
            top=1.0 - top_margin,
            bottom=bottom_margin,
        )

        # Redraw the figure
        self.canvas.draw()

    def update_plot(self):
        self.ax.relim()
        self.ax.autoscale_view()
        for tick_label in self.ax.get_xticklabels():
            tick_label.set_rotation(60)
        self.canvas.draw()

    def compute_message(self, message):
        # Plot update
        command = message["command"]
        if command == "stop":
            self.thr_dispatch.stop()
            self.thr_dispatch.wait()
            self.close()

        command = message["command"]
        if command == "enable_exit_btn":
            size = self.size()
            self.setWindowFlag(Qt.WindowCloseButtonHint, True)
            self.resize(size)
            self.show()

        if command == "add":
            values = message["values"]
            for k in values.keys():
                curve = None
                line = None
                for l, c in self.lines:
                    if str(c) == k:
                        curve = c
                        line = l
                        c.add(values[k])

                if curve is None:
                    curve = RealTimePlotCurve(
                        k, values[k], self.date0, self.t0, self.log_path
                    )
                    t, _, v = curve.values()
                    (line,) = self.ax.plot(t, v, label=k)
                    self.ax.legend()
                    self.lines.append((line, curve))

                else:
                    t, _, v = curve.values()
                    line.set_xdata(t)
                    line.set_ydata(v)

            self.update_plot()

        if command == "last_values":
            res = {}
            for _, curve in self.lines:
                time, timeout, value = curve.last_value()

                res.update(
                    {
                        curve.name: [
                            str(time),
                            self.__val_to_json(timeout),
                            self.__val_to_json(value),
                        ]
                    }
                )
            self.msg_out.put(res)

        if command.startswith("export"):
            tf = command.split(".")[1]
            if tf == "pdf":
                prepare_file_to_save(message["values"])
                self.canvas.figure.savefig(message["values"])
            if tf == "csv":
                headers = ""
                for l, c in self.lines:
                    t, _, v = c.values()
                    data = np.column_stack((t, v))
                    headers = "time;" + str(c)
                    fname = os.path.splitext(message["values"])[0] + "-" + str(c)
                    fname = fname + os.path.splitext(message["values"])[1]
                    prepare_file_to_save(fname)
                    np.savetxt(fname, data, delimiter=";", fmt="%s", header=headers)


def plot_app(args, queue_in, queue_out):
    app = QApplication([])
    d = DialogRealTimePlot(args[0], queue_in, queue_out, args[1])
    d.setWindowTitle(args[0])
    d.show()
    sys.exit(app.exec())


class RuntimePlotPeriodic(PeriodicTimer):
    def __init__(self, msg_queue, period, file, func_name, args, post_eval="") -> None:
        super().__init__(period, self.on_timer_event)
        self.msg_queue = msg_queue
        self.file = file
        self.func_name = func_name
        self.args = args
        self.post_eval = post_eval
        self.start()
        self.on_timer_event()

    def on_timer_event(self):
        succ, ret = py_func_exec(self.file, self.func_name, self.args)
        if succ == TestValue.SUCCESS:
            res, _ = ret
            res = post_evaluate(self.post_eval, res)
            self.msg_queue.put({"command": "add", "values": res})
        else:
            print("Plot periodic timer function ({self.file}/{self.func_name}) failed: \"{ret}\"")

class RuntimePlot:
    EXPORTS = [".pdf", ".csv"]

    def __init__(self, name: str, log_path: str = None) -> None:
        self.name = name
        self.periodic = []
        self._log_path = ""
        if log_path:
            self._log_path = log_path
        self.msg_queue_out = mp.Queue()
        self.msg_queue_in = mp.Queue()
        print(f"Opening the \"{self.name}\" plot window")
        self.p = mp.Process(
            target=plot_app,
            name=self.name,
            args=([self.name, self._log_path], self.msg_queue_out, self.msg_queue_in),
        )
        self.p.start()

    def close(self):
        for p in self.periodic:
            p.stop()

        if self.p.is_alive():
            self.msg_queue_out.put({"command": "stop"})
            self.p.join()
            print("Plot window closed.")
        else:
            raise ETUMRuntimeError(f"The plot window \"{self.name}\" has died unexpectedly")

    def close_wait_dialog_exit(self, timeout=-1):
        for p in self.periodic:
            p.stop()
            self.periodic = []
        if self.p.is_alive():
            if timeout > 0:
                tmr = Timer(timeout, self.on_close_timeout)
                tmr.start()
            self.msg_queue_out.put({"command": "enable_exit_btn"})
            self.p.join()
            print("Plot window closed.")
        else:
            raise ETUMRuntimeError(f"The plot window \"{self.name}\" has died unexpectedly")

    def on_close_timeout(self):
        if self.p.is_alive():
            self.close()

    def add_periodic(self, period, module, func_name, args=None, post_eval=""):
        self.periodic.append(
            RuntimePlotPeriodic(
                self.msg_queue_out, period, module, func_name, args, post_eval
            )
        )

    def add(self, dict_values):
        self.msg_queue_out.put({"command": "add", "values": dict_values})

    def save(self, file_name):
        path = abs_path_from_file(file_name)
        if not path.suffix in self.EXPORTS:
            raise ETUMRuntimeError(
                f"The \"{self.name}\" plot exported file type is unknown (file = {str(path)})"
            )

        self.msg_queue_out.put({"command": "export" + path.suffix, "values": str(path)})

    def last_values(self) -> dict:
        while not self.msg_queue_in.empty():
            self.msg_queue_in.get()
        self.msg_queue_out.put({"command": "last_values"})
        try:
            res = self.msg_queue_in.get(timeout=1)
        except:
            raise ETUMRuntimeError(f"Impossible to retrieve the last values of the \"{self.name}\" plot")
        return res
