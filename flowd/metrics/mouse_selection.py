import logging
import threading
import time
import mouse
from mouse import ButtonEvent, MoveEvent

from flowd.metrics import BaseCollector


class MouseUsedSelectionCollector(BaseCollector):
    """
    Mouse used for selection﻿ (Press -> Drag -> Release)
    ---
    Number per minute﻿ (Max duration for selection is 10 sec)
    """
    metric_name = "mouse_used_selection"

    LEFT_BUTTON = 'left'
    EVENT_TYPE_PRESSED = 'down'
    EVENT_TYPE_RELEASED = 'up'

    MOVING_MAX_DURATION_SEC = 10

    def __init__(self) -> None:
        self.count = 0

        self._pressed_event = None
        self._move_event = None

    def stop_collect(self) -> None:
        mouse.unhook(self.mouse_selection_callback)

    def mouse_selection_callback(self, event):
        if isinstance(event, ButtonEvent) and event.button == self.LEFT_BUTTON:
            if event.event_type == self.EVENT_TYPE_PRESSED:
                # start selection
                self._pressed_event = event
            if event.event_type == self.EVENT_TYPE_RELEASED:
                # end selection
                if self._pressed_event and self._move_event:
                    # if movement was between press and release
                    if self._pressed_event.time <= self._move_event.time <= event.time:
                        selection_sec = event.time - self._pressed_event.time
                        if selection_sec <= self.MOVING_MAX_DURATION_SEC:
                            self.count += 1
                            logging.debug(self.count)

                # clean up events
                self._pressed_event = None
                self._move_event = None
        if isinstance(event, MoveEvent):
            # moving selection
            self._move_event = event

    def start_collect(self) -> None:
        # set callback on all mouse activities
        mouse.hook(self.mouse_selection_callback)

    def get_current_state(self) -> tuple:
        return self.metric_name, self.count

    def cleanup(self) -> None:
        self.count = 0


if __name__ == '__main__':
    # Example of usage
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)-8s %(message)s")
    collector = MouseUsedSelectionCollector()
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
