import importlib
import logging
import os
from pathlib import Path
from types import ModuleType
from typing import List

from flowd import metrics

COLLECTOR_CLASSNAME = "MetricCollector"

MetricModules = List[ModuleType]
Collectors = List[metrics.BaseCollector]


class Supervisor:
    """Does all the initial setup and manages the lifecycle
    of metric collectors."""

    def __init__(self) -> None:
        self.collected_data_path = os.path.expanduser("~/flowd/")

        self._collectors: Collectors = []

    def configure(self) -> None:
        os.makedirs(self.collected_data_path, exist_ok=True)

        self._collectors = lookup_handlers(collect_metric_modules())

    def run(self) -> None:
        ...


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
        except ImportError as e:
            logging.error(e)
            continue
        mods.append(module)

    return mods


def lookup_handlers(ctrs: MetricModules) -> Collectors:
    """Gets a list of handlers from list of metric modules."""
    handlers = []

    for c in ctrs:
        h = getattr(c, COLLECTOR_CLASSNAME, None)

        try:
            if not h or not issubclass(h, metrics.BaseCollector):
                logging.warning(
                    f"{c.__name__} does not contain a class {COLLECTOR_CLASSNAME}"
                )
                continue
        except TypeError:
            logging.warning(
                f"expected {COLLECTOR_CLASSNAME} in module {c.__name__} to "
                f"implement {metrics.BaseCollector.__qualname__}, which it didn't"
            )
            continue

        handlers.append(h())

    return handlers
