import curses
import json
import os
import time
from datetime import datetime

LOOT_LOG_PATH = "loot_log.json"


def load_loot():
    if not os.path.exists(LOOT_LOG_PATH):
        return []
    with open(LOOT_LOG_PATH, "r") as f:
        return json.load(f)


def draw_ui(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    h, w = stdscr.getmaxyx()
    frame = 0

    while True:
        key = stdscr.getch()
        if key == ord('q') or key == 27:
            break

        stdscr.clear()
        stdscr.addstr(0, 0, "[ SESSION_EXFIL_OMEGA - LIVE DASHBOARD ]", curses.A_BOLD)
        stdscr.addstr(1, 0, "  press 'q' to exit", curses.A_DIM)
        stdscr.addstr(3, 2, f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        stdscr.addstr(4, 2, f"Frame: {frame}")
        stdscr.addstr(5, 2, f"Loot Entries: {len(load_loot())}")
        stdscr.addstr(7, 0, "-" * (w - 1))

        loot = load_loot()
        for i, item in enumerate(loot[-10:]):
            stdscr.addstr(9 + i, 2, f"{item['timestamp']} :: {item['type']}")

        stdscr.refresh()
        time.sleep(1)
        frame += 1


def main():
    curses.wrapper(draw_ui)


if __name__ == "__main__":
    main()
