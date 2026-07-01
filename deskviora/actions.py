"""
The action layer: every primitive the agent can actually perform on the
real screen. This is the desktop equivalent of Viora's content.js — instead
of DOM selectors, everything here works off screen coordinates and window
titles, since there's no DOM to query outside a browser.

Requires: pyautogui, pillow, mss, pygetwindow (all pure-Python, all
PyInstaller-friendly).
"""

import base64
import io
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Optional

import pyautogui
import mss
from PIL import Image, ImageChops

try:
    import pygetwindow as gw
except Exception:  # pygetwindow can be flaky outside Windows; degrade gracefully
    gw = None

pyautogui.FAILSAFE = True  # slam the mouse to a screen corner to abort, like Viora's stop button
pyautogui.PAUSE = 0.05


@dataclass
class ActionResult:
    success: bool
    message: str = ""
    data: Optional[dict] = None


# ---------------------------------------------------------------------------
# Screenshots
# ---------------------------------------------------------------------------

def screenshot_b64(region: Optional[tuple] = None, scale: float = 1.0) -> str:
    """Capture the screen (or a region) and return a data:image/png;base64 URL,
    same shape as what the extension sent to the model."""
    with mss.mss() as sct:
        monitor = sct.monitors[1] if region is None else {
            "left": region[0], "top": region[1], "width": region[2], "height": region[3]
        }
        raw = sct.grab(monitor)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
    if scale != 1.0:
        img = img.resize((int(img.width * scale), int(img.height * scale)))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _raw_screenshot(region: Optional[tuple] = None) -> Image.Image:
    with mss.mss() as sct:
        monitor = sct.monitors[1] if region is None else {
            "left": region[0], "top": region[1], "width": region[2], "height": region[3]
        }
        raw = sct.grab(monitor)
        return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")


# ---------------------------------------------------------------------------
# Mouse / keyboard primitives
# ---------------------------------------------------------------------------

def click(x: int, y: int, button: str = "left", clicks: int = 1) -> ActionResult:
    pyautogui.moveTo(x, y, duration=0.15)
    pyautogui.click(x, y, button=button, clicks=clicks)
    return ActionResult(True, f"Clicked ({x}, {y})")


def double_click(x: int, y: int) -> ActionResult:
    return click(x, y, clicks=2)


def right_click(x: int, y: int) -> ActionResult:
    return click(x, y, button="right")


def drag(x1: int, y1: int, x2: int, y2: int, duration: float = 0.4) -> ActionResult:
    pyautogui.moveTo(x1, y1, duration=0.15)
    pyautogui.dragTo(x2, y2, duration=duration, button="left")
    return ActionResult(True, f"Dragged ({x1},{y1}) -> ({x2},{y2})")


def type_text(text: str, interval: float = 0.02) -> ActionResult:
    # pyautogui.write mangles non-ASCII; fall back to clipboard+paste for those.
    try:
        text.encode("ascii")
        pyautogui.write(text, interval=interval)
    except UnicodeEncodeError:
        import pyperclip
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
    return ActionResult(True, f"Typed: {text[:60]}")


def press_key(key: str) -> ActionResult:
    pyautogui.press(key)
    return ActionResult(True, f"Pressed {key}")


def hotkey(*keys: str) -> ActionResult:
    pyautogui.hotkey(*keys)
    return ActionResult(True, f"Hotkey {'+'.join(keys)}")


def scroll(amount: int, x: Optional[int] = None, y: Optional[int] = None) -> ActionResult:
    if x is not None and y is not None:
        pyautogui.moveTo(x, y)
    pyautogui.scroll(amount)
    return ActionResult(True, f"Scrolled {amount}")


# ---------------------------------------------------------------------------
# Windows / apps
# ---------------------------------------------------------------------------

def launch_app(path_or_command: str) -> ActionResult:
    try:
        if sys.platform == "win32":
            import os
            os.startfile(path_or_command)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(path_or_command, shell=True)
        return ActionResult(True, f"Launched: {path_or_command}")
    except Exception as e:
        return ActionResult(False, f"Failed to launch {path_or_command}: {e}")


