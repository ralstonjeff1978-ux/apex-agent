"""
Apex Agent — Package Setup
==========================
Install from the apex/ directory:

    pip install .          # standard install
    pip install -e .       # editable install (recommended for development)
    pip install .[full]    # with all optional dependencies

After installation, import from anywhere:

    from apex.core.apex import create_apex
    apex = create_apex()
    result = apex.execute_task("List all Python files in C:/projects")
"""

from pathlib import Path
from setuptools import setup, find_packages

# Read the README for the long description
_readme = Path(__file__).parent / "docs" / "README.md"
long_description = _readme.read_text(encoding="utf-8") if _readme.exists() else ""

# Core requirements — always installed
_core_requires = [
    "requests>=2.31.0",
    "pyyaml>=6.0",
]

# Full requirements — all optional subsystems
_full_requires = [
    # Web / async
    "flask>=3.0.0",
    "websockets>=12.0",
    # System monitoring
    "psutil>=5.9.0",
    "gputil>=1.4.0",
    # Terminal
    "colorama>=0.4.6",
    # Security / crypto
    "cryptography>=42.0.0",
    # Computer vision and screen control
    "pyautogui>=0.9.54",
    "pillow>=10.0.0",
    "opencv-python>=4.8.0",
    "numpy>=1.24.0",
    "easyocr>=1.7.0",
    # Speech
    "speechrecognition>=3.10.0",
    "pyttsx3>=2.90",
    # Cloud sync
    "boto3>=1.34.0",
    "dropbox>=12.0.0",
    # Container management
    "docker>=7.0.0",
    # Extras
    "pyperclip>=1.9.0",
]

setup(
    name="apex-agent",
    version="0.1.0",
    description="Self-hosted autonomous AI agent platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires=">=3.10",

    # Map the apex package root to the current directory so that
    # `from apex.core.apex import create_apex` works after install.
    package_dir={
        "apex":                  ".",
        "apex.core":             "core",
        "apex.memory":           "memory",
        "apex.security":         "security",
        "apex.tools":            "tools",
        "apex.hardware":         "hardware",
        "apex.infrastructure":   "infrastructure",
        "apex.interfaces":       "interfaces",
    },
    packages=[
        "apex",
        "apex.core",
        "apex.memory",
        "apex.security",
        "apex.tools",
        "apex.hardware",
        "apex.infrastructure",
        "apex.interfaces",
    ],

    install_requires=_core_requires,

    extras_require={
        # Install everything:  pip install .[full]
        "full": _full_requires,
        # Individual subsystem groups for selective installs
        "web":        ["flask>=3.0.0", "websockets>=12.0"],
        "monitoring": ["psutil>=5.9.0", "gputil>=1.4.0"],
        "vision":     ["pyautogui>=0.9.54", "pillow>=10.0.0",
                       "opencv-python>=4.8.0", "numpy>=1.24.0", "easyocr>=1.7.0"],
        "speech":     ["speechrecognition>=3.10.0", "pyttsx3>=2.90"],
        "cloud":      ["boto3>=1.34.0", "dropbox>=12.0.0"],
        "security":   ["cryptography>=42.0.0"],
        "containers": ["docker>=7.0.0"],
    },

    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],

    package_data={
        # Include config.yaml so it ships with the package
        "apex.core": ["config.yaml"],
    },
)
