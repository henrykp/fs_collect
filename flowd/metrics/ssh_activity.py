import logging
import time
from flowd.metrics import BaseCollector
import psutil


class SSHActivityCollector(BaseCollector):
    """
    Active SSH connections
    ---
    Seconds in minute
    """

    metric_name = "ssh_activity"

    PORTS = [21, 22]

    def __init__(self) -> None:
        self.count = 0
        self.is_run = True

    def stop_collect(self) -> None:
        self.is_run = False

    def start_collect(self) -> None:
        while self.is_run:
            for x in psutil.net_connections(kind="all"):
                # get remote address
                if x.raddr:
                    r_address, r_port = x.raddr
                    if r_port in self.PORTS and x.status == psutil.CONN_ESTABLISHED:
                        logging.debug(x)
                        self.count += 1

            logging.debug(f'Current state {self.count}')
            time.sleep(1)

    def get_current_state(self) -> tuple:
        return self.metric_name, self.count

    def cleanup(self) -> None:
        self.count = 0
        self.is_run = True


if __name__ == '__main__':
    # Example of usage
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)-8s %(message)s")
    collector = SSHActivityCollector()
    collector.start_collect()
