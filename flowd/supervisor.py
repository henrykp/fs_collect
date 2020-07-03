import datetime
import importlib
import logging
import time
import os
import threading
from pathlib import Path
from types import ModuleType
from typing import List
from typing import Optional
from flowd.model import logistic_regression
from flowd.utils import wnf

import pythoncom

from flowd import metrics

MetricModules = List[ModuleType]
Collectors = List[metrics.BaseCollector]


class Supervisor:
    """Does all the initial setup and manages the lifecycle
    of metric collectors."""

    def __init__(self) -> None:
        self.collect_interval: float = 60
        self.collected_data_path = os.path.expanduser("~/flowd/")

        self._collectors: Collectors = []
        self._quit = threading.Event()
        self._active: List[CollectorThread] = []
        self._data: Optional[str] = None
        self._data_pivot: Optional[str] = None
        self.model = logistic_regression.train_model()
        self.flow_threshold = 70
        self._fs_data: Optional[str] = None
        self._flow_state = 0

    @staticmethod
    def _sort_collectors(element):
        name, v = element.get_current_state()
        return name

    def configure(self) -> None:
        os.makedirs(self.collected_data_path, exist_ok=True)
        self._data = os.path.join(self.collected_data_path, "data.csv")
        self._data_pivot = os.path.join(self.collected_data_path, "data_pivot.csv")
        self._fs_data = os.path.join(self.collected_data_path, "fs_data.csv")
        logging.info(f"storing collected data in {self._data}")

        self._collectors = lookup_handlers(collect_metric_modules())
        self._collectors.sort(key=self._sort_collectors)
        self.write_headers()

    def write_headers(self) -> None:
        if not os.path.exists(self._data_pivot) or os.path.getsize(self._data_pivot) == 0:
            with open(self._data_pivot, "a") as f1:
                header = "date"
                for c in self._collectors:
                    name, v = c.get_current_state()
                    header = f"{header},{name}"
                f1.write(f"{header}\n")
        if not os.path.exists(self._fs_data) or os.path.getsize(self._fs_data) == 0:
            with open(self._fs_data, "a") as fs:
                fs.write("Date,Flow State Prediction (%)\n")

    def run(self) -> None:
        if not self._collectors:
            logging.error(
                "we didn't find any collector implementations, nothing to do"
            )
            return

        logging.info("began collecting metrics")

        self._active = [CollectorThread(c) for c in self._collectors]
        for t in self._active:
            t.start()

        while not self._quit.is_set():
            time.sleep(self.collect_interval)
            threading.Thread(target=self.output_collected_metrics).start()
            self._flow_state = self.check_flow_state()
            wnf.set_focus_mode(2 if self._flow_state > self.flow_threshold else 0)

    def check_flow_state(self) -> bool:
        p = int(logistic_regression.predict(logistic_regression.pivot_stats(), self.model, 15))
        logging.info(f'Last 15 minutes prediction {p * 100}%')
        return p

    def stop(self, timeout: float = None) -> None:
        self._quit.set()
        for c in self._active:
            c._collector.stop_collect()
            c.join(timeout)

    def output_collected_metrics(self) -> None:
        if not self._data:
            logging.warning("unknown data file path; did you call configure()?")
            return

        ts = datetime.datetime.now()
        with open(self._data, "a") as f:
            with open(self._data_pivot, "a") as f1:
                row = ""
                for ct in self._active:
                    name, current = ct.pop()
                    if not ct.is_alive():
                        current = -1
                    f.write(f"{name},{current},{ts}\n")
                    row = f"{row},{current}"
                f1.write(f"{ts}{row}\n")
        with open(self._fs_data, "a") as fs:
            fs.write(f"{ts},{self._flow_state}\n")


class CollectorThread(threading.Thread):
    """A collector interface-aware thread wrapper."""

    def __init__(self, collector: metrics.BaseCollector) -> None:
        self._collector = collector
        super().__init__(
            name=f"CollectorThread-{self._collector.metric_name}", daemon=True
        )

    def run(self) -> None:
        pythoncom.CoInitialize()
        try:
            self._collector.start_collect()
        except Exception as e:
            logging.error(f"Unexpected error in {self.name}: {e}", exc_info=True)
            return
        finally:
            pythoncom.CoUninitialize()
            self._collector.stop_collect()

    def pop(self) -> metrics.CollectedData:
        v = self._collector.get_current_state()
        self._collector.cleanup()
        return v


def collect_metric_modules() -> MetricModules:
    """Gets a list of all available metric modules
    from the metrics package. Doesn't do any filtering or collector lookups."""
    # TODO(alex): check how well the runtime module
    # collection works when compiled to a binary
    logging.debug("looking for collectors in the metrics module")
    mods = []

    metrics_pkg_path = Path(metrics.__file__).parent
    for file in metrics_pkg_path.glob("*"):
        if file.suffix not in (".py", ".pyc", ".pyd"):
            continue

        if file.stem == "__init__":
            continue

        module_name = ".".join([metrics.__name__, file.stem])
        try:
            module = importlib.import_module(module_name)
        except (ImportError, AttributeError) as e:
            logging.error(e)
            continue
        mods.append(module)

    return mods


def lookup_handlers(mods: MetricModules) -> Collectors:
    """Gets a list of handlers from list of metric modules."""
    collectors = []

    for m in mods:
        for v in m.__dict__.values():
            try:
                if v and issubclass(v, metrics.BaseCollector):
                    collectors.append(v())
                    logging.info(
                        f"found a metric collector {m.__name__}:{v.metric_name}"
                    )
            except TypeError:
                continue

    return collectors
