"""
AR Glasses Bridge — Augmented Reality Integration
==================================================
Connect Apex to AR glasses for visual overlays and assistance.

Features:
- Visual object highlighting
- Text overlay on real-world items
- Person recognition and info display
- Navigation assistance
- Real-time data overlay
"""

import cv2
import numpy as np
import json
import time
import logging
import yaml
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass
from threading import Thread

log = logging.getLogger("apex.ar_glasses")

_CONFIG_PATH = Path(__file__).parent.parent / "core" / "config.yaml"


def _load_config() -> dict:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _get_camera_index() -> int:
    cfg = _load_config()
    return int(cfg.get("hardware", {}).get("ar_camera_index", 0))


@dataclass
class OverlayItem:
    """Represents an item to be overlaid in AR."""
    id: str
    text: str
    position: Tuple[int, int]
    type: str
    priority: int
    expiration: float
    color: Tuple[int, int, int] = (255, 255, 255)


class ARGlassesBridge:
    def __init__(self, camera_index=None):
        self.camera_index = camera_index if camera_index is not None else _get_camera_index()
        self.video_capture = None
        self.overlays: List[OverlayItem] = []
        self.running = False
        self.frame_callback = None
        self.object_detector = None

        self.initialize_cv()

    def initialize_cv(self):
        """Initialize computer vision components."""
        try:
            self.video_capture = cv2.VideoCapture(self.camera_index)
            if not self.video_capture.isOpened():
                log.warning("Could not open camera")
                self.video_capture = None

            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )

            log.info("AR Glasses Bridge initialized")
        except Exception as e:
            log.error("CV initialization error: %s", e)

    def add_overlay(self, text: str, position: Tuple[int, int],
                    overlay_type: str = "info", priority: int = 5,
                    duration: float = 30.0, color: Tuple[int, int, int] = (255, 255, 255)):
        """Add an overlay item to display."""
        overlay = OverlayItem(
            id="overlay_%d" % int(time.time() * 1000),
            text=text,
            position=position,
            type=overlay_type,
            priority=priority,
            expiration=time.time() + duration,
            color=color
        )
        self.overlays.append(overlay)
        log.info("Added overlay: %s", text)
        return overlay.id

    def remove_overlay(self, overlay_id: str):
        """Remove a specific overlay."""
        self.overlays = [o for o in self.overlays if o.id != overlay_id]
        log.info("Removed overlay: %s", overlay_id)

    def clear_overlays(self):
        """Clear all overlays."""
        self.overlays.clear()
        log.info("Cleared all overlays")

    def highlight_object(self, object_name: str, coordinates: Tuple[int, int]):
        """Highlight a specific object with bounding box."""
        self.add_overlay("Object: %s" % object_name, coordinates, "object_highlight", 8, 10.0, (0, 255, 0))

    def display_person_info(self, person_name: str, coordinates: Tuple[int, int], info: Dict):
        """Display person information overlay."""
        info_text = "%s\n" % person_name
        if info.get("birthday"):
            info_text += "Birthday: %s\n" % info["birthday"]
        if info.get("relationship"):
            info_text += "Relationship: %s\n" % info["relationship"]
        if info.get("notes"):
            info_text += "Notes: %s" % info["notes"]

        self.add_overlay(info_text.strip(), coordinates, "person_info", 9, 30.0, (255, 255, 0))

    def process_frame(self, frame):
        """Process video frame for object/person detection."""
        if frame is None:
            return frame

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
            self.highlight_object("Face Detected", (x, y - 20))

        self.apply_overlays(frame)
        return frame

    def apply_overlays(self, frame):
        """Apply all active overlays to the frame."""
        current_time = time.time()
        self.overlays = [o for o in self.overlays if o.expiration > current_time]

        sorted_overlays = sorted(self.overlays, key=lambda x: x.priority, reverse=True)

        for overlay in sorted_overlays[:5]:
            x, y = overlay.position
            h, w = frame.shape[:2]
            x = max(10, min(x, w - 200))
            y = max(20, min(y, h - 20))

            lines = overlay.text.split("\n")
            for i, line in enumerate(lines):
                cv2.putText(frame, line, (x, y + i * 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, overlay.color, 2)

    def start_camera_feed(self, callback=None):
        """Start processing camera feed."""
        if not self.video_capture:
            log.error("No camera available")
            return

        self.frame_callback = callback
        self.running = True

        def camera_thread():
            while self.running:
                ret, frame = self.video_capture.read()
                if ret:
                    processed_frame = self.process_frame(frame)
                    if self.frame_callback:
                        self.frame_callback(processed_frame)
                time.sleep(0.033)

        self.camera_thread = Thread(target=camera_thread)
        self.camera_thread.daemon = True
        self.camera_thread.start()
        log.info("Camera feed started")

    def stop_camera_feed(self):
        """Stop camera feed processing."""
        self.running = False
        if self.video_capture:
            self.video_capture.release()
        log.info("Camera feed stopped")

    def get_camera_frame(self):
        """Get a single frame from camera."""
        if not self.video_capture:
            return None

        ret, frame = self.video_capture.read()
        if ret:
            return self.process_frame(frame)
        return None

    def integrate_with_agent(self, agent_instance):
        """Integrate with the main Apex agent system."""
        def on_person_recognized(person_data):
            if person_data.get("name") and person_data.get("coordinates"):
                self.display_person_info(
                    person_data["name"],
                    person_data["coordinates"],
                    person_data.get("info", {})
                )

        def on_item_found(item_name, location):
            self.highlight_object(item_name, location)

        log.info("AR Glasses integrated with Apex agent")


# ── SINGLETON ─────────────────────────────────────────────────────────────────
_ar_glasses = None


def get_ar_glasses_bridge() -> ARGlassesBridge:
    """Return the singleton ARGlassesBridge instance."""
    global _ar_glasses
    if _ar_glasses is None:
        _ar_glasses = ARGlassesBridge()
    return _ar_glasses


def test_ar_glasses():
    """Test AR glasses functionality."""
    ar = get_ar_glasses_bridge()

    ar.add_overlay("Welcome to Apex AR!", (50, 50), "welcome", 10, 60.0, (0, 255, 255))
    ar.add_overlay("Person: John Doe\nBirthday: Jan 15", (100, 100), "person_info", 8, 30.0, (255, 255, 0))
    ar.add_overlay("Item: Keys\nLocation: Kitchen Counter", (200, 200), "object_info", 7, 20.0, (0, 255, 0))

    print("AR Glasses Bridge Test")
    print("Overlays added. Call start_camera_feed() to see them in action.")
    return ar


# ── TOOL REGISTRY ─────────────────────────────────────────────────────────────
def register_tools(registry) -> None:
    """Register AR glasses tools with the agent tool registry."""
    ar = get_ar_glasses_bridge()
    registry.register(
        "ar_add_overlay",
        ar.add_overlay,
        description="Add a text overlay to the AR glasses display"
    )
    registry.register(
        "ar_remove_overlay",
        ar.remove_overlay,
        description="Remove an overlay from the AR glasses display by ID"
    )
    registry.register(
        "ar_clear_overlays",
        ar.clear_overlays,
        description="Clear all active AR overlays"
    )
    registry.register(
        "ar_highlight_object",
        ar.highlight_object,
        description="Highlight a detected object with an AR bounding box overlay"
    )
    registry.register(
        "ar_display_person_info",
        ar.display_person_info,
        description="Display person info as an AR overlay"
    )
    registry.register(
        "ar_get_frame",
        ar.get_camera_frame,
        description="Capture and return a single processed camera frame"
    )


if __name__ == "__main__":
    test_ar_glasses()