def list_windows() -> ActionResult:
    if gw is None:
        return ActionResult(False, "Window listing isn't available on this platform")
    titles = [t for t in gw.getAllTitles() if t.strip()]
    return ActionResult(True, f"{len(titles)} windows open", {"windows": titles})


def focus_window(title_substring: str) -> ActionResult:
    if gw is None:
        return ActionResult(False, "Window focusing isn't available on this platform")
    matches = [w for w in gw.getAllWindows() if title_substring.lower() in w.title.lower()]
    if not matches:
        return ActionResult(False, f"No open window matching '{title_substring}'")
    win = matches[0]
    try:
        if win.isMinimized:
            win.restore()
        win.activate()
        time.sleep(0.2)
        return ActionResult(True, f"Focused window: {win.title}")
    except Exception as e:
        return ActionResult(False, f"Couldn't focus '{win.title}': {e}")


# ---------------------------------------------------------------------------
# wait_for_idle — the screen-diff equivalent of the MutationObserver version
# ---------------------------------------------------------------------------

def wait_for_idle(region: Optional[tuple] = None, idle_ms: int = 900,
                   timeout_ms: int = 30000, min_wait_ms: int = 500,
                   diff_threshold: float = 0.4) -> ActionResult:
    """Poll screenshots of a region until consecutive frames stop changing.
    This is the desktop analog of content.js's MutationObserver-based
    wait_for_idle — there's no DOM to observe out here, so we watch pixels
    instead. Use this after sending a chat message, submitting a search, or
    launching something that takes a moment to render, before screenshotting
    or acting on what's shown."""
    start = time.time()
    time.sleep(min_wait_ms / 1000)

    last_img = _raw_screenshot(region)
    last_change = time.time()

    while (time.time() - start) * 1000 < timeout_ms:
        time.sleep(0.15)
        cur_img = _raw_screenshot(region)
        diff = ImageChops.difference(last_img.convert("L"), cur_img.convert("L"))
        # % of pixels that changed meaningfully
        hist = diff.histogram()
        changed = sum(hist[20:])  # ignore near-zero noise
        total = sum(hist)
        pct_changed = (changed / total * 100) if total else 0
        if pct_changed > diff_threshold:
            last_change = time.time()
        last_img = cur_img
        if (time.time() - last_change) * 1000 >= idle_ms:
            break

    elapsed_ms = (time.time() - start) * 1000
    timed_out = elapsed_ms >= timeout_ms
    return ActionResult(
        True,
        f"Screen settled after {int(elapsed_ms)}ms" if not timed_out
        else f"Waited {timeout_ms}ms but the screen was still changing — may still be loading",
        {"timedOut": timed_out},
    )


# ---------------------------------------------------------------------------
# Dispatch table — mirrors content.js's switch statement
# ---------------------------------------------------------------------------

def execute(action: dict) -> ActionResult:
    t = action.get("type")
    try:
        if t == "click":
            return click(action["x"], action["y"], action.get("button", "left"))
        if t == "double_click":
            return double_click(action["x"], action["y"])
        if t == "right_click":
            return right_click(action["x"], action["y"])
        if t == "drag":
            return drag(action["x1"], action["y1"], action["x2"], action["y2"])
        if t == "type":
            return type_text(action["text"])
        if t == "press_key":
            return press_key(action["key"])
        if t == "hotkey":
            return hotkey(*action["keys"])
        if t == "scroll":
            return scroll(action.get("amount", -500), action.get("x"), action.get("y"))
        if t == "launch_app":
            return launch_app(action["path"])
        if t == "focus_window":
            return focus_window(action["title"])
        if t == "list_windows":
            return list_windows()
        if t == "wait_for_idle":
            return wait_for_idle(
                region=action.get("region"),
                idle_ms=action.get("idleMs", 900),
                timeout_ms=action.get("timeout", 30000),
                min_wait_ms=action.get("minWait", 500),
            )
        if t == "wait":
            time.sleep(action.get("ms", 1000) / 1000)
            return ActionResult(True, "Waited")
        if t == "screenshot":
            return ActionResult(True, "Screenshot taken", {"screenshot": screenshot_b64()})
        return ActionResult(False, f"Unknown action type: {t}")
    except Exception as e:
        return ActionResult(False, f"{t} failed: {e}")
