"""
VOICE ACTIVATION - Narrated Workflow System for Apex
=====================================================
Architecture: voice -> transcribed text -> expand_shortcuts -> agent.think(text)
Everything the agent understands by typing, it understands by voice.

FEATURES:
- Thesaurus alias map: tuples of natural phrases -> explicit commands
- Narrated workflow recorder: walk the agent through once, saves as named routine
- Routine playback: one phrase replays the full sequence
- Push-to-talk (F9) or continuous wake-word mode ("hey Apex")
- Graceful fallback: unrecognized phrases go straight to the agent as natural language
"""

import json
import time
import threading
import logging
import os
import yaml
from typing import Dict, List, Optional, Callable
from pathlib import Path
from datetime import datetime

log = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent.parent / "core" / "config.yaml"


def _storage_base() -> Path:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return Path(cfg.get("storage", {}).get("base", "C:/ai_agent/apex/data"))


# ─────────────────────────────────────────────
# OPTIONAL IMPORTS — fail gracefully
# ─────────────────────────────────────────────
try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False
    log.warning("speech_recognition not installed. Run: pip install SpeechRecognition")

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False


# ═══════════════════════════════════════════════════════════
# THESAURUS ALIAS MAP
# Format: (tuple of natural phrases) : "explicit command"
# Add your own phrases freely — just add to the tuple.
# Unrecognized phrases pass to the agent LLM automatically.
# ═══════════════════════════════════════════════════════════
_ALIAS_MAP = {

    # ── SCREEN READING ─────────────────────────────────────
    (
        "scan the screen", "read the screen", "what do you see", "look at the screen",
        "analyze the screen", "eyes open", "read it", "what's on screen",
        "tell me what you see", "describe the screen"
    ): "Use see_screen and read all text visible, top to bottom. Describe everything.",

    (
        "do you see the instructions", "read the instructions", "what are the steps",
        "show me the instructions", "find the instructions", "what does it say"
    ): "Use see_screen to find the instruction block, read it completely, and summarize what needs to be done.",

    (
        "do you see the code", "read the code", "look at the code", "analyze the code",
        "what code is there", "show me the code"
    ): "Use see_screen and describe all code currently visible. Read every line.",

    (
        "read the question", "what is the question", "show me the question",
        "find the question"
    ): "Scroll to see the full question — scroll up then down if needed — read it completely, and tell me what it asks.",

    (
        "where is the mouse", "mouse position", "cursor position", "where am i"
    ): "TOOL: get_mouse_pos()",

    (
        "what app is open", "what is open", "what program is this",
        "identify the application"
    ): "Use analyze_visuals to identify what application is open and what state it is in.",

    # ── SCROLLING & NAVIGATION ─────────────────────────────
    (
        "scroll up", "move up", "go up", "up a bit"
    ): "TOOL: scroll_up(\"10\")",

    (
        "scroll down", "move down", "go down", "down a bit"
    ): "TOOL: scroll_down(\"10\")",

    (
        "page up", "scroll up more", "up more", "more up"
    ): "TOOL: scroll_up(\"30\")",

    (
        "page down", "scroll down more", "down more", "more down", "keep going down"
    ): "TOOL: scroll_down(\"30\")",

    (
        "go to the top", "scroll to top", "beginning", "start of page"
    ): "TOOL: scroll_up(\"100\")",

    (
        "go to the bottom", "scroll to bottom", "end of page", "bottom of page"
    ): "TOOL: scroll_down(\"100\")",

    (
        "go back", "previous page", "back"
    ): "TOOL: hotkey(\"alt+left\")",

    (
        "go forward", "next page", "forward"
    ): "TOOL: hotkey(\"alt+right\")",

    (
        "new tab", "open new tab"
    ): "TOOL: hotkey(\"ctrl+t\")",

    (
        "close tab", "close window", "close this"
    ): "TOOL: hotkey(\"ctrl+w\")",

    (
        "switch windows", "change window", "alt tab", "next window"
    ): "TOOL: hotkey(\"alt+tab\")",

    (
        "refresh", "reload", "refresh the page"
    ): "TOOL: hotkey(\"ctrl+r\")",

    # ── MOUSE & CLICKS ─────────────────────────────────────
    (
        "click here", "click that", "click it", "press this", "hit that",
        "tap it", "select it"
    ): "Get current mouse position with get_mouse_pos then click those coordinates.",

    (
        "double click", "double click that", "open that", "launch that"
    ): "Get current mouse position with get_mouse_pos then double-click those coordinates.",

    (
        "right click", "right click that", "open context menu", "options menu"
    ): "Get current mouse position with get_mouse_pos then right-click those coordinates.",

    (
        "check the box", "click the checkbox", "tick the box", "check that"
    ): "Use see_screen to find the checkbox near my last statement, get its coordinates, and click it.",

    (
        "click the button", "press the button", "hit the button"
    ): "Use see_screen to find the most relevant button for the current context and click it.",

    (
        "click ok", "press ok", "confirm", "accept"
    ): "Use find_text to locate OK, Confirm, Accept, or Yes and click it.",

    (
        "click cancel", "press cancel", "dismiss", "close dialog"
    ): "Use find_text to locate Cancel, Dismiss, Close, or No and click it.",

    # ── KEYBOARD & TEXT ENTRY ──────────────────────────────
    (
        "type this", "type it", "write this", "enter text", "fill in"
    ): "Type the exact text I just spoke into the currently focused input field.",

    (
        "send it", "press enter", "hit enter", "submit form", "go"
    ): "TOOL: press_key(\"enter\")",

    (
        "copy that", "copy this", "copy it"
    ): "TOOL: hotkey(\"ctrl+c\")",

    (
        "paste that", "paste this", "paste here", "drop it", "paste it"
    ): "TOOL: hotkey(\"ctrl+v\")",

    (
        "undo that", "undo this", "undo", "mistake"
    ): "TOOL: hotkey(\"ctrl+z\")",

    (
        "redo that", "redo this", "redo"
    ): "TOOL: hotkey(\"ctrl+y\")",

    (
        "select all", "grab everything", "highlight all"
    ): "TOOL: hotkey(\"ctrl+a\")",

    (
        "save that", "save file", "save progress", "save work", "save it"
    ): "TOOL: hotkey(\"ctrl+s\")",

    (
        "clear the line", "delete that line", "clear it"
    ): "TOOL: hotkey(\"ctrl+a\") then TOOL: press_key(\"backspace\")",

    (
        "tab", "next field", "tab over"
    ): "TOOL: press_key(\"tab\")",

    (
        "escape", "press escape", "close popup"
    ): "TOOL: press_key(\"escape\")",

    # ── CODE & PROGRAMMING ─────────────────────────────────
    (
        "write the code", "start coding", "build it", "code it up",
        "write me the code", "begin writing the code", "write a solution"
    ): "Read all visible instructions by scrolling, write complete working code, present it to me, and wait for my approval before doing anything else.",

    (
        "debug the code", "find the bugs", "what is wrong", "fix the code",
        "check the code for errors"
    ): "Read all code on screen by scrolling, analyze every line for bugs and errors, write corrected version with comments explaining each change, present it to me and wait for approval.",

    (
        "explain the code", "what does this do", "walk me through the code"
    ): "Read all code on screen, explain what it does in plain language, step by step.",

    (
        "run the code", "test it", "execute it"
    ): "Present the code to me first and confirm I want to run it. Do not execute without my explicit confirmation.",

    (
        "write a function", "write a method", "write a class"
    ): "Based on the visible instructions or my last statement, write the requested code structure, present it, and wait for my approval.",

    # ── TEST TAKING ────────────────────────────────────────
    (
        "answer the question", "solve this", "give me the answer",
        "what is the answer", "figure out the answer"
    ): "Read the full question on screen by scrolling, write the best expert answer, present it to me, and wait for my approval before typing it anywhere.",

    (
        "read all the options", "what are the choices", "read the choices"
    ): "Use see_screen and scroll to read every answer option for this question.",

    (
        "pick the best answer", "which option is correct", "which one is right"
    ): "Analyze all visible answer options, identify the correct one, explain your reasoning, present your choice to me, and wait for my approval before clicking anything.",

    (
        "i'm clicking the start box", "cursor is ready", "input is focused",
        "i clicked the box", "i clicked the field"
    ): "I have clicked the input field. The cursor is now positioned there. You may type the answer now.",

    (
        "start test mode", "start the test", "enter exam mode"
    ): "!test professional",

    (
        "end test mode", "exit test mode", "stop test mode"
    ): "!test off",

    # ── CONTEXT NARRATION (you tell the agent what you're doing) ─
    (
        "i've opened the app", "i opened the application", "app is open",
        "program is open", "i launched it"
    ): "I have opened the application. Use see_screen to read what is visible and describe what you see.",

    (
        "i'm on the website", "website is open", "page is loaded", "i opened the browser"
    ): "I have navigated to the page. Use see_screen to read what is visible.",

    (
        "i'm logged in", "i just logged in", "login complete"
    ): "I have logged in. Use see_screen to read the current state of the application.",

    (
        "new task", "next task", "moving on", "new question"
    ): "A new task or question is now visible. Use see_screen to read it and tell me what needs to be done.",

    (
        "i submitted it", "i clicked submit", "i sent it", "submitted"
    ): "I have submitted. Use see_screen to read the confirmation or result.",

    (
        "i reviewed it", "looks good", "approved", "that is correct"
    ): "Noted. I will proceed to the next step.",

    # ── SUSTAINED TASKS & WORKFLOWS ────────────────────────
    (
        "do the next step", "next step", "continue", "carry on", "proceed"
    ): "!resume",

    (
        "step by step", "walk me through it", "guide me through this",
        "break it down"
    ): "Break the current task into individual numbered steps. Wait for me to say 'next step' before executing each one.",

    (
        "do what i just said", "execute that", "make it happen", "do it"
    ): "Analyze my previous statement, determine the tools needed to accomplish it, and execute step by step.",

    (
        "keep going", "keep doing it", "dont stop", "loop it", "continue the task"
    ): "Continue the current task without stopping. Keep looping until I say stop.",

    (
        "wait for me", "hold on", "one moment"
    ): "!pause",

    # ── INTERNET / WEB ─────────────────────────────────────
    (
        "open google", "go to google", "search google"
    ): "TOOL: browse_url(\"https://www.google.com\")",

    (
        "open gemini", "go to gemini", "launch gemini"
    ): "TOOL: browse_url(\"https://gemini.google.com\")",

    (
        "speak to gemini", "chat with gemini", "start gemini chat", "talk to gemini"
    ): "Chat with Gemini. My mouse is on the Gemini input box. Search your memory for how to do this, then begin a conversation.",

    (
        "search for", "look up", "research"
    ): "Use research_online to search for the topic I mentioned.",

    (
        "read this page", "read the page", "what does this page say"
    ): "Scroll to top then read the full page by scrolling down section by section with see_screen.",

    # ── TASK CONTROL ───────────────────────────────────────
    (
        "stop", "stop now", "halt", "abort", "cancel", "wait", "freeze",
        "hold", "never mind", "forget it"
    ): "Stop immediately. Cancel current execution and wait for my next instruction.",

    (
        "pause", "hold on", "pause everything"
    ): "!pause",

    (
        "resume", "unpause", "go ahead"
    ): "!resume",

    (
        "arm controls", "go live", "enable controls", "activate"
    ): "!arm 30 minutes",

    (
        "disarm", "stand down", "safe mode", "disable controls"
    ): "!disarm",

    (
        "switch to vision mode", "vision mode", "use your eyes"
    ): "!mode vision",

    (
        "switch to task mode", "task mode", "action mode", "thinking mode"
    ): "!mode task",

    # ── STATUS & MEMORY ────────────────────────────────────
    (
        "status", "report", "what mode are you in", "how are you doing",
        "system status"
    ): "!status",

    (
        "show memory", "memory check", "what do you remember", "recall"
    ): "!stats",

    (
        "show ledger", "show audit", "what have you done"
    ): "!ledger",

    (
        "search memory", "check memory", "look in memory"
    ): "Search your memory for what you know about the current task and tell me what you find.",

    (
        "remember this", "save this to memory", "write this down"
    ): "Write what I just said to your memory as a lesson for future reference.",

    (
        "run dream cycle", "learn from today", "process the day"
    ): "!dream",
}

