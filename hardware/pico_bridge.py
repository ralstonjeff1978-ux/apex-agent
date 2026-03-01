"""
Pico Bridge — Controller
========================
Gets questions (clipboard or phone photo), generates AI answers,
sends them to the Pico to type on screen with human-like behavior.

LAUNCH MODES:
  Mode 1 — PC Terminal : type commands in terminal
  Mode 2 — Phone Mode  : browser on phone

COMMANDS:
  !clip_answer   — copy question text, this grabs it and types the answer
  !answer [text] — send any text directly to Pico right now
  !type_test     — test that Pico is connected and typing
  !photo         — (phone mode only) upload a photo of the question
  !status        — show current question and last answer
  !quit          — exit
"""

import sys
import socket
import threading
import logging
import requests
import base64
from pathlib import Path
from colorama import Fore, Style, init

import yaml

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

init(autoreset=True)

log = logging.getLogger("apex.pico_bridge")

_CONFIG_PATH = Path(__file__).parent.parent / "core" / "config.yaml"


def _load_config() -> dict:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _get_pico_port() -> str:
    cfg = _load_config()
    return cfg.get("hardware", {}).get("pico_port", "COM4")


def _get_pico_baud() -> int:
    cfg = _load_config()
    return int(cfg.get("hardware", {}).get("pico_baud", 115200))


def _get_flask_port() -> int:
    cfg = _load_config()
    return int(cfg.get("hardware", {}).get("pico_flask_port", 5001))


def _get_ollama_api() -> str:
    cfg = _load_config()
    return cfg.get("llm", {}).get("ollama_api", "http://localhost:11434/api/generate")


def _get_brain_model() -> str:
    cfg = _load_config()
    return cfg.get("llm", {}).get("brain_model", "deepseek-v3.1:671b-cloud")


def _get_coder_model() -> str:
    cfg = _load_config()
    return cfg.get("llm", {}).get("coder_model", "qwen3-coder:480b-cloud")


def _get_timeout() -> int:
    cfg = _load_config()
    return int(cfg.get("llm", {}).get("timeout", 600))


# ── CLIPBOARD (silent — no flash window) ─────────────────────────────────────
def _clipboard_paste():
    """Read clipboard using Windows API directly — no pyperclip flash window."""
    try:
        import ctypes
        import ctypes.wintypes
        CF_UNICODETEXT = 13
        ctypes.windll.user32.OpenClipboard(0)
        h = ctypes.windll.user32.GetClipboardData(CF_UNICODETEXT)
        if not h:
            ctypes.windll.user32.CloseClipboard()
            return ""
        ptr = ctypes.windll.kernel32.GlobalLock(h)
        text = ctypes.wstring_at(ptr)
        ctypes.windll.kernel32.GlobalUnlock(h)
        ctypes.windll.user32.CloseClipboard()
        return text
    except Exception:
        try:
            import pyperclip
            return pyperclip.paste()
        except Exception:
            return ""


def _clipboard_copy(text):
    """Write text to PC clipboard using Windows API — no pyperclip flash window."""
    try:
        import ctypes
        CF_UNICODETEXT = 13
        GMEM_MOVEABLE  = 0x0002
        ctypes.windll.user32.OpenClipboard(0)
        ctypes.windll.user32.EmptyClipboard()
        encoded = (text + "\0").encode("utf-16-le")
        h = ctypes.windll.kernel32.GlobalAlloc(GMEM_MOVEABLE, len(encoded))
        ptr = ctypes.windll.kernel32.GlobalLock(h)
        ctypes.memmove(ptr, encoded, len(encoded))
        ctypes.windll.kernel32.GlobalUnlock(h)
        ctypes.windll.user32.SetClipboardData(CF_UNICODETEXT, h)
        ctypes.windll.user32.CloseClipboard()
        return True
    except Exception:
        try:
            import pyperclip
            pyperclip.copy(text)
            return True
        except Exception:
            return False


state = {
    "last_question": "",
    "last_answer":   "",
    "review_mode":   False,
    "pico_busy":     False,
    "typing_speed":  "normal",
    "code_mode":     False,
}

