from collections import defaultdict
import enum
from functools import lru_cache, partial
import logging
import math
import random
from datetime import datetime
from typing import Literal, cast
import tkinter as tk
from tkinter import Canvas
from PIL import Image, ImageDraw
import threading
import pystray


class ClockOrientation(enum.Enum):
    """
    Enum representing the orientation of a clock.
    Each member corresponds to a specific angle in degrees.
    """
    DEG_0 = 0
    DEG_30 = 30
    DEG_60 = 60
    DEG_90 = 90
    DEG_120 = 120
    DEG_150 = 150
    DEG_180 = 180
    DEG_210 = 210
    DEG_240 = 240
    DEG_270 = 270
    DEG_300 = 300
    DEG_330 = 330


ClockOrientations = tuple[ClockOrientation, ClockOrientation]
ClockLine = tuple[ClockOrientations, ClockOrientations, ClockOrientations, ClockOrientations]
ClockSquare = tuple[ClockLine, ClockLine, ClockLine, ClockLine, ClockLine, ClockLine]


ClockDirectionMap: dict[str, ClockOrientations] = defaultdict(
    lambda: (ClockOrientation.DEG_150, ClockOrientation.DEG_150), {
        '└': (ClockOrientation.DEG_0, ClockOrientation.DEG_270),
        '┌': (ClockOrientation.DEG_270, ClockOrientation.DEG_180),
        '┐': (ClockOrientation.DEG_180, ClockOrientation.DEG_90),
        '┘': (ClockOrientation.DEG_90, ClockOrientation.DEG_0),
        '-': (ClockOrientation.DEG_90, ClockOrientation.DEG_270),
        '|': (ClockOrientation.DEG_0, ClockOrientation.DEG_180),
    }
)


