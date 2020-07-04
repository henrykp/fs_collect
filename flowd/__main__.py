import logging
import platform
import signal
import sys
from typing import Any
from typing import Callable
from typing import NoReturn

from flowd.integrations import Event
from flowd.integrations import MicrosoftGraph
from flowd.supervisor import Supervisor

EXIT_SIGNALS = [signal.SIGTERM, signal.SIGINT]
if platform.system() == "Windows":
    EXIT_SIGNALS.append(signal.SIGBREAK)


def on_quit(s: Supervisor) -> Callable:
    def quit(signo: int, _: Any) -> NoReturn:
        logging.info("ok, bye")
        s.stop(0.05)
        sys.exit(0)

    return quit


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
    if "--with-outlook" in sys.argv:
        graph = MicrosoftGraph.from_env()
        graph.authenticate()
        graph.schedule_meeting(Event())

    s = Supervisor()
    for sig in EXIT_SIGNALS:
        signal.signal(sig, on_quit(s))
    s.configure()
    s.run()


if __name__ == "__main__":
    main()
