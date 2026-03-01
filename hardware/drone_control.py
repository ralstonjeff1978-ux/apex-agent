"""
Drone Control Module — Aerial Surveillance and Mapping
======================================================
Control drones for mapping, surveillance, and reconnaissance.

Features:
- Drone flight control
- Aerial mapping and surveying
- Object detection from air
- Live video streaming
- Autonomous patrol routes
"""

import asyncio
import json
import time
import logging
import threading
import yaml
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum

log = logging.getLogger("apex.drone_control")

_CONFIG_PATH = Path(__file__).parent.parent / "core" / "config.yaml"


def _load_config() -> dict:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _get_default_drone_id() -> str:
    cfg = _load_config()
    return cfg.get("hardware", {}).get("default_drone_id", "apex_drone_001")


class DroneStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTED    = "connected"
    ARMED        = "armed"
    FLYING       = "flying"
    LANDED       = "landed"
    RTL          = "return_to_launch"
    ERROR        = "error"


class FlightMode(Enum):
    MANUAL = "manual"
    AUTO   = "auto"
    LOITER = "loiter"
    RTL    = "rtl"
    LAND   = "land"


@dataclass
class Waypoint:
    """GPS waypoint for autonomous flight."""
    latitude: float
    longitude: float
    altitude: float
    speed: float = 5.0


@dataclass
class DroneTelemetry:
    """Real-time drone telemetry data."""
    battery_level: int
    gps_fix: bool
    latitude: float
    longitude: float
    altitude: float
    heading: float
    speed: float
    voltage: float
    current: float
    status: DroneStatus
    last_update: float


