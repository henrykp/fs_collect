import logging
import re
import time

from flowd.metrics import BaseCollector


BROWSER_REGEXP = r'(.*YouTube.*)|(.*Facebook.*)|(.*VK.*)|(.*instagram.*)|(.*twitter.*)|' \
                 r'(.*VK.*)|(.*VKontakte.*)|(.*Pinterest.*)|(.*LinkedIn.*)' \
                 r'(.*LiveJournal.*)|(.*tiktok.*)'


class DistractorWindowCollector(BaseCollector):
    """
    Time spent in the distractors class﻿
    ---
    Number of 15 seconds intervals per minute (for example, 3 minutes  = 12 intervals)﻿
    """
    metric_name = "Distraction Class Window Activated (times)"

    APPS = (
        ('Teams', re.compile(r'.*| Microsoft Teams')),
        ('Telegram', re.compile(r'Telegram \(.*')),
        ('SkypeApp', re.compile(r'.*Skype.*')),
        ('OUTLOOK', re.compile(r'.*Outlook')),
        ('LockApp', re.compile(r'.*Windows Default Lock Screen.*')),
        ('Viber', re.compile(r'.*Viber.*﻿')),
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

    def _is_distractor_class(self, cur_win) -> bool:
        """ Check is distractor class """
        is_distractor_process, is_distractor_title = False, False
        res_apps = [i[0] in cur_win['app_name'] for i in self.APPS]
        try:
            ind = res_apps.index(True)
            is_distractor_process = True

            if self.APPS[ind][1].match(cur_win['title']):
                is_distractor_title = True

        except ValueError:
            pass

        logging.debug(f'is_distractor_process {is_distractor_process}')
        logging.debug(f'is_distractor_title {is_distractor_title}')
        return is_distractor_process and is_distractor_title

    def start_collect(self):
        # for threading need import wmi lib
        from flowd.utils.windows import get_current_active_window

        while self.is_run:
            current_window = get_current_active_window()
            logging.debug(f'Current window {current_window}')

            if self._is_distractor_class(current_window):
                self._second_count += 1

                if self._second_count > self.INTERVAL_SEC:
                    self._second_count = 0
                    self.count += 1
            else:
                # some useful and productive activity is happens
                self._second_count = 0

            logging.debug(f'Current state {self.metric_name} {self.count}')
            logging.debug(f'second_count {self._second_count}')

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
    win_collector = DistractorWindowCollector()
    win_collector.start_collect()
