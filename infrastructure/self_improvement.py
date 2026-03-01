"""
SELF-IMPROVEMENT SYSTEM - Autonomous Tool Installation
======================================================
Allows Apex to install packages, create new tools, and extend its own capabilities.

This is the key to true autonomy - Apex can recognize when something is missing
and acquire it autonomously.
"""

import os
import sys
import subprocess
import logging
import json
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List

log = logging.getLogger("self_improvement")

_CONFIG_PATH = Path(__file__).parent.parent / "core" / "config.yaml"


def _storage_base() -> Path:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return Path(cfg.get("storage", {}).get("base", "C:/ai_agent/apex/data"))


def _venv_path() -> Path:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return Path(cfg.get("venv", {}).get("path", "C:/ai_agent/.venv"))


class SelfImprovement:
    """Allows Apex to extend its own capabilities."""

    def __init__(self, venv_path: str = None):
        """
        Initialize self-improvement system.

        Args:
            venv_path: Path to the virtual environment
        """
        if venv_path is None:
            venv_path = str(_venv_path())
        self.venv_path = Path(venv_path)
        self.pip_path = self.venv_path / "Scripts" / "pip.exe"
        self.python_path = self.venv_path / "Scripts" / "python.exe"

        if not self.pip_path.exists():
            log.warning("pip not found at %s", self.pip_path)

        log.info("Self-improvement system initialized")

    def install_package(self, package_name: str, version: Optional[str] = None) -> str:
        """
        Install a Python package using pip.

        Args:
            package_name: Name of the package (e.g., "requests", "flask")
            version: Optional version (e.g., "2.28.0")

        Returns:
            Installation result message
        """
        try:
            if version:
                package_spec = "%s==%s" % (package_name, version)
            else:
                package_spec = package_name

            log.info("Installing package: %s", package_spec)

            result = subprocess.run(
                [str(self.pip_path), "install", package_spec],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                log.info("Successfully installed %s", package_spec)
                return "Installed %s\n%s" % (package_spec, result.stdout)
            else:
                log.error("Failed to install %s: %s", package_spec, result.stderr)
                return "Failed to install %s\nError: %s" % (package_spec, result.stderr)

        except subprocess.TimeoutExpired:
            return "Installation timeout for %s" % package_name
        except Exception as e:
            log.error("Error installing %s: %s", package_name, e)
            return "Error: %s" % e

    def uninstall_package(self, package_name: str) -> str:
        """
        Uninstall a Python package.

        Args:
            package_name: Name of the package to uninstall

        Returns:
            Uninstallation result message
        """
        try:
            log.info("Uninstalling package: %s", package_name)

            result = subprocess.run(
                [str(self.pip_path), "uninstall", "-y", package_name],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                log.info("Successfully uninstalled %s", package_name)
                return "Uninstalled %s" % package_name
            else:
                return "Failed to uninstall %s\nError: %s" % (package_name, result.stderr)

        except Exception as e:
            log.error("Error uninstalling %s: %s", package_name, e)
            return "Error: %s" % e

    def list_installed_packages(self) -> str:
        """
        List all installed packages.

        Returns:
            List of installed packages
        """
        try:
            result = subprocess.run(
                [str(self.pip_path), "list"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return result.stdout
            else:
                return "Failed to list packages\nError: %s" % result.stderr

        except Exception as e:
            log.error("Error listing packages: %s", e)
            return "Error: %s" % e

    def check_package_installed(self, package_name: str) -> str:
        """
        Check if a package is installed.

        Args:
            package_name: Name of the package to check

        Returns:
            "True" if installed, "False" if not, or error message
        """
        try:
            result = subprocess.run(
                [str(self.pip_path), "show", package_name],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return "True"
            else:
                return "False"

        except Exception as e:
            return "Error: %s" % e

    def install_from_requirements(self, requirements_path: str) -> str:
        """
        Install packages from a requirements.txt file.

        Args:
            requirements_path: Path to requirements.txt

        Returns:
            Installation result
        """
        try:
            req_file = Path(requirements_path)
            if not req_file.exists():
                return "Requirements file not found: %s" % requirements_path

            log.info("Installing from requirements: %s", requirements_path)

            result = subprocess.run(
                [str(self.pip_path), "install", "-r", str(req_file)],
                capture_output=True,
                text=True,
                timeout=600
            )

            if result.returncode == 0:
                log.info("Successfully installed requirements from %s", requirements_path)
                return "Installed all requirements\n%s" % result.stdout
            else:
                return "Failed to install requirements\nError: %s" % result.stderr

        except Exception as e:
            log.error("Error installing requirements: %s", e)
            return "Error: %s" % e

    def run_python_script(self, script_path: str, args: List[str] = None) -> str:
        """
        Run a Python script.

        Args:
            script_path: Path to the Python script
            args: Optional command-line arguments

        Returns:
            Script output
        """
        try:
            script = Path(script_path)
            if not script.exists():
                return "Script not found: %s" % script_path

            cmd = [str(self.python_path), str(script)]
            if args:
                cmd.extend(args)

            log.info("Running script: %s", script_path)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(script.parent)
            )

            output = "--- STDOUT ---\n%s\n" % result.stdout
            if result.stderr:
                output += "--- STDERR ---\n%s\n" % result.stderr
            output += "--- EXIT CODE: %d ---" % result.returncode

            return output

        except subprocess.TimeoutExpired:
            return "Script timeout: %s" % script_path
        except Exception as e:
            log.error("Error running script: %s", e)
            return "Error: %s" % e

    def install_flutter(self) -> str:
        """
        Provide instructions for installing Flutter.
        Flutter cannot be installed via pip, so this guides the user.

        Returns:
            Installation instructions
        """
        instructions = """
Flutter Installation Instructions:

1. Download Flutter SDK:
   - Visit: https://flutter.dev/docs/get-started/install/windows
   - Download the Flutter SDK zip file

2. Extract and Add to PATH:
   - Extract to C:\\flutter
   - Add C:\\flutter\\bin to your PATH environment variable

3. Verify Installation:
   - Open a new terminal
   - Run: flutter doctor
   - Follow any additional setup instructions

4. Install Android Studio (for Android development):
   - Download from: https://developer.android.com/studio
   - Install Android SDK and tools

5. Set up Android Emulator or connect a device

Once installed, Flutter commands can be used to build your app.
"""
        return instructions

    def create_tool_module(self, tool_name: str, tool_code: str) -> str:
        """
        Create a new tool module that can be imported by Apex.

        Args:
            tool_name: Name of the tool (e.g., "image_tools")
            tool_code: Python code for the tool

        Returns:
            Success message
        """
        try:
            base = _storage_base()
            tool_path = base.parent / f"{tool_name}.py"

            log.info("Creating new tool module: %s", tool_name)

            tool_path.write_text(tool_code, encoding='utf-8')

            return "Created tool module: %s\n\nTo use this tool, restart Apex or run: import %s" % (
                str(tool_path.absolute()), tool_name)

        except Exception as e:
            log.error("Error creating tool module: %s", e)
            return "Error: %s" % e

    def search_for_package(self, search_term: str) -> str:
        """
        Search PyPI for packages matching the search term.

        Args:
            search_term: Package name or description to search for

        Returns:
            Search guidance
        """
        instructions = """
To search for Python packages:

1. Visit PyPI: https://pypi.org/search/?q=%s

2. Or use pip-search (if installed):
   pip-search %s

3. Popular packages for common needs:
   - Web scraping: beautifulsoup4, selenium, scrapy
   - HTTP requests: requests, httpx, aiohttp
   - Data science: pandas, numpy, scipy, scikit-learn
   - Image processing: pillow, opencv-python, imageio
   - GUI: tkinter (built-in), PyQt5, kivy
   - Web frameworks: flask, django, fastapi
   - Database: sqlalchemy, pymongo, redis
   - Testing: pytest, unittest (built-in)
   - Automation: pyautogui, selenium, playwright

Once you know the package name, install it with install_package("package_name").
""" % (search_term, search_term)
        return instructions


# Singleton
_self_improvement_instance = None


def get_self_improvement() -> SelfImprovement:
    """Get or create the SelfImprovement singleton instance."""
    global _self_improvement_instance
    if _self_improvement_instance is None:
        _self_improvement_instance = SelfImprovement()
    return _self_improvement_instance


def register_tools(registry) -> None:
    """Register self-improvement tools with the tool registry."""
    si = get_self_improvement()

    registry.register(
        name="install_package",
        func=lambda package_name, version=None: si.install_package(package_name, version),
        description="Install a Python package via pip"
    )
    registry.register(
        name="uninstall_package",
        func=lambda package_name: si.uninstall_package(package_name),
        description="Uninstall a Python package"
    )
    registry.register(
        name="list_installed_packages",
        func=lambda: si.list_installed_packages(),
        description="List all installed Python packages"
    )
    registry.register(
        name="check_package_installed",
        func=lambda package_name: si.check_package_installed(package_name),
        description="Check if a Python package is installed"
    )
    registry.register(
        name="install_from_requirements",
        func=lambda requirements_path: si.install_from_requirements(requirements_path),
        description="Install packages from a requirements.txt file"
    )
    registry.register(
        name="run_python_script",
        func=lambda script_path, args=None: si.run_python_script(script_path, args),
        description="Run a Python script"
    )
    registry.register(
        name="create_tool_module",
        func=lambda tool_name, tool_code: si.create_tool_module(tool_name, tool_code),
        description="Create a new tool module for Apex"
    )
    registry.register(
        name="search_for_package",
        func=lambda search_term: si.search_for_package(search_term),
        description="Search PyPI for packages matching a term"
    )
