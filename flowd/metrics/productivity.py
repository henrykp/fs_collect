import logging
import re
import time

from flowd.metrics import BaseCollector
from flowd.utils.windows import get_current_active_window


BROWSER_REGEXP = r'(.*GitHub.*)|(.*Stack Overflow.*)|(Python\.org)|' \
                 r'(.*Google.*)|(PyPI)|(.*epam.*)﻿|' \
                 r'(.*jira.*)|(.*Python.*)'


class ProductivityWindowCollector(BaseCollector):
    """
    Window in a the productivity class activated
    ---
    Number of 15 seconds intervals per minute (for example, 3 minutes = 12 intervals)﻿
    """
    metric_name = "productivity_window"

    APPS = (
        ('eclipse', re.compile(r'.*Eclipse IDE﻿')),
        ('pycharm', re.compile(r'.* - PyCharm')),
        ('python', re.compile(r'Python \d.\d')),
        ('dbeaver', re.compile(r'DBeaver \d\.\d.*﻿')),
        ('explorer', re.compile(r'FileExplorer.*﻿')),
        ('VISIO', re.compile(r'.*Visio.*﻿')),
        ('putty', re.compile(r'.* - PuTTY')),
        ('cmd', re.compile(r'.*cmd.exe*')),
        ('GitHubDesktop', re.compile(r'GitHub Desktop.*﻿﻿')),
        ('Far', re.compile(r'.* - Far.*﻿')),
        ('ONENOTE', re.compile(r'.*﻿')),
        ('Taskmgr', re.compile(r'.*')),
        # browsers
        ('opera', re.compile(BROWSER_REGEXP, re.I)),
        ('firefox', re.compile(BROWSER_REGEXP, re.I)),
        ('chrome', re.compile(BROWSER_REGEXP, re.I))
    )

    INTERVAL_SEC = 15

    def __init__(self) -> None:
        self.count = 0  # for interval
        self._second_count = 0
        self.is_run = True

    def _is_productivity_class(self, cur_win) -> bool:
        """ Check is productive class """
        is_productive_process, is_productive_title = False, False
        res_apps = [i[0] in cur_win['app_name'] for i in self.APPS]
        try:
            ind = res_apps.index(True)
            is_productive_process = True

            if self.APPS[ind][1].match(cur_win['title']):
                is_productive_title = True

        except ValueError:
            pass

        logging.debug(f'is_productive_process {is_productive_process}')
        logging.debug(f'is_productive_title {is_productive_title}')
        return is_productive_process and is_productive_title

    def start_collect(self):
        while self.is_run:
            current_window = get_current_active_window()
            logging.debug(f'Current window {current_window}')

            if self._is_productivity_class(current_window):
                self._second_count += 1

                if self._second_count > self.INTERVAL_SEC:
                    self._second_count = 0
                    self.count += 1
            else:
                # kind of distraction, reset seconds counter ?
                self._second_count = 0

            logging.debug(f'Current state {self.count}')
            logging.debug(f'second_count {self._second_count}')

            time.sleep(1)

    def stop_collect(self) -> None:
        self.is_run = False

    def get_current_state(self) -> tuple:
        return self.metric_name, self.count

    def cleanup(self) -> None:
        self.count = 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)-8s %(message)s")
    win_collector = ProductivityWindowCollector()
    win_collector.start_collect()
