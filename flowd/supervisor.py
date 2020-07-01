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

    def configure(self) -> None:
        os.makedirs(self.collected_data_path, exist_ok=True)
        self._data = os.path.join(self.collected_data_path, "data.csv")
        logging.info(f"storing collected data in {self._data}")

        self._collectors = lookup_handlers(collect_metric_modules())

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
            for ct in self._active:
                if not ct.is_alive():
                    continue

                name, current = ct.pop()
                f.write(f"{name},{current},{ts}\n")


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
