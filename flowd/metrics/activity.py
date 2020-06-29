import logging
import time

from flowd.metrics import BaseCollector


class ActivityWindowCollector(BaseCollector):
    """
    Active Window Changed
    ---
    Number per minute﻿
    """
    metric_name = "activity_window"

    def __init__(self) -> None:
        self.count = 0
        self._prev_window = None
        self.is_run = True

    def start_collect(self):
        # for threading need import wmi lib
        from flowd.utils.windows import get_current_active_window

        while self.is_run:
            current_window = get_current_active_window()
            logging.debug(f'Current window {current_window}')
            logging.debug(f'Previous window {self._prev_window}')

            # check app and title
            if self._prev_window and self._prev_window != current_window:
                self.count += 1

            self._prev_window = current_window
            logging.debug(f'Current state {self.count}')

            time.sleep(1)

    def stop_collect(self) -> None:
        self.is_run = False

    def get_current_state(self) -> tuple:
        return self.metric_name, self.count

    def cleanup(self) -> None:
        self.count = 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)-8s %(message)s")
    win_collector = ActivityWindowCollector()
    win_collector.start_collect()
