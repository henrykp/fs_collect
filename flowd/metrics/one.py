import logging
import threading
import time
from flowd.metrics import BaseCollector


class MetricCollector(BaseCollector):

    metric_name = "test_metric"

    def __init__(self) -> None:
        self.count = 0  # for interval

    def stop_collect(self) -> None:
        return

    def start_collect(self) -> None:
        return

    def get_current_state(self) -> tuple:
        return self.metric_name, self.count

    def cleanup(self) -> None:
        self.count = 0


if __name__ == '__main__':
    # Example of usage
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)-8s %(message)s")
    collector = MetricCollector()
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