# ── Unpack thesaurus tuples into flat lookup dict ──────────
VOICE_SHORTCUTS: Dict[str, str] = {}
for _aliases, _command in _ALIAS_MAP.items():
    for _alias in _aliases:
        VOICE_SHORTCUTS[_alias] = _command


# ═══════════════════════════════════════════════════════════
# ROUTINE RECORDER
# Walk the agent through a task once -> save -> replay any time
# ═══════════════════════════════════════════════════════════
class RoutineRecorder:
    def __init__(self, memory_module=None):
        self.memory = memory_module
        self.recording = False
        self.routine_name = ""
        self.steps: List[str] = []
        self.routines: Dict[str, List[str]] = {}
        self._load_routines()

    def start(self, name: str) -> str:
        self.recording = True
        self.routine_name = name.strip().lower().replace(" ", "_")
        self.steps = []
        log.info("Recording routine: %s", self.routine_name)
        return "Recording started for routine '%s'. Every command you give me will be saved. Say 'stop recording' when done." % name

    def add_step(self, command: str):
        if self.recording:
            self.steps.append(command)
            log.info("Step %d recorded: %s", len(self.steps), command)

    def stop(self) -> Optional[str]:
        if not self.recording or not self.steps:
            self.recording = False
            return None
        self.recording = False
        name = self.routine_name
        self.routines[name] = self.steps.copy()
        self._save_routines()
        if self.memory:
            try:
                steps_text = " | ".join(
                    ["Step %d: %s" % (i + 1, s) for i, s in enumerate(self.steps)]
                )
                self.memory.write_lesson(
                    "VOICE ROUTINE '%s': %s" % (name, steps_text),
                    tags=["routine", name, "workflow", "voice"]
                )
            except Exception as e:
                log.warning("Could not write routine to memory: %s", e)
        log.info("Routine '%s' saved with %d steps", name, len(self.steps))
        return name

    def get_routine(self, name: str) -> Optional[List[str]]:
        key = name.strip().lower().replace(" ", "_")
        return self.routines.get(key)

    def list_routines(self) -> List[str]:
        return list(self.routines.keys())

    def delete_routine(self, name: str) -> bool:
        key = name.strip().lower().replace(" ", "_")
        if key in self.routines:
            del self.routines[key]
            self._save_routines()
            return True
        return False

    def _routines_path(self) -> Path:
        return _storage_base() / "voice_config" / "routines.json"

    def _save_routines(self):
        try:
            path = self._routines_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.routines, f, indent=2)
        except Exception as e:
            log.warning("Could not save routines: %s", e)

    def _load_routines(self):
        try:
            path = self._routines_path()
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    self.routines = json.load(f)
                log.info("Loaded %d saved routines", len(self.routines))
        except Exception as e:
            log.warning("Could not load routines: %s", e)


