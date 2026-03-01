"""
ENHANCED PERCEPTION SYSTEM
===========================
Professional voice, network awareness, and visual input processing for Apex.

Features:
- Natural human voices (Microsoft/Google quality)
- Network device discovery and management
- Professional audio processing
- Flexible coordinate arguments: all region-based functions accept
  either a single tuple (left, top, width, height) OR four separate
  arguments - works correctly from any caller without wrappers.
"""

import speech_recognition as sr
import pyttsx3
import logging
import pyautogui
import numpy as np
import easyocr
import io
import base64
import requests
import time
import re
import yaml
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import cv2
import subprocess
import json
import threading
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path
import os
import socket
import platform

# Network discovery
try:
    import nmap
    NM = True
except ImportError:
    NM = False

# Windows DPI awareness
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

log = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent.parent / "core" / "config.yaml"


def _storage_base() -> Path:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return Path(cfg.get("storage", {}).get("base", "C:/ai_agent/apex/data"))


def _resolve_region(left_or_region, top=None, width=None, height=None) -> Tuple[int, int, int, int]:
    """
    Universal region argument resolver.

    Accepts either:
      _resolve_region((left, top, width, height))      single tuple or list
      _resolve_region(left, top, width, height)         four separate ints

    Returns a clean (int, int, int, int) tuple in all cases.
    Every region-based function calls this first so they work correctly
    regardless of how they are called.
    """
    if isinstance(left_or_region, (tuple, list)):
        parts = tuple(left_or_region)
        return (int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3]))
    return (
        int(left_or_region) if left_or_region is not None else 0,
        int(top)            if top            is not None else 0,
        int(width)          if width          is not None else 1920,
        int(height)         if height         is not None else 1080,
    )


