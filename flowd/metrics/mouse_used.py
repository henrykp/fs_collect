import logging
import threading
import time
import mouse
from flowd.metrics import BaseCollector


class MouseUsedCollector(BaseCollector):
    """
    Mouse used﻿
    ---
    Seconds per minute﻿
    """

    metric_name = "Mouse Used (seconds)"

    TIMEOUT_NOT_USED_SEC = 3

    def __init__(self) -> None:
        self.second_per_minute = 0
        self.is_run = True
        self._last_event_time = 0

    def stop_collect(self) -> None:
        mouse.unhook(self.mouse_used_callback)
        self.is_run = False

    def mouse_used_callback(self, event):
        duration_sec = event.time - self._last_event_time
        if duration_sec < self.TIMEOUT_NOT_USED_SEC:
            self.second_per_minute += duration_sec

        self._last_event_time = event.time

    def start_collect(self) -> None:
        # set callback on all mouse activities
        mouse.hook(self.mouse_used_callback)

        while self.is_run:
            time.sleep(1e6)

    def get_current_state(self) -> tuple:
        return self.metric_name, self.second_per_minute

    def cleanup(self) -> None:
        self.second_per_minute = 0


if __name__ == '__main__':
    # Example of usage
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)-8s %(message)s")
    collector = MouseUsedCollector()
    x = threading.Thread(target=collector.start_collect, args=())
    logging.debug("Main    : create and start thread")
    x.start()
    logging.debug("Main    : wait for the thread to finish")
    time.sleep(20)
    logging.debug("Main    : stop collect")
    collector.stop_collect()

    metric_name, value = collector.get_current_state()
    logging.info(f'metric_name {metric_name}')
    logging.info(f'value {value}')

    logging.debug("Main    : cleanup")
    collector.cleanup()
    metric_name, value = collector.get_current_state()
    logging.info(f'metric_name {metric_name}')
    logging.info(f'value {value}')
    assert value == 0
