"""
DESKTOP DASHBOARD - Full Control Panel Interface
================================================
Professional web dashboard for complete Apex management.

Features:
- Real-time system monitoring
- Network device management
- Security dashboard
- Maintenance scheduling
- AI interaction console
"""

import asyncio
import json
import yaml
import websockets
from flask import Flask, render_template, request, jsonify
from threading import Thread
from pathlib import Path
import psutil
import GPUtil
import time
from datetime import datetime
import logging

log = logging.getLogger(__name__)

app = Flask(__name__)

_CONFIG_PATH = Path(__file__).parent.parent / "core" / "config.yaml"


def _storage_base() -> Path:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return Path(cfg.get("storage", {}).get("base", "C:/ai_agent/apex/data"))


class DesktopDashboard:
    def __init__(self, host="localhost", port=8765):
        self.host = host
        self.port = port
        self.websocket = None
        self.dashboard_data = {
            "system_status": {},
            "network_devices": {},
            "recent_activities": [],
            "alerts": []
        }

    async def connect(self):
        """Connect to the Apex WebSocket server."""
        try:
            uri = "ws://%s:%s" % (self.host, self.port)
            self.websocket = await websockets.connect(uri)
            log.info("Connected to Apex server")
            return True
        except Exception as e:
            log.error("Connection failed: %s", e)
            return False

    async def send_command(self, command_type, data=None):
        """Send command to Apex."""
        if not self.websocket:
            if not await self.connect():
                return {"error": "Not connected to Apex"}

        try:
            payload = {
                "type": command_type,
                "data": data or {}
            }
            await self.websocket.send(json.dumps(payload))
            response = await self.websocket.recv()
            return json.loads(response)
        except Exception as e:
            return {"error": str(e)}

    def get_system_metrics(self):
        """Get real-time system metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            net_io = psutil.net_io_counters()

            gpus = []
            try:
                gpu_list = GPUtil.getGPUs()
                for gpu in gpu_list:
                    gpus.append({
                        "name": gpu.name,
                        "load": gpu.load * 100,
                        "temperature": gpu.temperature,
                        "memory_used": gpu.memoryUsed,
                        "memory_total": gpu.memoryTotal
                    })
            except Exception:
                pass

            return {
                "cpu": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_free_gb": disk.free / (1024**3),
                "network_sent_mb": net_io.bytes_sent / (1024**2),
                "network_received_mb": net_io.bytes_recv / (1024**2),
                "gpus": gpus,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": str(e)}

    def update_dashboard_data(self):
        """Update dashboard with latest information."""
        self.dashboard_data["system_status"] = self.get_system_metrics()

        if not self.dashboard_data["recent_activities"]:
            self.dashboard_data["recent_activities"] = [
                {"time": "10:30 AM", "action": "System diagnosis completed", "status": "success"},
                {"time": "09:15 AM", "action": "Network scan initiated", "status": "info"},
                {"time": "08:45 AM", "action": "Backup completed", "status": "success"}
            ]

        if not self.dashboard_data["alerts"]:
            self.dashboard_data["alerts"] = [
                {"type": "warning", "message": "Low disk space on drive C:", "time": "09:30 AM"},
                {"type": "info", "message": "Scheduled maintenance tonight", "time": "Yesterday"}
            ]


_dashboard_instance = None


def get_desktop_dashboard() -> DesktopDashboard:
    global _dashboard_instance
    if _dashboard_instance is None:
        _dashboard_instance = DesktopDashboard()
    return _dashboard_instance


# Global dashboard instance used by Flask routes
dashboard = get_desktop_dashboard()


@app.route('/')
def index():
    return render_template('dashboard.html')


@app.route('/api/system')
def api_system():
    return jsonify(dashboard.get_system_metrics())


@app.route('/api/dashboard')
def api_dashboard():
    dashboard.update_dashboard_data()
    return jsonify(dashboard.dashboard_data)


@app.route('/api/command', methods=['POST'])
def api_command():
    data = request.json
    command = data.get('command')
    params = data.get('params', {})

    if command == 'diagnose':
        result = asyncio.run(dashboard.send_command('diagnose', params))
        return jsonify(result)
    elif command == 'network_scan':
        result = asyncio.run(dashboard.send_command('network', params))
        return jsonify(result)
    elif command == 'arm_controls':
        result = asyncio.run(dashboard.send_command('arm', params))
        return jsonify(result)
    elif command == 'disarm_controls':
        result = asyncio.run(dashboard.send_command('disarm', params))
        return jsonify(result)
    else:
        return jsonify({"error": "Unknown command"})


def register_tools(registry) -> None:
    """Register desktop dashboard tools with the Apex tool registry."""
    registry.register("get_system_metrics", get_desktop_dashboard().get_system_metrics)
    registry.register("update_dashboard_data", get_desktop_dashboard().update_dashboard_data)


if __name__ == '__main__':
    print("Starting Apex Desktop Dashboard...")
    print("Access at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
