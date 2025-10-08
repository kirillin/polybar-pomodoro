#!/usr/bin/env python3
import os
import time
import sys
import notify2
import subprocess

from datetime import datetime
from enum import Enum

STATE_FILE = "/tmp/polybar_timer_state"
TIME_FILE = "/tmp/polybar_timer_time"
NOTIFY_INTERVAL = 10
CYCLE_MINUTES = 20

IDLE_COLOR = "#555555"
COLORS = {
    "0-20": "#A3BE8C",
    "20-40": "#ffBE8C",
    "40-60": "#ff9977",
    "60+": "#ff5533"
}

FILLED_CHAR = "▮"
EMPTY_CHAR = "▯"
PROGRESS_LENGTH = 0


class SystemSound(Enum):
    BELL = "bell"
    COMPLETE = "complete"
    MESSAGE = "message"
    DIALOG_INFO = "dialog-information"
    DIALOG_WARNING = "dialog-warning"
    DIALOG_ERROR = "dialog-error"


def play_sound(sound: SystemSound):
    try:
        subprocess.Popen(["canberra-gtk-play", "-i", sound.value])
    except FileNotFoundError:
        subprocess.Popen([
            "paplay",
            "/usr/share/sounds/freedesktop/stereo/complete.oga"
        ])

def read_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return f.read().strip()
    return "idle"

def write_state(state):
    with open(STATE_FILE, 'w') as f:
        f.write(state)

def read_time():
    if os.path.exists(TIME_FILE):
        with open(TIME_FILE, 'r') as f:
            return int(f.read().strip())
    return 0

def write_time(seconds):
    with open(TIME_FILE, 'w') as f:
        f.write(str(seconds))

def format_time(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def get_color(minutes):
    if minutes < 20:
        return COLORS["0-20"]
    elif 20 <= minutes < 40:
        return COLORS["20-40"]
    elif 40 <= minutes < 60:
        return COLORS["40-60"]
    else:
        return COLORS["60+"]

def progress_animation(seconds):
    minutes = seconds // 60
    cycle_progress = minutes % CYCLE_MINUTES
    filled = int((cycle_progress / CYCLE_MINUTES) * PROGRESS_LENGTH)
    progress_bar = (FILLED_CHAR * filled) + (EMPTY_CHAR * (PROGRESS_LENGTH - filled))
    return progress_bar

def send_notification(seconds):
    notify2.init("Polybar Timer")
    msg = f"Таймер: {format_time(seconds)}"
    notify2.Notification("Timer", msg).show()

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "toggle":
            state = read_state()
            if state == "running":
                write_state("paused")
            else:
                play_sound(SystemSound.BELL)
                write_state("running")
                if read_state() == "idle":
                    write_time(0)
        elif sys.argv[1] == "reset":
            write_time(0)
            write_state("idle")
            play_sound(SystemSound.DIALOG_WARNING)
        return

    state = read_state()
    seconds = read_time()
    
    if state == "running":
        seconds += 1
        write_time(seconds)
        if seconds % (NOTIFY_INTERVAL * 60) == 0:
            send_notification(seconds)
            play_sound(SystemSound.COMPLETE)
    
    minutes = seconds // 60
    if state == "running":
        color = get_color(minutes)
    else:
        color = IDLE_COLOR
    progress = progress_animation(seconds)
    time_str = format_time(seconds)

    print(f"%{{F{color}}}{progress}{time_str}%{{F-}}")

if __name__ == "__main__":
    main()
