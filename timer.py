#!/usr/bin/env python3
import os
import time
import sys
import notify2
import subprocess
import threading
import atexit

from datetime import datetime
from enum import Enum

STATE_FILE = "/tmp/reverse_stopwatch_timer_state"
TIME_FILE = "/tmp/reverse_stopwatch_timer_time"
LAST_UPDATE_FILE = "/tmp/reverse_stopwatch_timer_last_update"

IDLE_COLOR = "#999999"
RUNNING_COLOR = "#87CEEB"
ALERT_COLOR = "#FF0000"

CYCLE_MINUTES = 20
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
        subprocess.Popen(["canberra-gtk-play", "-i", sound.value], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        try:
            subprocess.Popen([
                "paplay",
                "/usr/share/sounds/freedesktop/stereo/complete.oga"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            pass

def read_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                content = f.read().strip()
                if content in ["idle", "running"]:
                    return content
                return "idle"
        except (ValueError, IOError, OSError):
            return "idle"
    return "idle"

def write_state(state):
    try:
        with open(STATE_FILE, 'w') as f:
            f.write(state)
    except (IOError, OSError):
        pass

def read_time():
    if os.path.exists(TIME_FILE):
        try:
            with open(TIME_FILE, 'r') as f:
                content = f.read().strip()
                if content:
                    value = int(content)
                    return max(0, value)
                return 0
        except (ValueError, IOError, OSError):
            return 0
    return 0

def write_time(seconds):
    try:
        with open(TIME_FILE, 'w') as f:
            f.write(str(max(0, seconds)))
    except (IOError, OSError):
        pass

def read_last_update():
    if os.path.exists(LAST_UPDATE_FILE):
        try:
            with open(LAST_UPDATE_FILE, 'r') as f:
                content = f.read().strip()
                if content:
                    return float(content)
                return time.time()
        except (ValueError, IOError, OSError):
            return time.time()
    return time.time()

def write_last_update(timestamp):
    try:
        with open(LAST_UPDATE_FILE, 'w') as f:
            f.write(str(timestamp))
    except (IOError, OSError):
        pass

def format_time(seconds):
    if seconds < 0:
        seconds = 0
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def progress_animation(seconds):
    if seconds <= 0:
        return EMPTY_CHAR * PROGRESS_LENGTH
    
    minutes = seconds // 60
    total_minutes = minutes
    cycle_progress = total_minutes % CYCLE_MINUTES
    filled = int((cycle_progress / CYCLE_MINUTES) * PROGRESS_LENGTH)
    progress_bar = (FILLED_CHAR * filled) + (EMPTY_CHAR * (PROGRESS_LENGTH - filled))
    return progress_bar

def send_notification(seconds):
    try:
        notify2.init("Polybar Timer")
        msg = f"Таймер закончил отсчет!"
        notify2.Notification("Timer", msg).show()
    except:
        pass

def update_timer():
    while True:
        time.sleep(0.5)
        
        state = read_state()
        if state != "running":
            continue
            
        current_time = time.time()
        last_update = read_last_update()
        elapsed = current_time - last_update
        
        if elapsed >= 1.0:
            seconds = read_time()
            if seconds > 0:
                new_seconds = max(0, seconds - int(elapsed))
                write_time(new_seconds)
                write_last_update(current_time)
                
                if new_seconds == 0 and seconds > 0:
                    write_state("idle")
                    send_notification(0)
                    play_sound(SystemSound.DIALOG_ERROR)
            else:
                if seconds <= 0:
                    write_state("idle")
                    write_last_update(current_time)

def main():
    if len(sys.argv) > 1:
        current_time = time.time()
        
        if sys.argv[1] == "start":
            seconds = read_time()
            if seconds > 0:
                write_state("running")
                write_last_update(current_time)
                play_sound(SystemSound.BELL)
                
        elif sys.argv[1] == "add":
            current_seconds = read_time()
            new_time = current_seconds + 600
            write_time(new_time)
            if read_state() == "running":
                write_last_update(current_time)
            play_sound(SystemSound.MESSAGE)
            
        elif sys.argv[1] == "reset":
            write_time(0)
            write_state("idle")
            write_last_update(current_time)
            play_sound(SystemSound.DIALOG_WARNING)
        return

    state = read_state()
    
    if state == "running":
        current_time = time.time()
        last_update = read_last_update()
        elapsed = int(current_time - last_update)
        
        if elapsed >= 1:
            seconds = read_time()
            if seconds > 0:
                new_seconds = max(0, seconds - elapsed)
                write_time(new_seconds)
                write_last_update(current_time)
                
                if new_seconds == 0:
                    write_state("idle")
    
    seconds = read_time()
    
    if seconds == 0 and state == "idle":
        current_second = int(time.time())
        if current_second % 2 == 0:
            color = ALERT_COLOR
        else:
            color = RUNNING_COLOR
    elif state == "running":
        color = RUNNING_COLOR
    else:
        color = IDLE_COLOR
    
    progress = progress_animation(seconds)
    time_str = format_time(seconds)
    
    print(f"%{{F{color}}}{progress}{time_str}%{{F-}}")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        if not os.path.exists(LAST_UPDATE_FILE):
            write_last_update(time.time())
        
        timer_thread = threading.Thread(target=update_timer, daemon=True)
        timer_thread.start()
    
    main()