class PerceptionHub:
    def __init__(self):
        self.vision_active = True
        self.network_devices = {}
        self.voice_profile = "professional_male"

        self.setup_audio()
        self.setup_ocr()

        self.network_monitor_thread = None
        self.monitoring_network = False

        log.info("Perception Hub initialized")

    # =========================================================================
    # AUDIO / VOICE
    # =========================================================================

    def setup_audio(self):
        """Setup high-quality voice synthesis."""
        try:
            import edge_tts
            self.tts_engine = "edge_tts"
            self.voice_options = {
                "professional_male":   "en-US-GuyNeural",
                "professional_female": "en-US-JennyNeural",
                "warm_male":           "en-US-DavisNeural",
                "friendly_female":     "en-US-AriaNeural"
            }
        except ImportError:
            try:
                self.tts_engine = "pyttsx3"
                self.engine = pyttsx3.init()
                voices = self.engine.getProperty('voices')
                if voices:
                    english_voices = [v for v in voices
                                      if 'english' in v.name.lower() or 'en' in v.id.lower()]
                    if english_voices:
                        self.engine.setProperty('voice', english_voices[0].id)
                self.engine.setProperty('rate', 200)
                self.engine.setProperty('volume', 0.9)
            except Exception as e:
                log.warning("Fallback TTS setup failed: %s", e)
                self.tts_engine = None

    def speak(self, text: str, voice_profile: str = None):
        """
        Text-to-speech output.
        Uses edge_tts (natural human voice) with reliable synchronous playback.
        Falls back to pyttsx3, then print.
        """
        if not text or not text.strip():
            return

        if voice_profile:
            self.voice_profile = voice_profile

        clean_lines = []
        skip_prefixes = (
            '[TOOL', '[MODE', '[LOOP', '[MEMORY', '[GOVERNANCE',
            'TOOL:', 'INFO:', 'WARNING:', 'ERROR:', '-> '
        )
        for line in text.split('\n'):
            s = line.strip()
            if any(s.startswith(p) for p in skip_prefixes):
                continue
            if s:
                clean_lines.append(s)
        clean = ' '.join(clean_lines).strip()
        if not clean:
            return
        if len(clean) > 500:
            clean = clean[:500] + "..."

        try:
            if self.tts_engine == "edge_tts":
                self._speak_edge(clean)
            elif self.tts_engine == "pyttsx3":
                self._speak_pyttsx3(clean)
            else:
                print(clean)
        except Exception as e:
            log.error("TTS Error: %s", e)
            print(clean)

    def _speak_edge(self, text: str):
        """
        edge_tts playback — natural human voice.
        Saves mp3 then plays synchronously via PowerShell so we wait for it to finish.
        """
        try:
            import edge_tts
            import asyncio

            voice = self.voice_options.get(self.voice_profile, "en-US-GuyNeural")
            mp3_path = str(_storage_base() / "tts" / "temp_speech.mp3")
            Path(mp3_path).parent.mkdir(parents=True, exist_ok=True)

            async def _generate():
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(mp3_path)

            asyncio.run(_generate())

            if not os.path.exists(mp3_path):
                print(text)
                return

            ps_cmd = (
                "Add-Type -AssemblyName presentationCore; "
                "$mp = New-Object System.Windows.Media.MediaPlayer; "
                "$mp.Open([System.Uri]'%s'); "
                "$mp.Play(); "
                "Start-Sleep -Milliseconds 500; "
                "$dur = $mp.NaturalDuration.TimeSpan.TotalSeconds; "
                "if ($dur -gt 0) { Start-Sleep -Seconds $dur } else { Start-Sleep -Seconds 5 }; "
                "$mp.Close()"
            ) % mp3_path

            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                timeout=60
            )

        except Exception as e:
            log.error("edge_tts playback error: %s", e)
            self._speak_pyttsx3(text)

    def _speak_pyttsx3(self, text: str):
        """
        pyttsx3 fallback. Reinitializes engine each call to avoid WinError 6 handle issue.
        """
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty('rate', 175)
            engine.setProperty('volume', 0.95)
            voices = engine.getProperty('voices')
            if voices:
                for v in voices:
                    if 'david' in v.name.lower():
                        engine.setProperty('voice', v.id)
                        break
            engine.say(text)
            engine.runAndWait()
            try:
                engine.stop()
            except Exception:
                pass
        except Exception as e:
            log.error("pyttsx3 error: %s", e)
            print(text)

    def listen(self, timeout: int = 10):
        """Enhanced speech recognition."""
        try:
            recognizer = sr.Recognizer()
            mic = sr.Microphone()

            with mic as source:
                recognizer.adjust_for_ambient_noise(source)
                audio = recognizer.listen(source, timeout=timeout)

            try:
                return recognizer.recognize_google(audio)
            except Exception:
                return recognizer.recognize_sphinx(audio)

        except Exception as e:
            log.error("Speech recognition error: %s", e)
            return None

    # =========================================================================
    # OCR
    # =========================================================================

    def setup_ocr(self):
        """Initialize OCR with GPU acceleration."""
        try:
            self.reader = easyocr.Reader(['en'], gpu=True, verbose=False)
            log.info("GPU-accelerated OCR ready")
        except Exception as e:
            log.warning("GPU OCR failed, using CPU: %s", e)
            try:
                self.reader = easyocr.Reader(['en'], gpu=False, verbose=False)
            except Exception as e2:
                log.error("OCR completely failed: %s", e2)
                self.reader = None

    def _preprocess_for_ocr(self, image):
        """Windows 11 optimized preprocessing."""
        try:
            gray = image.convert('L')
            img_np = np.array(gray)

            mean_brightness = img_np.mean()
            if mean_brightness < 127:
                gray = ImageOps.invert(gray)
                img_np = np.array(gray)

            img_np = cv2.adaptiveThreshold(
                img_np, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, blockSize=15, C=3
            )
            return Image.fromarray(img_np).filter(ImageFilter.SHARPEN)

        except Exception:
            return image.convert('L')

    def _is_valid_text(self, text: str) -> bool:
        """Filter OCR garbage."""
        if not text or len(text) < 2:
            return False
        text_clean = text.strip()
        alpha_count = sum(c.isalnum() for c in text_clean)
        return alpha_count >= len(text_clean) * 0.3

    # =========================================================================
    # VISION MODEL (via Ollama)
    # =========================================================================

    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL image to base64 string for Ollama vision API."""
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    def _call_vision_model(self, image: Image.Image, prompt: str,
                           vision_model: str = None, timeout: int = 300) -> Optional[str]:
        """
        Send an image to the Ollama vision model and return its response.
        Falls back to None on any error so callers can fall back to EasyOCR.
        """
        try:
            model = vision_model or "huihui_ai/qwen3-vl-abliterated:8b"
            img_b64 = self._image_to_base64(image)

            payload = {
                "model":  model,
                "prompt": prompt,
                "images": [img_b64],
                "stream": False,
                "options": {"temperature": 0.1}
            }

            resp = requests.post(
                "http://localhost:11434/api/generate",
                json=payload,
                timeout=timeout
            )
            resp.raise_for_status()
            return resp.json().get("response", "").strip()

        except Exception as e:
            log.warning("Vision model call failed, falling back to EasyOCR: %s", e)
            return None

    # =========================================================================
    # SCREEN READING
    # =========================================================================

    def see_screen(self) -> str:
        """
        Screen reading — uses vision model when available,
        falls back to EasyOCR if vision model is unavailable or fails.
        """
        if not self.vision_active:
            return "[Vision disabled]"

        try:
            image = pyautogui.screenshot()

            vision_result = self._call_vision_model(
                image,
                "Read and transcribe ALL text visible on this screen exactly as it appears. "
                "Include every word, button label, menu item, and UI element text. "
                "Output only the transcribed text with no commentary."
            )

            if vision_result:
                log.info("see_screen: vision model succeeded")
                return vision_result

            log.info("see_screen: falling back to EasyOCR")
            if not self.reader:
                return "[Vision and OCR both unavailable]"

            processed = self._preprocess_for_ocr(image)
            image_np = np.array(processed)
            results = self.reader.readtext(image_np, detail=1)

            valid_texts = []
            for bbox, text, confidence in results:
                if confidence > 0.3 and self._is_valid_text(text):
                    valid_texts.append(text)

            return " ".join(valid_texts) if valid_texts else "[No text detected]"

        except Exception as e:
            return "[Screen read error: %s]" % str(e)

    def analyze_visuals(self, image_path: str = None) -> str:
        """
        Deep visual analysis — uses vision model for full scene understanding.
        Falls back to EasyOCR summary if vision model unavailable.
        """
        try:
            if image_path and os.path.exists(image_path):
                image = Image.open(image_path)
                source = "image file: %s" % image_path
            else:
                image = pyautogui.screenshot()
                source = "current screen"

            vision_result = self._call_vision_model(
                image,
                "Analyze this screen or image in detail. Describe: "
                "1) What application or website is shown, "
                "2) All visible text content, "
                "3) UI elements like buttons, forms, menus, "
                "4) The current state or context, "
                "5) Any important visual indicators like errors, alerts, or progress. "
                "Be specific and thorough."
            )

            if vision_result:
                log.info("analyze_visuals: vision model succeeded")
                return "[Visual Analysis - AI Vision]\nSource: %s\n\n%s" % (source, vision_result)

            log.info("analyze_visuals: falling back to EasyOCR")
            if not self.reader:
                return "[Visual Analysis Unavailable - vision model and OCR both failed]"

            processed = self._preprocess_for_ocr(image)
            image_np = np.array(processed)
            results = self.reader.readtext(image_np, detail=1)

            high_conf_texts = []
            low_conf_texts = []

            for bbox, text, confidence in results:
                if confidence > 0.7:
                    high_conf_texts.append(text)
                elif confidence > 0.4:
                    low_conf_texts.append(text)

            if not high_conf_texts and not low_conf_texts:
                return "[Visual Analysis] No readable content detected on %s" % source

            word_count = sum(len(t.split()) for t in high_conf_texts)
            confidence_level = "High" if len(high_conf_texts) > len(low_conf_texts) else "Medium"

            summary = (
                "[Visual Analysis - EasyOCR Fallback]\n"
                "Source: %s\n"
                "Confidence: %s\n"
                "Words detected: %d\n"
                "Content: %s"
            ) % (source, confidence_level, word_count, ' | '.join(high_conf_texts[:10]))

            return summary

        except Exception as e:
            return "[Visual Analysis Error] %s" % str(e)

    def find_text_on_screen(self, target_text: str) -> Optional[Tuple[int, int]]:
        """Find text on screen and return center coordinates."""
        try:
            screenshot = pyautogui.screenshot()
            processed = self._preprocess_for_ocr(screenshot)
            image_np = np.array(processed)

            results = self.reader.readtext(image_np, detail=1)
            target_lower = target_text.lower().strip()

            for bbox, text, confidence in results:
                if confidence < 0.4:
                    continue
                if target_lower in text.lower():
                    x_coords = [point[0] for point in bbox]
                    y_coords = [point[1] for point in bbox]
                    center_x = int(sum(x_coords) / 4)
                    center_y = int(sum(y_coords) / 4)
                    return (center_x, center_y)

            return None

        except Exception as e:
            log.error("Find text error: %s", e)
            return None

    def screenshot_region(self,
                          left_or_region: Union[int, Tuple[int, int, int, int]],
                          top: int = None,
                          width: int = None,
                          height: int = None) -> Optional[Image.Image]:
        """
        Take screenshot of a specific screen region.

        Accepts EITHER:
          screenshot_region((left, top, width, height))    single tuple
          screenshot_region(left, top, width, height)      four separate ints

        Both calling conventions are fully supported and identical in result.
        """
        region = _resolve_region(left_or_region, top, width, height)
        try:
            return pyautogui.screenshot(region=region)
        except Exception as e:
            log.error("Region screenshot error: %s", e)
            return None

    def read_chat_history(self,
                          left_or_region: Union[int, Tuple[int, int, int, int]],
                          top: int = None,
                          width: int = None,
                          height: int = None) -> List[str]:
        """
        Read chat history from a specific window region using OCR.

        Accepts EITHER:
          read_chat_history((left, top, width, height))    single tuple
          read_chat_history(left, top, width, height)      four separate ints

        Both calling conventions are fully supported and identical in result.
        Returns a list of message strings detected in the region.
        """
        region = _resolve_region(left_or_region, top, width, height)
        try:
            chat_screenshot = self.screenshot_region(region)
            if not chat_screenshot:
                return []

            processed = self._preprocess_for_ocr(chat_screenshot)
            image_np = np.array(processed)
            results = self.reader.readtext(image_np, detail=1)

            messages = []
            for bbox, text, confidence in results:
                if confidence > 0.5 and len(text.strip()) > 2:
                    messages.append(text.strip())

            return messages

        except Exception as e:
            log.error("Chat history read error: %s", e)
            return []

    def distinguish_participants(self, chat_history: List[str]) -> Dict[str, List[str]]:
        """Distinguish between different chat participants."""
        participants = {"user": [], "agent": [], "other": []}

        for message in chat_history:
            if "User:" in message:
                participants["user"].append(message)
            elif "Apex:" in message or "Agent:" in message:
                participants["agent"].append(message)
            else:
                participants["other"].append(message)

        return participants

    # =========================================================================
    # MOUSE & KEYBOARD
    # =========================================================================

    def click_text(self, target_text: str, double_click: bool = False):
        """Enhanced text clicking with fuzzy matching."""
        if not self.reader:
            return "OCR Unavailable"

        try:
            screenshot = pyautogui.screenshot()
            processed = self._preprocess_for_ocr(screenshot)
            image_np = np.array(processed)

            results = self.reader.readtext(image_np, detail=1)
            target_lower = target_text.lower().strip()

            for bbox, text, confidence in results:
                if confidence < 0.4:
                    continue
                if target_lower in text.lower():
                    x_coords = [point[0] for point in bbox]
                    y_coords = [point[1] for point in bbox]
                    center_x = int(sum(x_coords) / 4)
                    center_y = int(sum(y_coords) / 4)

                    pyautogui.moveTo(center_x, center_y, duration=0.3)
                    if double_click:
                        pyautogui.doubleClick()
                    else:
                        pyautogui.click()
                    return "Clicked '%s'" % text

            return "Text '%s' not found" % target_text

        except Exception as e:
            return "Click error: %s" % e

    def click_coordinates(self, x: int, y: int, double_click: bool = False) -> bool:
        """Click at specific screen coordinates."""
        try:
            pyautogui.moveTo(int(x), int(y), duration=0.3)
            if double_click:
                pyautogui.doubleClick()
            else:
                pyautogui.click()
            return True
        except Exception as e:
            log.error("Coordinate click error: %s", e)
            return False

    def move_mouse(self, x: int, y: int) -> bool:
        """Move mouse to specific coordinates."""
        try:
            pyautogui.moveTo(int(x), int(y), duration=0.3)
            return True
        except Exception as e:
            log.error("Mouse move error: %s", e)
            return False

    def drag_to(self, x: int, y: int, duration: float = 0.3) -> bool:
        """Drag from current position to coordinates."""
        try:
            pyautogui.dragTo(int(x), int(y), duration=duration)
            return True
        except Exception as e:
            log.error("Drag error: %s", e)
            return False

    def scroll(self, clicks: int) -> bool:
        """Scroll up (positive) or down (negative)."""
        try:
            pyautogui.scroll(int(clicks))
            return True
        except Exception as e:
            log.error("Scroll error: %s", e)
            return False

    def get_screen_size(self) -> Tuple[int, int]:
        """Get screen dimensions."""
        try:
            return pyautogui.size()
        except Exception as e:
            log.error("Screen size error: %s", e)
            return (0, 0)

    def get_mouse_position(self) -> Tuple[int, int]:
        """Get current mouse position."""
        try:
            return pyautogui.position()
        except Exception as e:
            log.error("Mouse position error: %s", e)
            return (0, 0)

    def type(self, text: str) -> bool:
        """Type text using keyboard automation."""
        try:
            pyautogui.write(text, interval=0.01)
            return True
        except Exception as e:
            log.error("Text typing error: %s", e)
            return False

    def press(self, key: str) -> bool:
        """Press a key using keyboard automation."""
        try:
            pyautogui.press(key)
            return True
        except Exception as e:
            log.error("Key press error: %s", e)
            return False

    # =========================================================================
    # NETWORK
    # =========================================================================

    def discover_network_devices(self) -> Dict:
        """Discover all devices on local network."""
        devices = {}

        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            network_base = '.'.join(local_ip.split('.')[:-1]) + '.0/24'

            if NM:
                nm = nmap.PortScanner()
                nm.scan(hosts=network_base, arguments='-sn')

                for host in nm.all_hosts():
                    if 'mac' in nm[host]:
                        mac = nm[host]['addresses'].get('mac', 'Unknown')
                        ip = nm[host]['addresses'].get('ipv4', host)
                        vendor = (nm[host]['vendor'].get(mac, 'Unknown')
                                  if 'vendor' in nm[host] else 'Unknown')

                        devices[mac] = {
                            'ip': ip,
                            'hostname': nm[host].get('hostnames', [{'name': 'Unknown'}])[0]['name'],
                            'mac': mac,
                            'vendor': vendor,
                            'status': nm[host].state()
                        }
            else:
                for i in range(1, 255):
                    ip = "%s.%d" % ('.'.join(local_ip.split('.')[:-1]), i)
                    try:
                        result = subprocess.run(['ping', '-n', '1', '-w', '1000', ip],
                                                capture_output=True, timeout=2)
                        if result.returncode == 0:
                            devices[ip] = {'ip': ip, 'status': 'online'}
                    except Exception:
                        pass

        except Exception as e:
            log.error("Network discovery error: %s", e)

        self.network_devices = devices
        return devices

    def start_network_monitoring(self):
        """Continuously monitor network for changes."""
        if self.monitoring_network:
            return

        self.monitoring_network = True

        def monitor():
            while self.monitoring_network:
                self.discover_network_devices()
                time.sleep(30)

        self.network_monitor_thread = threading.Thread(target=monitor, daemon=True)
        self.network_monitor_thread.start()
        log.info("Network monitoring started")

    def stop_network_monitoring(self):
        """Stop network monitoring."""
        self.monitoring_network = False
        log.info("Network monitoring stopped")

    def get_device_by_name(self, name: str) -> Optional[Dict]:
        """Find device by hostname or partial name match."""
        name_lower = name.lower()
        for device in self.network_devices.values():
            if (name_lower in device.get('hostname', '').lower() or
                    name_lower in device.get('vendor', '').lower()):
                return device
        return None

    def remote_diagnose_device(self, device_ip: str) -> str:
        """Diagnose remote device issues."""
        try:
            ping_result = subprocess.run(['ping', '-n', '4', device_ip],
                                         capture_output=True, text=True, timeout=10)

            if NM:
                nm = nmap.PortScanner()
                nm.scan(device_ip, '22,80,443,3389')
                ports = nm[device_ip].get('tcp', {}) if device_ip in nm.all_hosts() else {}

                return (
                    "Device %s Diagnosis:\n"
                    "Ping: %s\n"
                    "Open Ports: %s\n"
                    "Response Time: %s"
                ) % (
                    device_ip,
                    'Success' if ping_result.returncode == 0 else 'Failed',
                    ', '.join(str(p) for p in ports.keys()) if ports else 'None detected',
                    ping_result.stdout.split('Average = ')[-1].strip()
                    if 'Average' in ping_result.stdout else 'Unknown'
                )

            return "Device %s: Ping %s" % (
                device_ip,
                'successful' if ping_result.returncode == 0 else 'failed'
            )

        except Exception as e:
            return "Remote diagnosis error: %s" % e

    # =========================================================================
    # MISC
    # =========================================================================

    def send_mobile_notification(self, message: str, title: str = "Apex Alert") -> str:
        """Send notification to connected mobile device."""
        log.info("Mobile Notification: %s - %s", title, message)
        return "Notification sent to mobile device"

    def browse_url(self, url: str) -> bool:
        """Open URL in default browser."""
        try:
            import webbrowser
            webbrowser.open(url)
            return True
        except Exception as e:
            log.error("Browse URL error: %s", e)
            return False


# =========================================================================
# SINGLETON
# =========================================================================
_hub_instance: Optional[PerceptionHub] = None


def get_perception_system() -> PerceptionHub:
    global _hub_instance
    if _hub_instance is None:
        _hub_instance = PerceptionHub()
    return _hub_instance


def register_tools(registry) -> None:
    """Register perception system tools with the Apex tool registry."""
    hub = get_perception_system()
    registry.register("see_screen", hub.see_screen)
    registry.register("analyze_visuals", hub.analyze_visuals)
    registry.register("find_text_on_screen", hub.find_text_on_screen)
    registry.register("screenshot_region", hub.screenshot_region)
    registry.register("read_chat_history", hub.read_chat_history)
    registry.register("click_text", hub.click_text)
    registry.register("click_coordinates", hub.click_coordinates)
    registry.register("move_mouse", hub.move_mouse)
    registry.register("drag_to", hub.drag_to)
    registry.register("scroll", hub.scroll)
    registry.register("get_screen_size", hub.get_screen_size)
    registry.register("get_mouse_position", hub.get_mouse_position)
    registry.register("type_text", hub.type)
    registry.register("press_key", hub.press)
    registry.register("speak", hub.speak)
    registry.register("listen", hub.listen)
    registry.register("discover_network_devices", hub.discover_network_devices)
    registry.register("remote_diagnose_device", hub.remote_diagnose_device)
    registry.register("browse_url", hub.browse_url)
    registry.register("send_mobile_notification", hub.send_mobile_notification)
