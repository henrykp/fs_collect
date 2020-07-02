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

    metric_name = "SSH Session Active (seconds)"

    PORTS = [21, 22]

    def __init__(self) -> None:
        self.is_run = True
        self.time_in_mode = 0

    def stop_collect(self) -> None:
        self.is_run = False

    def start_collect(self) -> None:
        start_time = time.time()
        while self.is_run:
            for x in psutil.net_connections(kind="all"):
                # get remote address
                if x.raddr:
                    r_address, r_port = x.raddr
                    if r_port in self.PORTS and x.status == psutil.CONN_ESTABLISHED:
                        logging.debug(x)
                        self.time_in_mode += time.time() - start_time
                        start_time = time.time()
            time.sleep(1e6)

    def get_current_state(self) -> tuple:
        return self.metric_name, int(round(self.time_in_mode))

    def cleanup(self) -> None:
        self.time_in_mode = 0
        self.is_run = True


if __name__ == '__main__':
    # Example of usage
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)-8s %(message)s")
    collector = SSHActivityCollector()
    collector.start_collect()
