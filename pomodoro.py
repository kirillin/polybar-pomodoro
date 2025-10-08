#!/usr/bin/env python3
import os
import time
import sys
import notify2
import subprocess

from enum import Enum

STATE_FILE = "/tmp/polybar_pomodoro_state"
TIME_FILE = "/tmp/polybar_pomodoro_time"
POMODORO_FILE = "/tmp/polybar_pomodoro_count"
NOTIFY_INTERVAL = 5
POMODORO_MINUTES = 25
BREAK_MINUTES = 5
LONG_BREAK_MINUTES = 15
POMODOROS_PER_LONG_BREAK = 4

IDLE_COLOR = "#555555"
POMODORO_COLOR = "#D08770"
BREAK_COLOR = "#A3BE8C"
LONG_BREAK_COLOR = "#81A1C1"
COMPLETED_COLOR = "#ff5555"

TOMATO_SYMBOLS = ["○", "◔", "◑", "◕", "●"]
TOMATO_EMPTY = "○"
TOMATO_FULL = "●"

class SystemSound(Enum):
    BELL = "bell"
    COMPLETE = "complete"
    MESSAGE = "message"
    DIALOG_INFO = "dialog-information"
    DIALOG_WARNING = "dialog-warning"
    DIALOG_ERROR = "dialog-error"

def play_sound(sound: SystemSound, times=1):
    try:
        for _ in range(times):
            subprocess.Popen(["canberra-gtk-play", "-i", sound.value])
            time.sleep(0.2)
    except FileNotFoundError:
        for _ in range(times):
            subprocess.Popen([
                "paplay",
                "/usr/share/sounds/freedesktop/stereo/complete.oga"
            ])
            time.sleep(0.2)

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

def read_pomodoro_count():
    if os.path.exists(POMODORO_FILE):
        with open(POMODORO_FILE, 'r') as f:
            return int(f.read().strip())
    return 0

def write_pomodoro_count(count):
    with open(POMODORO_FILE, 'w') as f:
        f.write(str(count))

def format_time(seconds):
    m = seconds // 60
    s = seconds % 60
    return f"{m:02d}:{s:02d}"

def get_current_period_type(pomodoro_count):
    if pomodoro_count % 2 == 0:
        return "pomodoro"
    else:
        if (pomodoro_count + 1) % (POMODOROS_PER_LONG_BREAK * 2) == 0:
            return "long_break"
        return "short_break"

def get_period_duration(period_type):
    if period_type == "pomodoro":
        return POMODORO_MINUTES * 60
    elif period_type == "long_break":
        return LONG_BREAK_MINUTES * 60
    else:
        return BREAK_MINUTES * 60

def get_period_color(period_type):
    if period_type == "pomodoro":
        return POMODORO_COLOR
    elif period_type == "long_break":
        return LONG_BREAK_COLOR
    else:
        return BREAK_COLOR

def get_tomato_symbol(progress):
    index = min(int(progress * (len(TOMATO_SYMBOLS) - 1)), len(TOMATO_SYMBOLS) - 1)
    return TOMATO_SYMBOLS[index]

def get_completed_tomatoes_display(pomodoro_count):
    completed_pomodoros = pomodoro_count // 2
    return TOMATO_FULL * completed_pomodoros

def send_notification(message):
    notify2.init("Polybar Pomodoro")
    notify2.Notification("Pomodoro Timer", message).show()

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "toggle":
            state = read_state()
            if state == "running":
                write_state("paused")
                message = "Pause work or break!"
            else:
                play_sound(SystemSound.BELL)
                write_state("running")
                if state == "idle":
                    write_time(0)
                    write_pomodoro_count(0)
                message = "Start work!"
        elif sys.argv[1] == "reset":
            write_time(0)
            write_state("idle")
            write_pomodoro_count(0)
            play_sound(SystemSound.DIALOG_WARNING, 3)
            message = "Reset!"
            send_notification("RESET clicked")
        elif sys.argv[1] == "skip":
            pomodoro_count = read_pomodoro_count()
            current_period_type = get_current_period_type(pomodoro_count)
            write_pomodoro_count(pomodoro_count + 1)
            write_time(0)
            play_sound(SystemSound.DIALOG_INFO)
            message = "Break skipped!"
        
        send_notification(message)
        return

    state = read_state()
    seconds = read_time()
    pomodoro_count = read_pomodoro_count()
    
    current_period_type = get_current_period_type(pomodoro_count)
    period_duration = get_period_duration(current_period_type)
    
    if state == "running":
        seconds += 1
        write_time(seconds)
        
        if seconds >= period_duration:
            play_sound(SystemSound.COMPLETE, 5)
            
            if current_period_type == "pomodoro":
                message = "Time to break. Ask yourself: 'Are you ready spend next pomodoro to THIS task?'"
                pomodoro_count += 1
            else:
                message = "Time to work."
                pomodoro_count += 1
            
            write_pomodoro_count(pomodoro_count)
            write_time(0)
            send_notification(message)
        
        elif seconds % (NOTIFY_INTERVAL * 60) == 0:
            remaining = period_duration - seconds
            message = f"{'Pomodoro' if current_period_type == 'pomodoro' else 'Break'}: {format_time(remaining)} left"
            send_notification(message)
    
    completed_tomatoes = get_completed_tomatoes_display(pomodoro_count)
    
    if state == "running":
        completed_tomatos_color = COMPLETED_COLOR
        color = get_period_color(current_period_type)
        progress = min(seconds / period_duration, 1.0)
        current_tomato = get_tomato_symbol(progress)
    else:
        color = completed_tomatos_color = IDLE_COLOR
        current_tomato = TOMATO_EMPTY
    
    time_str = format_time(seconds)
    
    if state == "running":
        if len(completed_tomatoes) > 0:
            display_str = f"%{{F{completed_tomatos_color}}}{completed_tomatoes}%{{F-}} %{{F{color}}}{current_tomato} {time_str}%{{F-}}"
        else:
            display_str = f"%{{F{color}}}{current_tomato} {time_str}%{{F-}}"
    else:
        display_str = f"%{{F{color}}}{time_str}%{{F-}}"

    print(display_str)


if __name__ == "__main__":
    main()