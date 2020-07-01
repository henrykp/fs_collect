import logging
import threading
import time

from flowd.metrics import BaseCollector
from flowd.utils.windows import seconds_since_last_input


class AFKCollector(BaseCollector):
    """
    Time in AFK﻿
    ---
    Seconds per minute﻿, AFK timeout - 30 sec﻿
    """
    metric_name = "afk"
    AFK_TIMEOUT_SEC = 30

    def __init__(self) -> None:
        self.count = 0
        self._afk = False
        self.is_run = True

    def start_collect(self):
        while self.is_run:
            seconds_since_input = seconds_since_last_input()
            logging.debug(f'Seconds since last input: {seconds_since_input}')

            if self._afk and seconds_since_input < self.AFK_TIMEOUT_SEC:
                logging.info("No longer AFK")
                self._afk = False
            # If becomes AFK
            elif not self._afk and seconds_since_input >= self.AFK_TIMEOUT_SEC:
                logging.info("Became AFK")
                self._afk = True
                self.count += 1
            else:
                if self._afk:
                    self.count += 1

            logging.debug(f'Current state {self.metric_name} {self.count}')
            logging.debug(f'AFK: {self._afk}')
            time.sleep(1)

    def stop_collect(self) -> None:
        self.is_run = False

    def get_current_state(self) -> tuple:
        return self.metric_name, self.count

    def cleanup(self) -> None:
        self.count = 0
        self.is_run = True


if __name__ == "__main__":
    # Example of usage
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)-8s %(message)s")
    win_collector = AFKCollector()

    # start first time
    x = threading.Thread(target=win_collector.start_collect, args=())
    x.start()
    time.sleep(60)
    win_collector.stop_collect()

    metric_name, value = win_collector.get_current_state()
    logging.info(f'metric_name {metric_name}')
    logging.info(f'value {value}')

    win_collector.cleanup()

    # start second time
    x = threading.Thread(target=win_collector.start_collect, args=())
    x.start()
    time.sleep(5)
    win_collector.stop_collect()

    metric_name, value = win_collector.get_current_state()
    logging.info(f'metric_name {metric_name}')
    logging.info(f'value {value}')

    win_collector.cleanup()