# ── PICO SERIAL ───────────────────────────────────────────────────────────────
def _pico_worker(text):
    """Send in small chunks. Newlines become ~~NL~~ so Pico presses Enter correctly."""
    import time
    import random
    ser = None
    SPEEDS = {
        "slow":   {"chunk": 12, "delay": 0.28, "variance": 0.18},
        "normal": {"chunk": 24, "delay": 0.13, "variance": 0.07},
        "fast":   {"chunk": 48, "delay": 0.06, "variance": 0.03},
    }
    profile    = SPEEDS.get(state.get("typing_speed", "normal"), SPEEDS["normal"])
    CHUNK_SIZE = profile["chunk"]
    BASE_DELAY = profile["delay"]
    VARIANCE   = profile["variance"]
    try:
        if not SERIAL_AVAILABLE:
            log.error("pyserial not installed. Run: pip install pyserial")
            state["pico_busy"] = False
            return
        text_safe = text.replace("\n", "~~NL~~").replace("\r", "")
        ser = serial.Serial()
        ser.port          = _get_pico_port()
        ser.baudrate      = _get_pico_baud()
        ser.timeout       = 2
        ser.write_timeout = 15
        ser.dtr           = False
        ser.open()
        time.sleep(0.1)
        data = (text_safe + "\n").encode("utf-8")
        for i in range(0, len(data), CHUNK_SIZE):
            chunk = data[i:i + CHUNK_SIZE]
            ser.write(chunk)
            ser.flush()
            time.sleep(BASE_DELAY + random.uniform(0, VARIANCE))
        time.sleep(0.2)
    except Exception as e:
        log.error("Pico serial error: %s", e)
    finally:
        state["pico_busy"] = False
        try:
            if ser and ser.is_open:
                ser.close()
        except Exception:
            pass


def send_to_pico(text):
    if not text:
        return "[ERROR] No text to send"
    state["last_question"] = ""
    if state.get("code_mode"):
        ok = _clipboard_copy(text)
        if not ok:
            return "[ERROR] Could not write to PC clipboard"
        threading.Thread(target=_pico_worker, args=("~~PASTE~~",), daemon=True).start()
        return "[CODE MODE] Text on clipboard — Pico pressing Ctrl+V now"
    text = text.replace("\n", "~~NL~~").replace("\r", "")
    threading.Thread(target=_pico_worker, args=(text,), daemon=True).start()
    return "[SENT TO PICO] %d chars on the way" % len(text)


# ── AI ANSWER ─────────────────────────────────────────────────────────────────
def generate_answer(question_text):
    """Pick the best model for the question type and get a clean answer."""
    try:
        q = question_text.lower()
        wants_code = any(k in q for k in [
            "write", "implement", "code", "function", "program", "script",
            "translate", "convert", "build", "create a"
        ])

        if any(k in q for k in [
            "python", "java", "javascript", "html", "css", "sql",
            "docker", "git", "react", "typescript", "go", "swift",
            "c++", "c#", "dart", "verilog", "bash", "linux", "network",
            "tcp", "udp", "arp", "dns", "exploit", "payload", "nmap",
            "write", "implement", "function", "algorithm", "code"
        ]):
            model = _get_coder_model()
            if wants_code:
                prefix = (
                    "You are answering a coding challenge. Respond with ONLY the working code "
                    "— no explanation, no markdown, no bullet points, no backticks. "
                    "Just the raw code that can be typed directly into an editor."
                )
            else:
                prefix = "Give a concise, accurate technical answer. No markdown, no bullet points, plain sentences only:"
        else:
            model  = _get_brain_model()
            prefix = "Give a clear, accurate answer in plain sentences. No markdown, no bullet points:"

        prompt = "%s\n\nQuestion: %s\n\nAnswer:" % (prefix, question_text)
        r = requests.post(
            _get_ollama_api(),
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=_get_timeout()
        )
        r.raise_for_status()
        answer = r.json().get("response", "").strip()
        answer = answer.replace("**", "").replace("*", "").replace("`", "").replace("#", "")
        answer = answer.replace("\n", " ").replace("\r", " ")
        while "  " in answer:
            answer = answer.replace("  ", " ")
        state["last_answer"] = answer
        return answer
    except Exception as e:
        return "[ANSWER ERROR] %s" % str(e)


def analyze_photo_and_answer(image_bytes):
    """Send photo directly to model — answer what you see, no extraction step."""
    try:
        b64 = base64.b64encode(image_bytes).decode("utf-8")

        prompt = (
            "Look at this image. There is a coding challenge or technical question visible.\n"
            "Answer it directly. If it asks you to write code, return ONLY the raw working code "
            "with no markdown, no backticks, no explanation.\n"
            "If it asks a conceptual question, answer in plain conversational sentences, "
            "no bullet points, no markdown.\n"
            "If the image is too blurry to read clearly, respond only with: UNCLEAR_IMAGE"
        )

        r = requests.post(
            _get_ollama_api(),
            json={
                "model": _get_coder_model(),
                "prompt": prompt,
                "images": [b64],
                "stream": False
            },
            timeout=_get_timeout()
        )
        r.raise_for_status()
        answer = r.json().get("response", "").strip()

        if not answer or answer == "UNCLEAR_IMAGE":
            return None, "[ERROR] Photo too blurry or unclear — get closer and shoot straight on"

        answer = (
            answer.replace("```python", "").replace("```", "")
            .replace("**", "").replace("*", "").replace("#", "").strip()
        )
        answer = answer.replace("\n", " ").replace("\r", " ")
        while "  " in answer:
            answer = answer.replace("  ", " ")
        state["last_answer"] = answer
        return "photo", answer
    except Exception as e:
        return None, "[PHOTO ERROR] %s" % str(e)


