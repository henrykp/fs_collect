# pip install keyboard
# git clone https://github.com/boppreh/keyboard

import keyboard

import logging
import threading
import time
from flowd.metrics import BaseCollector

MODIFIERS = keyboard.all_modifiers

POPULAR_SHORTCUTS = [
    # save
    "ctrl+s",
    # copy
    "ctrl+c",
    "ctrl+insert",
    # paste
    "ctrl+v",
    "windows+v",
    "shift+insert",
    # cut
    "ctrl+x",
    "shift+delete"
]

CODE_ASSIST_SHORTCUTS = [
    # code assist
    "ctrl+space"
]

ALL_SHORTCUTS = POPULAR_SHORTCUTS + CODE_ASSIST_SHORTCUTS


class PopularShortcutsCollector(BaseCollector):
    """
    Popular IDE shortcuts used﻿.

    The shortcuts must be in the format `ctrl+shift+a, s`. This would trigger when the user holds
    ctrl, shift and "a" at once, releases, and then presses "s". To represent
    literal commas, pluses, and spaces, use their names ('comma', 'plus',
    'space').
    ---------------
    Number per minute﻿
    """
    metric_name = "popular_shortcuts"

    def __init__(self) -> None:
        self.count = 0  # for interval

    def shortcut_pressed(self):
        self.count += 1

    def stop_collect(self) -> None:
        return

    def start_collect(self) -> None:
        for h in POPULAR_SHORTCUTS:
            keyboard.add_hotkey(hotkey=h,
                                callback=self.shortcut_pressed,
                                args=(),
                                timeout=0.1)

    def get_current_state(self) -> tuple:
        return self.metric_name, self.count

    def cleanup(self) -> None:
        self.count = 0


class ShortcutsCollector(BaseCollector):
    """
    Keyboard shortcuts used﻿. Shortcuts are any key combinations with modifiers (Ctrl, Alt, Shift),
    except popular IDE shortcuts
    ---------------
    Number per minute﻿
    """
    metric_name = "all_shortcuts"

    def __init__(self) -> None:
        self.count = 0  # for interval

    def stop_collect(self) -> None:
        return

    def start_collect(self) -> None:
        keyboard.on_press(self.key_pressed)

    def get_current_state(self) -> tuple:
        return self.metric_name, self.count

    def cleanup(self) -> None:
        self.count = 0

    def key_pressed(self, e) -> None:
        if keyboard.is_modifier(e.scan_code):
            return
        hk = keyboard.get_hotkey_name()
        for m in MODIFIERS:
            if keyboard.is_pressed(m) and not keyboard.is_modifier(hk) and hk not in ALL_SHORTCUTS:
                self.count += 1
                return


class CodeAssistCollector(BaseCollector):
    """
    Code assist activated﻿ Ctrl+Space﻿
    ---------------
    Number per minute﻿
    """
    metric_name = "code_assist_shortcuts"

    def __init__(self) -> None:
        self.count = 0  # for interval

    def stop_collect(self) -> None:
        return

    def start_collect(self) -> None:
        keyboard.on_press(self.key_pressed)

    def get_current_state(self) -> tuple:
        return self.metric_name, self.count

    def cleanup(self) -> None:
        self.count = 0

    def key_pressed(self, e) -> None:
        if keyboard.get_hotkey_name() in CODE_ASSIST_SHORTCUTS:
            self.count += 1


class FullLinesCollector(BaseCollector):
    """
    Few regular characters + Enter﻿
    ---------------
    Number per minute﻿
    """
    metric_name = "full_lines"

    def __init__(self) -> None:
        self.count = 0  # for interval

    def line_entered(self):
        self.count += 1

    def stop_collect(self) -> None:
        return

    # Just a dynamic object to store attributes for the closures.
    class _State(object):
        pass

    def start_collect(self) -> None:
        state = self._State()
        state.current = ''
        state.time = -1
        timeout = 5
        triggers = ["enter"]

        def handler(event) -> None:
            name = event.name
            if event.event_type == keyboard.KEY_UP or name in keyboard.all_modifiers:
                return

            if timeout and event.time - state.time > timeout:
                state.current = ''
            state.time = event.time

            if name in triggers:
                self.line_entered()
                state.current = ''
            elif len(name) > 1:
                state.current = ''
            else:
                state.current += name
        keyboard.hook(handler)

    def get_current_state(self) -> tuple:
        return self.metric_name, self.count

    def cleanup(self) -> None:
        self.count = 0


if __name__ == '__main__':
    # Example of usage
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)-8s %(message)s")
    collector = FullLinesCollector()
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