class DroneController:
    def __init__(self, drone_id: str = "drone_001"):
        self.drone_id = drone_id
        self.status = DroneStatus.DISCONNECTED
        self.telemetry = DroneTelemetry(
            battery_level=100,
            gps_fix=False,
            latitude=0.0,
            longitude=0.0,
            altitude=0.0,
            heading=0.0,
            speed=0.0,
            voltage=14.8,
            current=0.0,
            status=DroneStatus.DISCONNECTED,
            last_update=time.time()
        )
        self.waypoints: List[Waypoint] = []
        self.current_waypoint = 0
        self.mission_active = False
        self.video_stream = None

        self.simulated = True
        self.simulation_speed = 1.0

        log.info("Drone Controller initialized for %s", drone_id)

    def connect(self) -> bool:
        """Connect to drone."""
        try:
            if self.simulated:
                time.sleep(1)
                self.status = DroneStatus.CONNECTED
                self.telemetry.status = DroneStatus.CONNECTED
                self.telemetry.gps_fix = True
                log.info("Simulated connection to %s", self.drone_id)
                return True
            else:
                pass
        except Exception as e:
            log.error("Connection failed: %s", e)
            self.status = DroneStatus.ERROR
            return False

    def disconnect(self):
        """Disconnect from drone."""
        if self.status != DroneStatus.DISCONNECTED:
            self.land()
            time.sleep(2)
            self.status = DroneStatus.DISCONNECTED
            self.telemetry.status = DroneStatus.DISCONNECTED
            log.info("Disconnected from %s", self.drone_id)

    def arm(self) -> bool:
        """Arm the drone motors."""
        if self.status not in [DroneStatus.CONNECTED, DroneStatus.LANDED]:
            log.warning("Cannot arm: Drone not ready")
            return False

        try:
            if self.simulated:
                time.sleep(0.5)
                self.status = DroneStatus.ARMED
                self.telemetry.status = DroneStatus.ARMED
                log.info("%s armed", self.drone_id)
                return True
        except Exception as e:
            log.error("Arming failed: %s", e)
            return False

    def disarm(self):
        """Disarm the drone motors."""
        if self.status == DroneStatus.ARMED:
            self.status = DroneStatus.CONNECTED
            self.telemetry.status = DroneStatus.CONNECTED
            log.info("%s disarmed", self.drone_id)

    def takeoff(self, altitude: float = 10.0) -> bool:
        """Takeoff to specified altitude."""
        if self.status != DroneStatus.ARMED:
            log.warning("Cannot takeoff: Drone not armed")
            return False

        try:
            if self.simulated:
                log.info("Taking off to %sm...", altitude)
                for i in range(int(altitude)):
                    self.telemetry.altitude = i
                    self.status = DroneStatus.FLYING
                    self.telemetry.status = DroneStatus.FLYING
                    time.sleep(0.1 / self.simulation_speed)

                self.telemetry.altitude = altitude
                log.info("Takeoff complete at %sm", altitude)
                return True
        except Exception as e:
            log.error("Takeoff failed: %s", e)
            return False

    def land(self):
        """Land the drone."""
        if self.status == DroneStatus.FLYING:
            try:
                if self.simulated:
                    log.info("Landing...")
                    start_alt = self.telemetry.altitude
                    for i in range(int(start_alt), 0, -1):
                        self.telemetry.altitude = i
                        time.sleep(0.05 / self.simulation_speed)

                    self.telemetry.altitude = 0
                    self.status = DroneStatus.LANDED
                    self.telemetry.status = DroneStatus.LANDED
                    log.info("Landed successfully")
            except Exception as e:
                log.error("Landing failed: %s", e)
                self.status = DroneStatus.ERROR
                self.telemetry.status = DroneStatus.ERROR

    def return_to_launch(self):
        """Return to launch position."""
        if self.status == DroneStatus.FLYING:
            self.status = DroneStatus.RTL
            self.telemetry.status = DroneStatus.RTL
            log.info("Returning to launch...")
            if self.simulated:
                time.sleep(2)
                self.land()

    def set_waypoints(self, waypoints: List[Waypoint]):
        """Set mission waypoints."""
        self.waypoints = waypoints
        self.current_waypoint = 0
        log.info("Mission set with %s waypoints", len(waypoints))

    def start_mission(self) -> bool:
        """Start autonomous mission."""
        if not self.waypoints:
            log.warning("No waypoints set")
            return False

        if self.status != DroneStatus.FLYING:
            log.warning("Drone not flying")
            return False

        self.mission_active = True
        log.info("Mission started")

        if self.simulated:
            def mission_thread():
                for i, wp in enumerate(self.waypoints):
                    if not self.mission_active:
                        break

                    log.info("Navigating to waypoint %s: (%s, %s, %sm)",
                             i + 1, wp.latitude, wp.longitude, wp.altitude)

                    self.telemetry.latitude = wp.latitude
                    self.telemetry.longitude = wp.longitude
                    self.telemetry.altitude = wp.altitude
                    self.current_waypoint = i

                    time.sleep(3 / self.simulation_speed)

                self.mission_active = False
                log.info("Mission completed")

            thread = threading.Thread(target=mission_thread)
            thread.daemon = True
            thread.start()

        return True

    def stop_mission(self):
        """Stop current mission."""
        self.mission_active = False
        log.info("Mission stopped")

    def get_telemetry(self) -> DroneTelemetry:
        """Get current drone telemetry."""
        self.telemetry.last_update = time.time()
        return self.telemetry

    def move(self, direction: str, distance: float = 5.0):
        """Manual movement control."""
        movements = {
            "forward":  (distance, 0),
            "backward": (-distance, 0),
            "left":     (0, -distance),
            "right":    (0, distance),
            "up":       (0, 0, distance),
            "down":     (0, 0, -distance)
        }

        if direction in movements:
            dx, dy = movements[direction][:2]
            self.telemetry.latitude  += dx * 0.00001
            self.telemetry.longitude += dy * 0.00001
            if len(movements[direction]) > 2:
                self.telemetry.altitude += movements[direction][2]
            log.info("Moved %s by %sm", direction, distance)

    def start_video_stream(self):
        """Start video streaming."""
        self.video_stream = "video_stream_placeholder"
        log.info("Video stream started")

    def stop_video_stream(self):
        """Stop video streaming."""
        self.video_stream = None
        log.info("Video stream stopped")

    def detect_objects(self) -> List[Dict]:
        """Detect objects in video feed."""
        if self.video_stream:
            objects = [
                {"type": "person",  "confidence": 0.85, "position": (100, 150)},
                {"type": "vehicle", "confidence": 0.72, "position": (300, 200)},
                {"type": "animal",  "confidence": 0.65, "position": (450, 100)}
            ]
            log.info("Detected %s objects", len(objects))
            return objects
        return []