# ── COMMANDS ──────────────────────────────────────────────────────────────────
def cmd_clip_answer():
    text = _clipboard_paste().strip()
    if not text:
        return "[ERROR] Clipboard is empty — copy the question first"
    state["last_question"] = text
    print(Fore.YELLOW + "[QUESTION] %s..." % text[:80] + Style.RESET_ALL)
    print(Fore.YELLOW + "[GENERATING ANSWER...]" + Style.RESET_ALL)
    answer = generate_answer(text)
    if "[ERROR]" in answer or "[ANSWER ERROR]" in answer:
        return answer
    if state["review_mode"]:
        return "REVIEW:%s" % answer
    print(Fore.YELLOW + "[SENDING TO PICO...]" + Style.RESET_ALL)
    result = send_to_pico(answer)
    return "[CLIP & ANSWER]\nQ: %s\nA: %s...\n%s" % (text[:100], answer[:10000], result)


def cmd_answer(text):
    return send_to_pico(text)


def cmd_type_test():
    return send_to_pico("Pico bridge is online and working correctly.")


def cmd_status():
    return (
        "Last question: %s\n"
        "Last answer:   %s\n"
        "Pico port:     %s\n"
        "Serial lib:    %s"
    ) % (
        state["last_question"][:120] or "none",
        state["last_answer"][:120] or "none",
        _get_pico_port(),
        "OK" if SERIAL_AVAILABLE else "NOT INSTALLED — pip install pyserial"
    )


def cmd_set_question(q):
    state["last_question"] = q
    return "[QUESTION SET] Ready — use !auto_answer to generate and type the answer"


def cmd_auto_answer():
    if not state["last_question"]:
        return "[NO QUESTION] Set one with !clip_answer, !photo, or type the question after !set_question"
    print(Fore.YELLOW + "[GENERATING ANSWER...]" + Style.RESET_ALL)
    answer = generate_answer(state["last_question"])
    if "[ERROR]" in answer or "[ANSWER ERROR]" in answer:
        return answer
    print(Fore.YELLOW + "[SENDING TO PICO...]" + Style.RESET_ALL)
    return send_to_pico(answer)


def dispatch(cmd_raw, extra_data=None):
    cmd     = cmd_raw.strip()
    cmd_low = cmd.lower()
    extra   = extra_data or {}

    if cmd_low == "!clip_answer":
        return cmd_clip_answer()

    if cmd_low.startswith("!answer "):
        return cmd_answer(cmd[8:].strip())

    if cmd_low == "!type_test":
        return cmd_type_test()

    if cmd_low == "!status":
        return cmd_status()

    if cmd_low == "!auto_answer" or cmd_low.startswith("!auto_answer "):
        inline = cmd[13:].strip()
        if inline:
            state["last_question"] = inline
        return cmd_auto_answer()

    if cmd_low.startswith("!set_question "):
        return cmd_set_question(cmd[14:].strip())

    if cmd_low == "!set_question":
        q = extra.get("question", "").strip()
        if q:
            state["last_question"] = q
            return "[QUESTION SET] %s" % q[:100]
        return "[ERROR] No question provided"

    if cmd_low in ("!slow", "!speed_slow"):
        state["typing_speed"] = "slow"
        return "[SPEED] Slow — hunt and peck mode"

    if cmd_low in ("!normal", "!speed_normal"):
        state["typing_speed"] = "normal"
        return "[SPEED] Normal — confident typist mode"

    if cmd_low in ("!fast", "!speed_fast"):
        state["typing_speed"] = "fast"
        return "[SPEED] Fast — transcribing mode"

    if cmd_low == "!review_on":
        state["review_mode"] = True
        return "[REVIEW MODE ON] Answers will be shown for approval before typing"

    if cmd_low == "!review_off":
        state["review_mode"] = False
        return "[AUTO MODE ON] Answers will be sent to Pico immediately"

    if cmd_low == "!send_answer":
        if not state["last_answer"]:
            return "[ERROR] No answer to send"
        result = send_to_pico(state["last_answer"])
        return "[SENT TO PICO] %s" % result

    if cmd_low == "!clear":
        state["last_question"] = ""
        state["last_answer"]   = ""
        return "[CLEARED] Question and answer wiped. Fresh start."

    if cmd_low == "!human":
        if not state["last_answer"]:
            return "[ERROR] No answer to rewrite yet."
        print(Fore.YELLOW + "[HUMAN] Rewriting in plain language..." + Style.RESET_ALL)
        try:
            prompt = (
                "Rewrite this answer so it sounds like a smart person talking casually.\n"
                "No bullet points, no markdown, no jargon. Plain conversational sentences only.\n"
                "Keep it accurate but make it sound natural, like you're explaining it out loud.\n\n"
                "ORIGINAL:\n%s\n\nRewrite:" % state["last_answer"]
            )
            r = requests.post(
                _get_ollama_api(),
                json={"model": _get_brain_model(), "prompt": prompt, "stream": False},
                timeout=_get_timeout()
            )
            r.raise_for_status()
            human_answer = r.json().get("response", "").strip()
            human_answer = (
                human_answer.replace("**", "").replace("*", "")
                .replace("`", "").replace("#", "")
            )
            state["last_answer"] = human_answer
            return "REVIEW:%s" % human_answer
        except Exception as e:
            return "[ERROR] Human rewrite failed: %s" % e

    if cmd_low in ("!quit", "!exit", "quit", "exit"):
        return "__QUIT__"

    if cmd_low == "!clip":
        text = _clipboard_paste()
        return "[PC CLIP] %s chars\n\n%s%s" % (
            len(text), text[:500], "..." if len(text) > 500 else ""
        )

    if cmd_low == "!code_on":
        state["code_mode"] = True
        return "[CODE MODE ON] Remember: set VS Code autoIndent to None (Ctrl+, -> autoIndent -> None)"

    if cmd_low == "!code_off":
        state["code_mode"] = False
        return "[CODE MODE OFF] Normal prose mode"

    return "[UNKNOWN] '%s' — try !clip_answer, !answer [text], !type_test, !status, !quit" % cmd