DigitRepresentationKey = Literal['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ' ', ':', '/']
DigitRepresentation: dict[str, tuple[str, str, str, str, str, str]] = {
    '0': (
          '┌--┐',
          '|┌┐|',
          '||||',
          '||||',
          '|└┘|',
          '└--┘'
    ),
    '1': (
          '┌-┐ ',
          '└┐| ',
          ' || ',
          ' || ',
          '┌┘└┐',
          '└--┘'
    ),
    '2': (
          '┌--┐',
          '└-┐|',
          '┌-┘|',
          '|┌-┘',
          '|└-┐',
          '└--┘'
    ),
    '3': (
          '┌--┐',
          '└-┐|',
          ' ┌┘|',
          ' └┐|',
          '┌-┘|',
          '└--┘'
    ),
    '4': (
          '┌┐┌┐',
          '||||',
          '|└┘|',
          '└-┐|',
          '  ||',
          '  └┘'
    ),
    '5': (
          '┌--┐',
          '|┌-┘',
          '|└-┐',
          '└-┐|',
          '┌-┘|',
          '└--┘'
    ),
    '6': (
          '┌--┐',
          '|┌-┘',
          '|└-┐',
          '|┌┐|',
          '|└┘|',
          '└--┘'
    ),
    '7': (
          '┌--┐',
          '└-┐|',
          '  ||',
          '  ||',
          '  ||',
          '  └┘'
    ),
    '8': (
          '┌--┐',
          '|┌┐|',
          '|└┘|',
          '|┌┐|',
          '|└┘|',
          '└--┘'
    ),
    '9': (
          '┌--┐',
          '|┌┐|',
          '|└┘|',
          '└-┐|',
          '┌-┘|',
          '└--┘'
    ),
    ' ': (
          '    ',
          '    ',
          '    ',
          '    ',
          '    ',
          '    '
    ),
    ':': (
          '    ',
          ' ┌┐ ',
          ' └┘ ',
          ' ┌┐ ',
          ' └┘ ',
          '    '
    ),
    '/': (
          '  ┌┐',
          ' ┌┘|',
          ' |┌┘',
          '┌┘| ',
          '|┌┘ ',
          '└┘  '
    ),
}


assert all(
    len(square) == 6 and all(len(row) == 4 for row in square) for square in DigitRepresentation.values()
), "All digit representations must be 6x4."


def new_random_color() -> tuple[int, int, int]:
    """
    Generate a new random RGB color.
    Returns:
        tuple: A tuple representing an RGB color in 255 format (R, G, B).
    """
    return tuple(random.randint(0, 255) for _ in range(3))  # type: ignore (Tuple size)


def current_time(date: bool = False, hours: bool = True) -> tuple[str, str, str] | tuple[str, str, str, str, str, str]:
    """
    Get the current time or date as a formatted string.
    Args:
        date (bool): If True, include the date (year, month, day).
        hours (bool): If True, include the time (hour, minute, second).
    Returns:
        tuple: A tuple containing the current date and/or time components.
    Raises:
        ValueError: If neither date nor hours is True.
    """
    now = datetime.now().strftime("%Y %m %d %H %M %S")
    all_parts = cast(tuple[str, str, str, str, str, str], tuple(now.split(" ")))
    if date and hours:
        return all_parts
    if date:
        return all_parts[:3]
    if hours:
        return all_parts[3:]
    raise ValueError("At least one of 'date' or 'hours' must be True.")


def clock_digit(digit: DigitRepresentationKey) -> ClockSquare:
    """
    Makes a list of orientations of clocks to know what clock to show in tkinter.
    Args:
        digit (str): A single character string representing a digit ('0'-'9').
    Returns:
        ClockSquare: A 6x4 tuple representing the orientations of clocks for the given digit
    """
    string = DigitRepresentation[digit]
    return tuple(
        tuple(
            ClockDirectionMap[char] for char in line
        ) for line in string
    )  # type: ignore[return-value] (incorrectly infers tuple size)


def full_clock_string(s: str) -> tuple[ClockSquare, ...]:
    """
    Converts a string of digits into a full clock representation.
    Args:
        s (str): A string containing digits and possibly other characters.
    Returns:
        tuple: A tuple of ClockSquare representations for each character in the string.
    """
    assert all(char in DigitRepresentation for char in s), "String contains invalid characters."
    return tuple(clock_digit(char) for char in cast(tuple[DigitRepresentationKey], s))


def full_clock_time(date: bool = False, hours: bool = True) -> tuple[ClockSquare, ...]:
    """
    Get the current time or date as a full clock representation.
    Args:
        date (bool): If True, include the date (year, month, day).
        hours (bool): If True, include the time (hour, minute, second).
    Returns:
        tuple: A tuple of ClockSquare representations for the current date and/or time.
    """
    current: tuple[str, ...] = current_time(date=date, hours=hours)
    if date:
        current = current[3:] + (" " if hours else "", "/".join(reversed(current[:3])))
    if hours:
        current = (":".join(current[:3]),) + current[3:]
    return full_clock_string("".join(current))


@lru_cache
def unpositionned_angle_calculation(angle: float, clock_size: float) -> tuple[float, float]:
    rad = math.radians(angle)
    x_end = clock_size / 2 + (clock_size / 2 - 3) * 0.8 * -1 * math.sin(rad)
    y_end = clock_size / 2 + (clock_size / 2 - 3) * 0.8 * -1 * math.cos(rad)
    logging.log(logging.INFO, f"Angle {angle}° (rad: {rad}) gives end coordinates ({x_end}, {y_end})")
    return round(x_end, 10), round(y_end, 10)


@lru_cache
def angle_calculation(angle: float, clock_size: float, x: float, y: float) -> tuple[float, float]:
    x_end, y_end = unpositionned_angle_calculation(angle, clock_size)
    return x + x_end, y + y_end


def create_image() -> Image.Image:
    """Create an icon image for the tray."""
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    center = (32, 32)
    radius = 28

    # Clock face
    draw.ellipse((center[0] - radius, center[1] - radius,
                  center[0] + radius, center[1] + radius),
                 fill="white", outline="black", width=3)

    # Hour marks
    for i in range(12):
        angle = math.radians(i * 30)
        x1 = center[0] + math.sin(angle) * (radius - 6)
        y1 = center[1] - math.cos(angle) * (radius - 6)
        x2 = center[0] + math.sin(angle) * (radius - 2)
        y2 = center[1] - math.cos(angle) * (radius - 2)
        draw.line((x1, y1, x2, y2), fill="black", width=2)

    def draw_hand(length: int, angle_deg: ClockOrientation, width: int = 3) -> None:
        angle = math.radians(angle_deg.value)
        x = center[0] + math.sin(angle) * length
        y = center[1] - math.cos(angle) * length
        draw.line((center, (x, y)), fill="black", width=width)

    draw_hand(14, ClockOrientation.DEG_300, 4)
    draw_hand(22, ClockOrientation.DEG_60, 2)

    return img


def on_quit(root: tk.Tk, icon: pystray.Icon, item: pystray.MenuItem | None):
    """Exit tray and close Tkinter."""
    icon.stop()
    root.destroy()


def show_window(root: tk.Tk, icon: pystray.Icon, item: pystray.MenuItem | None):
    """Show Tkinter window."""
    icon.stop()
    root.after(0, root.deiconify)


def toggle_window(root: tk.Tk, icon: pystray.Icon, item: pystray.MenuItem | None):
    """Toggle visibility of the Tkinter window."""
    if root.state() == 'withdrawn':
        root.deiconify()
    else:
        root.withdraw()
    icon.update_menu()


hours = True
date = False


def toggle_hours(icon: pystray.Icon, item: pystray.MenuItem):
    """Toggle hours display in the tray menu."""
    global hours
    hours = not hours
    icon.update_menu()


def toggle_date(icon: pystray.Icon, item: pystray.MenuItem):
    """Toggle date display in the tray menu."""
    global date
    date = not date
    icon.update_menu()


def print_to_tk(root: tk.Tk, canvas: tk.Canvas) -> None:
    """
    Print the current time or date using tkinter with clock representations.
    Args:
        root (tk.Tk): The tkinter root window where the clock will be displayed.
        canvas (tk.Canvas): The tkinter canvas to draw the clock on.
    Returns:
        None
    """
    try:
        color_value = new_random_color()
        color = "#%02x%02x%02x" % color_value
        is_dark = sum(color_value) / 3 < 128
        bg_color = "#eeeeee" if is_dark else "#111111"
        width = (640 if hours else 0) + (800 if date else 0) + (80 if hours and date else 0)
        canvas.delete("all")
        canvas.config(width=width, bg=bg_color)
        canvas.pack(fill=tk.BOTH, expand=True)
        clock_squares = full_clock_time(date=date, hours=hours)
        clock_size = round(width / len(clock_squares) / 4)
        padding = 0
        for idx, square in enumerate(clock_squares):
            for row_idx, line in enumerate(square):
                for col_idx, (ori1, ori2) in enumerate(line):
                    x = idx * (4 * (clock_size + padding)) + col_idx * (clock_size + padding) + padding
                    y = row_idx * (clock_size + padding) + padding
                    # Draw clock face
                    canvas.create_oval(
                        x, y,
                        x + clock_size, y + clock_size,
                        outline=bg_color.replace("e", "d").replace("1", "2"), width=2
                    )
                    # Draw clock hands
                    for angle in (ori1.value, ori2.value):
                        x_end, y_end = angle_calculation(angle, clock_size, x, y)
                        logging.log(logging.DEBUG, f"Drawing line from ({x}, {y}) to ({x_end}, {y_end})")
                        canvas.create_line(
                            x + clock_size / 2, y + clock_size / 2,
                            x_end, y_end,
                            fill=color, width=2
                        )
    except ValueError as e:
        if "At least one of 'date' or 'hours' must be True." not in str(e):
            raise
    root.after(1000, print_to_tk, root, canvas)


def make_menu(root: tk.Tk) -> pystray.Menu:
    return pystray.Menu(
        pystray.MenuItem(
            lambda _: "Show Window" if root.state() == 'withdrawn' else "Hide Window",
            partial(toggle_window, root)
        ),
        pystray.MenuItem(
            lambda _: "Show Hours" if not hours else "Hide Hours",
            toggle_hours
        ),
        pystray.MenuItem(
            lambda _: "Show Date" if not date else "Hide Date",
            toggle_date
        ),
        pystray.MenuItem("Quit", partial(on_quit, root))
    )


def setup_tray():
    """Create and run the system tray icon."""
    image = create_image()
    menu = make_menu(root)
    icon = pystray.Icon("Clock", image, "Clock", menu)
    icon.run()


if __name__ == "__main__":
    import shutil
    import os
    from sys import argv
    date = "--date" in argv
    hours = "--hours" in argv or not date

    try:
        appdata = os.getenv("APPDATA")
        if not appdata:
            raise EnvironmentError("APPDATA environment variable not found.")
    except EnvironmentError as e:
        home = os.path.expanduser("~")
        if home == "~":
            raise EnvironmentError("Cannot determine home directory.") from e
        appdata = os.path.join(home, ".appdata")
    log_dir = os.path.join(appdata, "PyClock")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "clock.log")

    if os.path.exists(log_file):
        shutil.move(log_file, log_file + ".old")
    logging.basicConfig(level=logging.INFO, filename=log_file,
                        filemode="x",
                        format="[%(levelname)s] %(asctime)s: %(message)s")
    logging.info(f"Starting clock with date={date} and hours={hours}")
    root = tk.Tk()
    root.title("Clock Display")
    canvas = Canvas(root, width=640 if hours else 0, height=120)
    root.after(1000, print_to_tk, root, canvas)
    root.resizable(False, False)
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.attributes("-toolwindow", True)
    root.withdraw()
    threading.Thread(target=setup_tray, daemon=True).start()
    root.mainloop()