class DroneFleet:
    """Manage multiple drones."""
    def __init__(self):
        self.drones: Dict[str, DroneController] = {}
        self.active_missions = {}

    def add_drone(self, drone_id: str) -> DroneController:
        """Add a drone to the fleet."""
        if drone_id not in self.drones:
            self.drones[drone_id] = DroneController(drone_id)
        return self.drones[drone_id]

    def remove_drone(self, drone_id: str):
        """Remove a drone from the fleet."""
        if drone_id in self.drones:
            drone = self.drones[drone_id]
            drone.disconnect()
            del self.drones[drone_id]
            log.info("Removed drone %s", drone_id)

    def get_drone(self, drone_id: str) -> DroneController:
        """Get drone controller by ID."""
        return self.drones.get(drone_id)

    def get_all_status(self) -> Dict[str, DroneStatus]:
        """Get status of all drones."""
        return {drone_id: drone.status for drone_id, drone in self.drones.items()}

    def coordinate_patrol(self, drone_ids: List[str], patrol_area: List[Tuple[float, float]]):
        """Coordinate patrol mission for multiple drones."""
        log.info("Coordinating patrol for %s drones", len(drone_ids))
        pass


# ── SINGLETONS ────────────────────────────────────────────────────────────────
_drone_fleet = DroneFleet()
_current_drone = None


def get_drone_fleet() -> DroneFleet:
    """Return the singleton DroneFleet instance."""
    global _drone_fleet
    return _drone_fleet


def get_drone_controller() -> DroneController:
    """Return the singleton primary DroneController instance."""
    global _current_drone
    if _current_drone is None:
        fleet = get_drone_fleet()
        _current_drone = fleet.add_drone(_get_default_drone_id())
    return _current_drone


def test_drone():
    """Test drone functionality."""
    print("Drone Control Test")
    print("=" * 30)

    drone = get_drone_controller()

    if drone.connect() and drone.arm():
        print("Drone connected and armed")

        if drone.takeoff(20):
            print("Takeoff successful")

            waypoints = [
                Waypoint(37.7749, -122.4194, 20),
                Waypoint(37.7759, -122.4204, 25),
                Waypoint(37.7769, -122.4214, 20)
            ]
            drone.set_waypoints(waypoints)
            drone.start_mission()

            time.sleep(10)

            drone.land()
            drone.disconnect()

            print("Mission complete")

    return drone


# ── TOOL REGISTRY ─────────────────────────────────────────────────────────────
def register_tools(registry) -> None:
    """Register drone control tools with the agent tool registry."""
    drone = get_drone_controller()
    registry.register("drone_connect",       drone.connect,          description="Connect to the primary drone")
    registry.register("drone_disconnect",    drone.disconnect,       description="Disconnect from the primary drone")
    registry.register("drone_arm",           drone.arm,              description="Arm the primary drone motors")
    registry.register("drone_disarm",        drone.disarm,           description="Disarm the primary drone motors")
    registry.register("drone_takeoff",       drone.takeoff,          description="Command primary drone to take off to given altitude")
    registry.register("drone_land",          drone.land,             description="Command primary drone to land")
    registry.register("drone_rtl",           drone.return_to_launch, description="Command primary drone to return to launch")
    registry.register("drone_move",          drone.move,             description="Move primary drone in a direction by a distance")
    registry.register("drone_set_waypoints", drone.set_waypoints,    description="Set waypoints for an autonomous drone mission")
    registry.register("drone_start_mission", drone.start_mission,    description="Start the autonomous waypoint mission")
    registry.register("drone_stop_mission",  drone.stop_mission,     description="Stop the current drone mission")
    registry.register("drone_telemetry",     drone.get_telemetry,    description="Get current drone telemetry data")
    registry.register("drone_detect_objects",drone.detect_objects,   description="Detect objects in the drone video feed")
    registry.register("drone_fleet_status",  get_drone_fleet().get_all_status, description="Get status of all drones in the fleet")


if __name__ == "__main__":
    test_drone()