# ── WEB UI ────────────────────────────────────────────────────────────────────
WEB_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>Apex Pico Controller</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0d1117; color: #e6edf3; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; display: flex; flex-direction: column; height: 100dvh; }
  #header { background: #161b22; border-bottom: 1px solid #30363d; padding: 10px 14px; display: flex; align-items: center; justify-content: space-between; }
  #header h1 { font-size: 14px; font-weight: 600; color: #3fb950; }
  #chat { flex: 1; overflow-y: auto; padding: 12px 14px; display: flex; flex-direction: column; gap: 10px; }
  .msg { max-width: 100%; line-height: 1.5; }
  .msg.user { align-self: flex-end; background: #1f3a5f; color: #cae3ff; border-radius: 14px 14px 4px 14px; padding: 10px 14px; font-size: 14px; max-width: 90%; }
  .msg.bot { align-self: flex-start; background: #161b22; color: #e6edf3; border: 1px solid #30363d; border-radius: 4px 14px 14px 14px; padding: 12px 14px; font-size: 13px; white-space: pre-wrap; word-break: break-word; max-width: 100%; }
  .msg.system { align-self: center; color: #8b949e; font-size: 12px; font-style: italic; }
  .msg.thinking { align-self: flex-start; color: #f0a500; font-size: 13px; font-style: italic; }
  #input-area { background: #161b22; border-top: 1px solid #30363d; padding: 10px 12px; display: flex; flex-direction: column; gap: 8px; }
  #step-hint { font-size: 12px; color: #f0a500; display: none; padding: 4px 2px; }
  #text-input { width: 100%; background: #0d1117; color: #e6edf3; border: 1px solid #30363d; border-radius: 10px; padding: 10px 14px; font-size: 14px; resize: none; min-height: 44px; max-height: 180px; font-family: inherit; }
  #text-input:focus { outline: none; border-color: #3fb950; }
  #btn-row { display: flex; gap: 8px; }
  #send-btn { flex: 1; background: #2ea043; color: #fff; border: none; border-radius: 10px; padding: 10px; font-size: 15px; font-weight: 600; cursor: pointer; }
  .qcmd { background: #21262d; color: #8b949e; border: 1px solid #30363d; border-radius: 8px; padding: 8px 12px; font-size: 13px; cursor: pointer; flex: 1; }
  .qcmd.green { background: #0d4429; border-color: #2ea043; color: #3fb950; }
  .qcmd.blue  { background: #0c2d6b; border-color: #1f6feb; color: #58a6ff; }
  .btn-group { display: flex; gap: 6px; flex-wrap: wrap; }
  .btn-group-label { font-size: 10px; color: #3fb950; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; width: 100%; margin-top: 6px; }
  #photo-input { display: none; }
  .spd-btn { background:#21262d; color:#8b949e; border:1px solid #30363d; border-radius:8px; padding:5px 12px; font-size:12px; cursor:pointer; }
  .spd-btn.active { background:#0c2d6b; border-color:#1f6feb; color:#58a6ff; font-weight:600; }
  #paste-btn  { background:#0d4429; color:#3fb950; border:1px solid #2ea043; border-radius:10px; padding:10px 11px; font-size:13px; cursor:pointer; white-space:nowrap; }
  #pcpaste-btn{ background:#0c2d6b; color:#58a6ff; border:1px solid #1f6feb; border-radius:10px; padding:10px 11px; font-size:13px; cursor:pointer; white-space:nowrap; }
  #typepc-btn { background:#1a0a3d; color:#d2a8ff; border:1px solid #8957e5; border-radius:10px; padding:10px 11px; font-size:13px; cursor:pointer; white-space:nowrap; }
  #pcclip-btn { background:#21262d; color:#8b949e; border:1px solid #30363d; border-radius:10px; padding:10px 11px; font-size:13px; cursor:pointer; white-space:nowrap; }
  #code-bar { display:flex; align-items:center; gap:8px; background:#0d1117; border-bottom:1px solid #30363d; padding:7px 14px; }
  .code-btn { background:#21262d; color:#8b949e; border:1px solid #30363d; border-radius:8px; padding:5px 12px; font-size:12px; cursor:pointer; }
  .code-btn.active { background:#0d2a1f; border-color:#2ea043; color:#3fb950; font-weight:600; }
  #paste-modal { display:none; position:fixed; inset:0; background:rgba(0,0,0,0.75); z-index:100; align-items:center; justify-content:center; padding:20px; }
  .modal-box { background:#161b22; border:1px solid #30363d; border-radius:14px; padding:16px; width:100%; max-width:480px; display:flex; flex-direction:column; gap:10px; }
  #modal-ta { width:100%; background:#0d1117; color:#e6edf3; border:1px solid #30363d; border-radius:10px; padding:10px; font-size:14px; resize:none; font-family:inherit; }
  #modal-ta:focus { outline:none; border-color:#58a6ff; }
  #mode-bar { display: flex; align-items: center; justify-content: space-between; background: #0d1117; border-bottom: 1px solid #30363d; padding: 8px 14px; font-size: 12px; }
  #mode-label { color: #8b949e; }
  #mode-label span { font-weight: 600; }
  #mode-label span.auto { color: #3fb950; }
  #mode-label span.review { color: #f0a500; }
  .toggle-wrap { display: flex; align-items: center; gap: 8px; }
  .toggle { position: relative; width: 44px; height: 24px; }
  .toggle input { opacity: 0; width: 0; height: 0; }
  .slider { position: absolute; cursor: pointer; inset: 0; background: #21262d; border-radius: 24px; transition: .3s; border: 1px solid #30363d; }
  .slider:before { position: absolute; content: ""; height: 16px; width: 16px; left: 3px; bottom: 3px; background: #8b949e; border-radius: 50%; transition: .3s; }
  input:checked + .slider { background: #3d2000; border-color: #f0a500; }
  input:checked + .slider:before { transform: translateX(20px); background: #f0a500; }
  #review-panel { display: none; background: #161b22; border: 1px solid #f0a500; border-radius: 10px; margin: 8px 14px 0; padding: 12px; }
  #review-panel .review-title { color: #f0a500; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
  #review-text { width: 100%; background: #0d1117; color: #e6edf3; border: 1px solid #30363d; border-radius: 8px; padding: 10px; font-size: 13px; min-height: 80px; max-height: 200px; resize: vertical; font-family: inherit; }
  #review-text:focus { outline: none; border-color: #f0a500; }
  #review-btns { display: flex; gap: 8px; margin-top: 8px; }
  #review-send { flex: 1; background: #2ea043; color: #fff; border: none; border-radius: 8px; padding: 9px; font-size: 14px; font-weight: 600; cursor: pointer; }
  #review-discard { background: #3d1212; color: #f85149; border: 1px solid #f85149; border-radius: 8px; padding: 9px 14px; font-size: 13px; cursor: pointer; }
</style>
</head>
<body>
<div id="header"><h1>Apex Pico Controller</h1></div>

<div id="mode-bar">
  <div id="mode-label">Mode: <span id="mode-text" class="auto">Auto Fire</span></div>
  <div class="toggle-wrap">
    <span style="font-size:11px;color:#8b949e;">Review</span>
    <label class="toggle">
      <input type="checkbox" id="review-toggle" onchange="toggleReviewMode(this)">
      <span class="slider"></span>
    </label>
  </div>
</div>

<div id="speed-bar" style="display:flex; align-items:center; gap:8px; background:#0d1117; border-bottom:1px solid #30363d; padding:8px 14px;">
  <span style="font-size:11px;color:#8b949e; white-space:nowrap;">Speed:</span>
  <button id="speed-slow" class="spd-btn" onclick="setSpeed('slow')">Slow</button>
  <button id="speed-normal" class="spd-btn active" onclick="setSpeed('normal')">Normal</button>
  <button id="speed-fast" class="spd-btn" onclick="setSpeed('fast')">Fast</button>
</div>

<div id="code-bar">
  <span style="font-size:11px;color:#8b949e;white-space:nowrap;">Mode:</span>
  <button id="code-off-btn" class="code-btn active" onclick="setCodeMode(false)">Prose</button>
  <button id="code-on-btn"  class="code-btn"        onclick="setCodeMode(true)">Code</button>
  <span id="code-hint" style="font-size:11px;color:#f0a500;margin-left:4px;display:none;">Set VS Code autoIndent to None first</span>
</div>

<div id="review-panel">
  <div class="review-title">Review Answer Before Typing</div>
  <textarea id="review-text" placeholder="Answer will appear here..."></textarea>
  <div id="review-btns">
    <button id="review-send" onclick="approveAndSend()">Send to Pico</button>
    <button style="background:#0c2d6b;border:1px solid #1f6feb;color:#58a6ff;border-radius:8px;padding:9px 14px;font-size:13px;cursor:pointer;" onclick="humanRewrite()">Human</button>
    <button id="review-discard" onclick="discardAnswer()">Discard</button>
  </div>
</div>

<div id="chat">
  <div class="msg system">Apex Pico Controller ready. Clip a question or send a photo.</div>
</div>
<div id="input-area">
  <div id="step-hint"></div>
  <textarea id="text-input" placeholder="Type question or !answer [text]..." rows="1"></textarea>
  <div id="btn-row">
    <button id="send-btn" onclick="sendMsg()">Send</button>
    <button id="paste-btn"   onclick="pasteToInput()"   title="Paste phone clipboard into input">Paste</button>
    <button id="pcpaste-btn" onclick="pcClipToInput()"  title="Pull PC clipboard into input">PC Clip In</button>
    <button id="typepc-btn"  onclick="typeToPC()"       title="Type phone clipboard on PC via Pico">Type to PC</button>
    <button id="pcclip-btn"  onclick="sendCmd('!clip')" title="Show PC clipboard in chat">PC Clip</button>
  </div>
  <div class="btn-group-label">Quick Actions</div>
  <div class="btn-group">
    <button class="qcmd green" onclick="sendCmd('!clip_answer')">Clip &amp; Answer</button>
    <button class="qcmd green" onclick="sendCmd('!auto_answer')">Auto Answer</button>
  </div>
  <div class="btn-group">
    <button class="qcmd blue" onclick="startSetQuestion()">Set Question</button>
    <button class="qcmd blue" onclick="document.getElementById('photo-input').click()">Photo</button>
    <button class="qcmd" onclick="sendCmd('!type_test')">Test Pico</button>
    <button class="qcmd" onclick="sendCmd('!status')">Status</button>
  </div>
  <div class="btn-group-label">Tools</div>
  <div class="btn-group">
    <button class="qcmd" style="background:#3d2000;border-color:#f0a500;color:#f0a500;" onclick="humanRewrite()">Human</button>
    <button class="qcmd" style="background:#3d1212;border-color:#f85149;color:#f85149;" onclick="clearSession()">Clear</button>
  </div>
  <input type="file" id="photo-input" accept="image/*" capture="environment" onchange="uploadPhoto(this)">
</div>

<div id="paste-modal" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.75); z-index:100; align-items:center; justify-content:center; padding:20px;">
  <div class="modal-box">
    <div style="display:flex; justify-content:space-between; align-items:center;">
      <span id="modal-title" style="color:#e6edf3; font-size:14px; font-weight:600;"></span>
      <button onclick="closePasteModal()" style="background:none;border:none;color:#8b949e;font-size:18px;cursor:pointer;">X</button>
    </div>
    <p style="color:#8b949e;font-size:12px;">Long-press below, choose Paste, then tap Confirm</p>
    <textarea id="modal-ta" rows="6" placeholder="Long-press here and choose Paste..."></textarea>
    <div style="display:flex;gap:8px;">
      <button onclick="confirmPasteModal()" style="flex:1;background:#1f6feb;color:#fff;border:none;border-radius:10px;padding:12px;font-size:15px;font-weight:600;cursor:pointer;">Confirm</button>
      <button onclick="closePasteModal()" style="background:#21262d;color:#8b949e;border:1px solid #30363d;border-radius:10px;padding:12px 16px;font-size:14px;cursor:pointer;">Cancel</button>
    </div>
  </div>
</div>
<script>
const chat = document.getElementById('chat');
const input = document.getElementById('text-input');
const stepHint = document.getElementById('step-hint');
let flowState = null;
let reviewMode = false;

async function setSpeed(speed) {
  document.querySelectorAll('.spd-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('speed-' + speed).classList.add('active');
  await sendToServer({cmd: '!' + speed});
}

async function setCodeMode(on) {
  document.getElementById('code-on-btn').classList.toggle('active', on);
  document.getElementById('code-off-btn').classList.toggle('active', !on);
  document.getElementById('code-hint').style.display = on ? 'inline' : 'none';
  const r = await sendToServer({cmd: on ? '!code_on' : '!code_off'});
  addMsg(r, 'system');
}

let pasteModalMode = null;

function openPasteModal(mode) {
  pasteModalMode = mode;
  document.getElementById('modal-title').textContent = mode === 'typepc'
    ? 'Paste text to type on PC'
    : 'Paste text into command box';
  document.getElementById('modal-ta').value = '';
  document.getElementById('paste-modal').style.display = 'flex';
  setTimeout(() => document.getElementById('modal-ta').focus(), 100);
}

function closePasteModal() {
  document.getElementById('paste-modal').style.display = 'none';
  pasteModalMode = null;
}

async function confirmPasteModal() {
  const text = document.getElementById('modal-ta').value;
  const mode = pasteModalMode;
  closePasteModal();
  if (!text.trim()) return;
  if (mode === 'typepc') {
    addMsg('Typing to PC: "' + text.substring(0, 60) + (text.length > 60 ? '...' : '') + '"', 'user');
    const thinking = addMsg('Sending to Pico...', 'thinking');
    const r = await sendToServer({cmd: '!answer ' + text});
    thinking.remove();
    addMsg(r, 'bot');
  } else {
    const pos = input.selectionStart || input.value.length;
    input.value = input.value.substring(0, pos) + text + input.value.substring(pos);
    input.focus();
    input.selectionStart = input.selectionEnd = pos + text.length;
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 180) + 'px';
  }
}

function pasteToInput() { openPasteModal('input'); }
function typeToPC()     { openPasteModal('typepc'); }

async function pcClipToInput() {
  try {
    const res = await fetch('/clip_to_input', {method:'POST', headers:{'Content-Type':'application/json'}});
    const data = await res.json();
    if (!data.text) { addMsg('[PC clipboard is empty]', 'system'); return; }
    const pos = input.selectionStart || input.value.length;
    input.value = input.value.substring(0, pos) + data.text + input.value.substring(pos);
    input.focus();
    input.selectionStart = input.selectionEnd = pos + data.text.length;
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 180) + 'px';
  } catch(e) {
    addMsg('[Could not reach server: ' + e.message + ']', 'system');
  }
}

async function toggleReviewMode(el) {
  reviewMode = el.checked;
  const label = document.getElementById('mode-text');
  label.textContent = reviewMode ? 'Review' : 'Auto Fire';
  label.className = reviewMode ? 'review' : 'auto';
  const cmd = reviewMode ? '!review_on' : '!review_off';
  await sendToServer({cmd});
}

function showReviewPanel(answer) {
  const panel = document.getElementById('review-panel');
  document.getElementById('review-text').value = answer;
  panel.style.display = 'block';
  panel.scrollIntoView({behavior: 'smooth'});
}

function hideReviewPanel() {
  document.getElementById('review-panel').style.display = 'none';
  document.getElementById('review-text').value = '';
}

async function approveAndSend() {
  const edited = document.getElementById('review-text').value.trim();
  if (!edited) return;
  const r = await sendToServer({cmd: '!answer ' + edited});
  addMsg('[SENT] ' + edited.substring(0, 80) + '...', 'bot');
  hideReviewPanel();
}

function discardAnswer() {
  hideReviewPanel();
  addMsg('[DISCARDED] Answer thrown away.', 'system');
}

async function humanRewrite() {
  addMsg('Rewriting in plain language...', 'system');
  const r = await sendToServer({cmd: '!human'});
  if (r.startsWith('REVIEW:')) {
    const answer = r.substring(7);
    addMsg('[HUMAN] Rewritten — review it above.', 'system');
    showReviewPanel(answer);
  } else {
    addMsg(r, 'bot');
  }
}

async function clearSession() {
  const r = await sendToServer({cmd: '!clear'});
  hideReviewPanel();
  addMsg(r, 'system');
}

function addMsg(text, cls) {
  const d = document.createElement('div');
  d.className = 'msg ' + cls;
  d.textContent = text;
  chat.appendChild(d);
  chat.scrollTop = chat.scrollHeight;
  return d;
}
function setHint(text) { stepHint.style.display = text ? 'block' : 'none'; stepHint.textContent = text; }

async function sendToServer(payload) {
  const thinking = addMsg('Working...', 'thinking');
  try {
    const res = await fetch('/command', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload) });
    const data = await res.json();
    thinking.remove();
    return data.result || '[No response]';
  } catch(e) { thinking.remove(); return '[Connection error: ' + e.message + ']'; }
}

function startSetQuestion() {
  flowState = 'set_question';
  setHint('Type or paste the question, then tap Send');
  addMsg('Set Question mode — paste your question below', 'system');
}

async function sendCmd(cmd) {
  input.value = '';
  addMsg(cmd, 'user');
  const r = await sendToServer({cmd});
  if (r.startsWith('REVIEW:')) {
    const answer = r.substring(7);
    addMsg('[REVIEW MODE] Check the answer above before sending.', 'system');
    showReviewPanel(answer);
  } else {
    addMsg(r, 'bot');
  }
}

async function sendMsg() {
  const text = input.value.trim();
  if (!text) return;
  input.value = ''; input.style.height = 'auto';
  addMsg(text, 'user');

  if (flowState === 'set_question') {
    flowState = null; setHint('');
    const r = await sendToServer({cmd: '!set_question', question: text});
    addMsg(r, 'bot');
    return;
  }
  const r = await sendToServer({cmd: text});
  if (r.startsWith('REVIEW:')) {
    const answer = r.substring(7);
    addMsg('[REVIEW MODE] Check the answer above before sending.', 'system');
    showReviewPanel(answer);
  } else {
    addMsg(r, 'bot');
  }
}

async function uploadPhoto(input_el) {
  const file = input_el.files[0];
  if (!file) return;
  addMsg('Photo received — extracting question and generating answer...', 'system');
  const thinking = addMsg('Reading photo...', 'thinking');
  try {
    const formData = new FormData();
    formData.append('photo', file);
    const res = await fetch('/upload_photo', { method: 'POST', body: formData });
    const data = await res.json();
    thinking.remove();
    addMsg(data.result || '[No response]', 'bot');
  } catch(e) { thinking.remove(); addMsg('[Upload error: ' + e.message + ']', 'bot'); }
  input_el.value = '';
}

input.addEventListener('input', function() { this.style.height = 'auto'; this.style.height = Math.min(this.scrollHeight, 180) + 'px'; });
input.addEventListener('keydown', function(e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMsg(); } });
</script>
</body>
</html>"""


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def run_web_server():
    try:
        from flask import Flask, request, jsonify, render_template_string
    except ImportError:
        log.error("Flask not installed. Run: pip install flask")
        sys.exit(1)

    flask_port = _get_flask_port()
    app = Flask(__name__)
    app.logger.disabled = True
    import logging as _logging
    _logging.getLogger("werkzeug").setLevel(_logging.ERROR)

    @app.route("/")
    def index():
        return render_template_string(WEB_HTML)

    @app.route("/clip_to_input", methods=["POST"])
    def clip_to_input():
        try:
            text = _clipboard_paste()
            return jsonify({"text": text})
        except Exception as e:
            return jsonify({"text": "", "error": str(e)})

    @app.route("/command", methods=["POST"])
    def command():
        data    = request.get_json(force=True) or {}
        cmd_raw = data.get("cmd", "").strip()
        if not cmd_raw:
            return jsonify({"result": "[Empty command]"})
        extra = {"question": data.get("question", "")}
        result = dispatch(cmd_raw, extra)
        return jsonify({"result": result})

    @app.route("/upload_photo", methods=["POST"])
    def upload_photo():
        if "photo" not in request.files:
            return jsonify({"result": "[ERROR] No photo received"})
        photo = request.files["photo"]
        image_bytes = photo.read()
        question, answer = analyze_photo_and_answer(image_bytes)
        if not question:
            return jsonify({"result": answer})
        send_to_pico(answer)
        return jsonify({
            "result": "[PHOTO ANSWER]\nQ: %s\nA: %s...\n[SENT TO PICO]" % (
                question[:120], answer[:120]
            )
        })

    local_ip = get_local_ip()
    log.info("Apex Pico Controller web server started on %s:%s", local_ip, flask_port)
    print(Fore.GREEN + "\nApex Pico Controller — Phone Mode\n" + Style.RESET_ALL)
    print("  Open on your phone:  http://%s:%d" % (local_ip, flask_port))
    print("  Or on this PC:       http://localhost:%d" % flask_port)
    print("  Press Ctrl+C to stop.\n")
    app.run(host="0.0.0.0", port=flask_port, debug=False, use_reloader=False, threaded=True)


def run_terminal():
    print(Fore.GREEN + "\nApex Pico Controller — PC Terminal Mode\n" + Style.RESET_ALL)
    print("Commands: !clip_answer  !answer [text]  !type_test  !auto_answer  !status  !quit\n")

    while True:
        try:
            raw = input("Apex >> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye.")
            break

        if not raw:
            continue

        result = dispatch(raw)
        if result == "__QUIT__":
            print("Goodbye.")
            break
        print(Fore.CYAN + "-" * 60 + Style.RESET_ALL)
        print(result)
        print(Fore.CYAN + "-" * 60 + Style.RESET_ALL)
        print()


def main():
    print(Fore.GREEN + "\nApex Pico Controller\n" + Style.RESET_ALL)
    print("  1  —  PC Terminal Mode")
    print("  2  —  Phone Mode (browser on phone)")
    print()
    mode = input("Pick a mode [1/2]: ").strip()
    if mode == "2":
        run_web_server()
    else:
        run_terminal()


# ── SINGLETON ─────────────────────────────────────────────────────────────────
_pico_bridge_instance = None


def get_pico_bridge():
    """Return the singleton PicoBridge state dict (and ensure serial config is loaded)."""
    global _pico_bridge_instance
    if _pico_bridge_instance is None:
        _pico_bridge_instance = state
    return _pico_bridge_instance


# ── TOOL REGISTRY ─────────────────────────────────────────────────────────────
def register_tools(registry) -> None:
    """Register Pico bridge tools with the agent tool registry."""
    registry.register("pico_send", send_to_pico, description="Send text to Pico for HID typing")
    registry.register("pico_status", cmd_status, description="Return Pico bridge status")
    registry.register("pico_type_test", cmd_type_test, description="Run Pico connection type test")
    registry.register("pico_dispatch", dispatch, description="Dispatch a raw Pico bridge command")


if __name__ == "__main__":
    main()
