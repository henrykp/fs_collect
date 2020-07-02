import time
from typing import Tuple
from flowd.metrics import BaseCollector


class MetricCollector(BaseCollector):
    metric_name = "Test Metric"

    def __init__(self) -> None:
        self.count = 0
        self.should_continue = True

    def stop_collect(self) -> None:
        self.should_continue = False

    def start_collect(self) -> None:
        # while self.should_continue:
        #     self.count += 1
        #     time.sleep(1)
        pass

    def get_current_state(self) -> Tuple[str, float]:
        return self.metric_name, self.count

    def cleanup(self) -> None:
        self.count = 0