# ═══════════════════════════════════════════════════════════
# VOICE ACTIVATION SYSTEM
# ═══════════════════════════════════════════════════════════
class VoiceActivationSystem:
    """
    Voice control for the Apex agent.

    Usage:
        vs = VoiceActivationSystem(think_callback=agent.think, say_callback=agent.say)
        vs.start_push_to_talk("F9")     # hold F9 to speak
        # or
        vs.start_continuous()           # say "hey Apex" to wake
    """

    def __init__(self, think_callback: Callable = None,
                 say_callback: Callable = None):
        self.think = think_callback
        self.say_fn = say_callback

        self.listening = False
        self.ptt_mode = False
        self.ptt_key = "F9"
        self.wake_words = [
            "hey apex", "apex", "okay apex",
            "main controller", "orchestrator"
        ]

        self.recognizer = None
        self.microphone = None
        self.tts_engine = None
        self._tts_mode = "console"

        self.recorder = RoutineRecorder()
        self.history: List[Dict] = []

        self._init_audio()
        self._init_tts()
        log.info("Voice Activation System initialized")

    # ── AUDIO INIT ──────────────────────────────────────────

    def _init_audio(self):
        if not SR_AVAILABLE:
            log.warning("speech_recognition not available -- voice input disabled")
            return
        try:
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = 300
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.pause_threshold = 0.8
            self.microphone = sr.Microphone()
            threading.Thread(target=self._calibrate, daemon=True).start()
        except Exception as e:
            log.error("Audio init failed: %s", e)

    def _calibrate(self):
        try:
            with self.microphone as source:
                log.info("Calibrating microphone...")
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                log.info("Microphone calibrated")
        except Exception as e:
            log.warning("Mic calibration failed: %s", e)

    # ── TTS INIT ────────────────────────────────────────────

    def _init_tts(self):
        if EDGE_TTS_AVAILABLE:
            self._tts_mode = "edge"
            log.info("TTS: edge-tts")
        elif PYTTSX3_AVAILABLE:
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty('rate', 185)
                self.tts_engine.setProperty('volume', 0.9)
                voices = self.tts_engine.getProperty('voices')
                for v in voices:
                    if 'david' in v.name.lower() or 'mark' in v.name.lower():
                        self.tts_engine.setProperty('voice', v.id)
                        break
                self._tts_mode = "pyttsx3"
                log.info("TTS: pyttsx3")
            except Exception as e:
                log.warning("pyttsx3 failed: %s", e)
                self._tts_mode = "console"
        else:
            self._tts_mode = "console"

    # ── SPEAKING ────────────────────────────────────────────

    def speak(self, text: str):
        """Speak text. Cleans output noise before speaking."""
        clean = self._clean_for_speech(text)
        if not clean:
            return
        if self._tts_mode == "edge":
            self._speak_edge(clean)
        elif self._tts_mode == "pyttsx3" and self.tts_engine:
            try:
                self.tts_engine.say(clean)
                self.tts_engine.runAndWait()
            except Exception as e:
                log.error("pyttsx3 error: %s", e)
                print(clean)
        else:
            print(clean)

    def _speak_edge(self, text: str):
        try:
            import asyncio

            async def _run():
                communicate = edge_tts.Communicate(text, voice="en-US-GuyNeural")
                tmp = _storage_base() / "voice_config" / "tts_out.mp3"
                tmp.parent.mkdir(parents=True, exist_ok=True)
                await communicate.save(str(tmp))
                os.startfile(str(tmp))
                time.sleep(min(len(text) * 0.055 + 0.5, 15))

            asyncio.run(_run())
        except Exception as e:
            log.warning("edge-tts failed: %s", e)
            print(text)

    def _clean_for_speech(self, text: str) -> str:
        """Remove tool execution lines, status codes, OCR noise."""
        skip_prefixes = (
            '[TOOL', '[MODE', '[LOOP', '[MEMORY', '[GOVERNANCE',
            '[AUTO-FIX', 'TOOL:', 'INFO:', 'WARNING:', 'ERROR:',
            '[ROUTINE]', '[VOICE]', '[RECORDED]', '-> '
        )
        lines = []
        for line in text.split('\n'):
            s = line.strip()
            if any(s.startswith(p) for p in skip_prefixes):
                continue
            if s:
                lines.append(s)
        result = ' '.join(lines)
        if len(result) > 450:
            result = result[:450] + "..."
        return result.strip()

    # ── TRANSCRIPTION ───────────────────────────────────────

    def transcribe(self, timeout: float = 5.0, phrase_limit: float = 12.0) -> Optional[str]:
        """Listen once, return transcribed text or None."""
        if not SR_AVAILABLE or not self.microphone:
            return None
        try:
            with self.microphone as source:
                audio = self.recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=phrase_limit
                )
            try:
                text = self.recognizer.recognize_google(audio)
                log.info("Heard: %s", text)
                return text
            except sr.UnknownValueError:
                return None
            except sr.RequestError:
                try:
                    return self.recognizer.recognize_sphinx(audio)
                except Exception:
                    return None
        except sr.WaitTimeoutError:
            return None
        except Exception as e:
            log.error("Transcribe error: %s", e)
            return None

    # ── LISTENING MODES ─────────────────────────────────────

    def start_push_to_talk(self, key: str = "F9") -> str:
        """
        Push-to-talk using global OS-level hotkey hook.
        Works even when the terminal is blocking on input().
        Press and release the key to speak one command.
        """
        if not KEYBOARD_AVAILABLE:
            return "Push-to-talk requires: pip install keyboard"

        self.ptt_key = key.upper()
        self.ptt_mode = True
        self.listening = True
        self._ptt_busy = False

        def _on_press():
            if not self.listening or not self.ptt_mode:
                return
            if self._ptt_busy:
                return
            self._ptt_busy = True

            def _capture():
                try:
                    self.speak("Listening")
                    text = self.transcribe(timeout=15.0, phrase_limit=25.0)
                    if text:
                        self._handle_command(text)
                except Exception as e:
                    log.error("PTT capture error: %s", e)
                finally:
                    self._ptt_busy = False

            threading.Thread(target=_capture, daemon=True).start()

        try:
            keyboard.add_hotkey(key, _on_press, suppress=False)
        except Exception as e:
            return "Could not register hotkey %s: %s. Try running as Administrator." % (key, e)

        log.info("PTT active on %s (global hotkey)", key)
        return "Push-to-talk active. Press %s to speak. Type !voice off to stop." % key

    def stop(self) -> str:
        """Stop all voice listening and remove hotkeys."""
        self.listening = False
        self.ptt_mode = False
        if KEYBOARD_AVAILABLE:
            try:
                keyboard.remove_all_hotkeys()
            except Exception:
                pass
        log.info("Voice listening stopped")
        return "Voice listening stopped."

    def start_continuous(self) -> str:
        """Always listening. Say a wake word then your command."""
        if not SR_AVAILABLE:
            return "speech_recognition not available -- pip install SpeechRecognition"
        self.listening = True

        def _loop():
            self.speak("Continuous voice mode active. Say hey Apex to speak.")
            log.info("Continuous voice mode active")
            while self.listening:
                try:
                    text = self.transcribe(timeout=None, phrase_limit=5)
                    if not text:
                        continue
                    text_lower = text.lower()
                    if any(w in text_lower for w in self.wake_words):
                        self.speak("Yes?")
                        command = self.transcribe(timeout=8.0, phrase_limit=20.0)
                        if command:
                            self._handle_command(command)
                except Exception as e:
                    log.error("Continuous loop error: %s", e)
                    time.sleep(0.5)

        threading.Thread(target=_loop, daemon=True).start()
        return "Continuous voice mode started. Say 'hey Apex' to speak."

    # ── COMMAND HANDLING ────────────────────────────────────

    def _handle_command(self, raw_text: str):
        """
        Main command dispatcher.
        Order: routine control -> routine recording -> shortcut expand -> LLM passthrough
        """
        text = raw_text.strip()
        text_lower = text.lower()
        log.info("Voice command: %s", text)
        print("\n[VOICE] %s" % text)

        # ── Routine: start recording ──────────────────────
        if text_lower.startswith("start recording routine"):
            name = text_lower.replace("start recording routine", "").strip()
            result = self.recorder.start(name or "unnamed_routine")
            self.speak(result)
            return

        if text_lower.startswith("record routine"):
            name = text_lower.replace("record routine", "").strip()
            result = self.recorder.start(name or "unnamed_routine")
            self.speak(result)
            return

        # ── Routine: stop recording ───────────────────────
        if text_lower in ("stop recording", "done recording", "finish recording", "save routine"):
            name = self.recorder.stop()
            if name:
                n = len(self.recorder.routines.get(name, []))
                self.speak("Routine %s saved with %d steps." % (name.replace('_', ' '), n))
            else:
                self.speak("No active recording to stop.")
            return

        # ── Routine: playback ─────────────────────────────
        if text_lower.startswith(("run routine", "play routine", "execute routine", "replay routine")):
            for prefix in ("run routine", "play routine", "execute routine", "replay routine"):
                if text_lower.startswith(prefix):
                    name = text_lower[len(prefix):].strip()
                    break
            self._run_routine(name)
            return

        # ── Routine: list ─────────────────────────────────
        if text_lower in ("list routines", "what routines", "show routines", "my routines"):
            routines = self.recorder.list_routines()
            if routines:
                self.speak("Saved routines: %s" % ', '.join(r.replace('_', ' ') for r in routines))
            else:
                self.speak("No routines saved yet.")
            return

        # ── Routine: delete ───────────────────────────────
        if text_lower.startswith("delete routine"):
            name = text_lower.replace("delete routine", "").strip()
            if self.recorder.delete_routine(name):
                self.speak("Routine %s deleted." % name)
            else:
                self.speak("No routine named %s found." % name)
            return

        # ── Record step if active ─────────────────────────
        if self.recorder.recording:
            self.recorder.add_step(text)
            print("[RECORDED] Step %d: %s" % (len(self.recorder.steps), text))

        # ── Expand shortcut or pass to agent ──────────────
        expanded = self._expand_shortcut(text_lower) or text
        self._write_to_agent(expanded)

        self.history.append({
            "ts": datetime.now().isoformat(),
            "raw": text,
            "expanded": expanded
        })

    def _expand_shortcut(self, text_lower: str) -> Optional[str]:
        """
        Check if text matches a shortcut.
        Exact match first, then starts-with for commands with trailing context.
        """
        if text_lower in VOICE_SHORTCUTS:
            return VOICE_SHORTCUTS[text_lower]

        for shortcut, expansion in VOICE_SHORTCUTS.items():
            if text_lower.startswith(shortcut + " "):
                remainder = text_lower[len(shortcut):].strip()
                return "%s %s" % (expansion, remainder)

        return None

    def _write_to_agent(self, command: str):
        """Send a command to the agent's think() method."""
        if self.think:
            try:
                print("-> Agent: %s" % command[:100])
                response = self.think(command)
                if response:
                    if self.say_fn:
                        self.say_fn(response)
                    else:
                        self.speak(response)
            except Exception as e:
                log.error("Agent think() error: %s", e)
                self.speak("Error processing that command.")
        else:
            print("[VOICE] No agent callback -- command was: %s" % command)

    def _run_routine(self, name: str):
        """Play back a saved routine step by step."""
        steps = self.recorder.get_routine(name)
        if not steps:
            all_routines = self.recorder.list_routines()
            close = [r for r in all_routines if name.replace(" ", "_") in r or r in name.replace(" ", "_")]
            if close:
                steps = self.recorder.get_routine(close[0])
                name = close[0]
        if not steps:
            self.speak("No routine named %s found. Say 'list routines' to see what is saved." % name)
            return

        n = len(steps)
        self.speak("Running routine %s -- %d steps." % (name.replace('_', ' '), n))
        for i, step in enumerate(steps, 1):
            print("[ROUTINE] Step %d/%d: %s" % (i, n, step))
            expanded = self._expand_shortcut(step.lower()) or step
            self._write_to_agent(expanded)
            time.sleep(2.5)

        self.speak("Routine %s complete." % name.replace('_', ' '))

    # ── STATUS ──────────────────────────────────────────────

    def get_status(self) -> str:
        sr_status = "YES" if SR_AVAILABLE else "NO -- pip install SpeechRecognition"
        kb_status = "YES" if KEYBOARD_AVAILABLE else "NO -- pip install keyboard"
        return (
            "Voice System Status:\n"
            "  Listening:      %s\n"
            "  PTT mode:       %s\n"
            "  PTT key:        %s\n"
            "  TTS engine:     %s\n"
            "  SR available:   %s\n"
            "  keyboard pkg:   %s\n"
            "  Wake words:     %s\n"
            "  Shortcuts:      %d\n"
            "  Routines saved: %d\n"
            "  Commands heard: %d"
        ) % (
            'YES' if self.listening else 'NO',
            'YES' if self.ptt_mode else 'NO',
            self.ptt_key,
            self._tts_mode,
            sr_status,
            kb_status,
            ', '.join(self.wake_words),
            len(VOICE_SHORTCUTS),
            len(self.recorder.list_routines()),
            len(self.history),
        )

    def list_shortcuts(self) -> str:
        """Show all recognized shortcut phrases grouped by category."""
        lines = ["VOICE SHORTCUTS (%d total):\n" % len(VOICE_SHORTCUTS)]
        categories = {}
        for phrase, cmd in VOICE_SHORTCUTS.items():
            cat = cmd[:40]
            categories.setdefault(cat, []).append(phrase)
        for cmd_preview, phrases in sorted(categories.items()):
            lines.append("  %s..." % cmd_preview[:50])
            for p in phrases[:3]:
                lines.append("    * '%s'" % p)
            if len(phrases) > 3:
                lines.append("    * ...and %d more" % (len(phrases) - 3))
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════
_voice_system: Optional[VoiceActivationSystem] = None


