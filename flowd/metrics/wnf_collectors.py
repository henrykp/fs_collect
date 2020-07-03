import logging
import threading
import time
from flowd.utils import wnf
from flowd.metrics import BaseCollector

PRIORITY_MODE = 1
ALERT_MODE = 2


class PriorityModeCollector(BaseCollector):

    metric_name = "Time in Priority Mode (seconds)"

    def __init__(self) -> None:
        self.time_in_mode = 0
        self.is_run = True

    def stop_collect(self) -> None:
        self.is_run = False

    def start_collect(self) -> None:
        start_time = time.time()
        while self.is_run:
            if wnf.do_read(wnf.format_state_name("WNF_SHEL_QUIETHOURS_ACTIVE_PROFILE_CHANGED")) == PRIORITY_MODE:
                self.time_in_mode += time.time() - start_time
                start_time = time.time()
            time.sleep(1)

    def get_current_state(self) -> tuple:
        t = int(round(self.time_in_mode))
        logging.debug(f'Time in priority mode: {t}')
        return self.metric_name, t

    def cleanup(self) -> None:
        self.is_run = True
        self.time_in_mode = 0


class AlertModeCollector(BaseCollector):

    metric_name = "Time in Alerts Only Mode (seconds)"

    def __init__(self) -> None:
        self.time_in_mode = 0
        self.is_run = True

    def stop_collect(self) -> None:
        self.is_run = False

    def start_collect(self) -> None:
        start_time = time.time()
        while self.is_run:
            if wnf.do_read(wnf.format_state_name("WNF_SHEL_QUIETHOURS_ACTIVE_PROFILE_CHANGED")) == ALERT_MODE:
                self.time_in_mode += time.time() - start_time
                start_time = time.time()
            time.sleep(1)

    def get_current_state(self) -> tuple:
        t = int(round(self.time_in_mode))
        logging.debug(f'Time in alert mode: {t}')
        return self.metric_name, t

    def cleanup(self) -> None:
        self.time_in_mode = 0
        self.is_run = True


if __name__ == '__main__':
    # Example of usage
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)-8s %(message)s")
    collector = PriorityModeCollector()
    x = threading.Thread(target=collector.start_collect, args=())
    logging.debug("Main    : create and start thread")
    x.start()
    logging.debug("Main    : wait for the thread to finish")
    time.sleep(10)
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

    logging.basicConfig(level=logging.DEBUG, format="%(levelname)-8s %(message)s")
    collector = AlertModeCollector()
    x = threading.Thread(target=collector.start_collect, args=())
    logging.debug("Main    : create and start thread")
    x.start()
    logging.debug("Main    : wait for the thread to finish")
    time.sleep(30)
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
