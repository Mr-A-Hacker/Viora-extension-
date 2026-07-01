# DeskViora

A desktop port of Viora's agent loop — instead of controlling a browser tab
through a Chrome extension, this controls your *whole screen*: any app, any
window, via real mouse/keyboard input and screenshots.

## What's here

- `actions.py` — the action layer (click, type, drag, scroll, launch apps,
  focus windows, wait_for_idle via screen-diff). Desktop equivalent of
  Viora's `content.js`.
- `agent.py` — the LLM loop: system prompt, planning, execution, and the
  double-check-until-actually-done verification loop with the same dynamic
  round caps and bulk/"all"-task handling as Viora. Desktop equivalent of
  `sidepanel.js`.
- `main.py` — a minimal Tkinter GUI (goal box, run/stop, settings). You can
  swap this for something fancier later without touching the agent logic.
- `config.py` — stores your API key locally.
- `build.spec` — PyInstaller spec to produce a single `DeskViora.exe`.

## Setup

```
pip install -r requirements.txt
python main.py
```

On first run it'll prompt for an API key. This is wired to OpenRouter by
default (`config.py` → `api_base`), so any vision-capable model works —
just get a key at https://openrouter.ai and paste it in. If you'd rather
call the Anthropic or OpenAI API directly, change `api_base` and the
request body in `agent.py`'s `call_llm()` to match their format — it's a
small change, the rest of the code doesn't care which backend answers.

## Building the .exe

**Important: PyInstaller builds for the OS it runs on.** I wrote and
syntax-checked all of this code here, but I can't produce a real Windows
`.exe` binary from this Linux environment — PyInstaller has to actually run
on Windows to produce a Windows executable.

### Option A — no Windows machine needed (recommended)
This repo includes `.github/workflows/build-exe.yml`, which builds the
`.exe` for you on GitHub's free Windows runner:
1. Create a new GitHub repo and push this folder to it (or use GitHub's
   "upload files" web UI if you don't want to use git directly).
2. Go to the repo's **Actions** tab. The workflow runs automatically on
   push — or click **Run workflow** to trigger it manually.
3. When it finishes (a couple of minutes), open the completed run and
   download the **DeskViora-windows** artifact — that's your `.exe`, built
   on a real Windows machine, ready to run.

### Option B — you have access to a Windows machine/VM
1. Copy this folder over.
2. `pip install -r requirements.txt`
3. `pyinstaller build.spec`
4. Your executable is at `dist/DeskViora.exe` — a single file, no install
   needed, no console window behind the GUI.

## Safety notes — read this before running it unattended

This app can genuinely do anything you could do with your mouse and
keyboard — click through any app, type into anything, close windows, launch
programs. A few things worth knowing:

- **PyAutoGUI's failsafe is on** — slam your mouse to any screen corner and
  it aborts immediately mid-action. Good habit to know before you let it run
  a long task.
- **It has no concept of "this app is dangerous, this one isn't."** It'll
  click Delete/Send/Submit in whatever's on screen, including things that
  aren't the browser. Don't leave sensitive windows (banking, admin panels)
  open on screen during a run unless the task genuinely needs them.
- **Unlike the browser extension, there's no DOM to read** — it's working
  purely from pixels, so it's more error-prone on cluttered screens or tiny
  UI elements. Bigger, cleaner target windows work better.
- Consider running it in a **separate Windows user account or VM** if
  you're going to give it long, unattended, multi-round tasks — same logic
  as not giving a new employee your admin password on day one.

## What's simplified vs. the full Viora feature set

To keep this a working first version rather than a half-finished giant one,
I left out a few things from the browser extension that don't have a clean
desktop equivalent yet — happy to add any of these if you want them:

- Undo (the extension can revert a step; there's no generic "undo a click"
  on the desktop)
- The 100+ selector-fallback strategy engine (there's no selector to fall
  back on — desktop clicking is coordinate-based)
- OCR-based text reading (right now it relies on the vision model reading
  the screenshot directly, which works but is slower/costlier than
  extracting real text where possible — I can wire in an OCR pass for
  faster/cheaper text-heavy tasks)
- The finish-alarm/notification toggle from Viora v4.3