def get_voice_system(think_callback=None, say_callback=None) -> VoiceActivationSystem:
    global _voice_system
    if _voice_system is None:
        _voice_system = VoiceActivationSystem(
            think_callback=think_callback,
            say_callback=say_callback
        )
    else:
        if think_callback and not _voice_system.think:
            _voice_system.think = think_callback
        if say_callback and not _voice_system.say_fn:
            _voice_system.say_fn = say_callback
    return _voice_system


def get_voice_activation() -> VoiceActivationSystem:
    return get_voice_system()


def register_tools(registry) -> None:
    """Register voice activation tools with the Apex tool registry."""
    vs = get_voice_activation()
    registry.register("voice_start_push_to_talk", vs.start_push_to_talk)
    registry.register("voice_start_continuous", vs.start_continuous)
    registry.register("voice_stop", vs.stop)
    registry.register("voice_speak", vs.speak)
    registry.register("voice_get_status", vs.get_status)
    registry.register("voice_list_shortcuts", vs.list_shortcuts)


if __name__ == "__main__":
    print("Voice Activation System -- Standalone Test")
    print("=" * 55)

    def fake_think(text):
        print("  [Agent would process]: %s" % text)
        return "Got it: %s" % text[:60]

    va = VoiceActivationSystem(think_callback=fake_think)
    print(va.get_status())
    print("\nTotal shortcuts: %d" % len(VOICE_SHORTCUTS))
    print("\nSample phrases:")
    for phrase in list(VOICE_SHORTCUTS.keys())[:15]:
        print("  '%s'" % phrase)
    print("  ...and %d more" % (len(VOICE_SHORTCUTS) - 15))
    print("\nCommands:")
    print("  va.start_push_to_talk('F9')")
    print("  va.start_continuous()")
    print("  va.stop()")
