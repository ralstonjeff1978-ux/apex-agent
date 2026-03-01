"""
APP DEVELOPMENT ASSISTANT - Mobile App Creation Toolkit
=======================================================
Help create Android/iOS apps with Flutter and native tools.

Features:
- Flutter project generation
- Code scaffolding and templates
- Build automation
- Publishing assistance
- Integration with development environments
"""

import os
import subprocess
import json
import time
import yaml
from typing import Dict, List, Optional
import logging
from pathlib import Path
from dataclasses import dataclass, asdict

log = logging.getLogger("app_dev")

_CONFIG_PATH = Path(__file__).parent.parent / "core" / "config.yaml"


def _storage_base() -> Path:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return Path(cfg.get("storage", {}).get("base", "C:/ai_agent/apex/data"))


@dataclass
class AppProject:
    """Represents a mobile app project"""
    name: str
    type: str
    description: str
    features: List[str]
    platform: str
    created_at: float
    project_path: str
    dependencies: List[str]
    main_components: List[str]


class AppDevelopmentAssistant:
    def __init__(self, workspace_dir: Path = None):
        if workspace_dir is None:
            workspace_dir = _storage_base() / "app_projects"
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.projects: Dict[str, AppProject] = {}
        self.flutter_available = self.check_flutter()
        self.android_studio_available = self.check_android_studio()

    def check_flutter(self) -> bool:
        """Check if Flutter is available"""
        try:
            result = subprocess.run(['flutter', '--version'],
                                    capture_output=True, timeout=10)
            if result.returncode == 0:
                log.info("Flutter available")
                return True
        except (subprocess.SubprocessError, FileNotFoundError):
            log.warning("Flutter not found")
        return False

    def check_android_studio(self) -> bool:
        """Check if Android Studio is available"""
        import platform
        system = platform.system()

        if system == "Windows":
            paths = [
                "C:/Program Files/Android/Android Studio/bin/studio64.exe",
                os.path.expanduser("~/AppData/Local/Android/Android Studio/bin/studio64.exe")
            ]
        elif system == "Darwin":
            paths = ["/Applications/Android Studio.app"]
        else:
            paths = ["/opt/android-studio/bin/studio.sh"]

        for path in paths:
            if os.path.exists(path):
                log.info("Android Studio available")
                return True

        log.warning("Android Studio not found")
        return False

    def create_flutter_app(self, app_name: str, description: str = "",
                           features: List[str] = None, platform: str = "both") -> Optional[AppProject]:
        """Create a new Flutter application"""
        if not self.flutter_available:
            log.error("Flutter not available - cannot create Flutter app")
            return None

        try:
            log.info("Creating Flutter app: %s", app_name)

            project_path = self.workspace_dir / app_name.lower().replace(" ", "_")
            project_path.mkdir(exist_ok=True)

            result = subprocess.run([
                'flutter', 'create', str(project_path)
            ], capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                log.error("Flutter create failed: %s", result.stderr)
                return None

            if features:
                self._customize_flutter_app(project_path, features)

            project = AppProject(
                name=app_name,
                type="flutter",
                description=description or f"Flutter app: {app_name}",
                features=features or [],
                platform=platform,
                created_at=time.time(),
                project_path=str(project_path),
                dependencies=["flutter", "cupertino_icons"],
                main_components=["main.dart", "app.dart"]
            )

            self.projects[app_name] = project
            self._save_project_config(project)

            log.info("Flutter app created at %s", project_path)
            return project

        except subprocess.TimeoutExpired:
            log.error("Flutter create timed out")
        except Exception as e:
            log.error("Flutter app creation failed: %s", e)

        return None

    def _customize_flutter_app(self, project_path: Path, features: List[str]):
        """Customize Flutter app with requested features"""
        try:
            pubspec_path = project_path / "pubspec.yaml"
            if pubspec_path.exists():
                with open(pubspec_path, 'r') as f:
                    content = f.read()

                feature_deps = {
                    "camera": "camera: ^0.10.0",
                    "location": "geolocator: ^9.0.0",
                    "storage": "shared_preferences: ^2.0.0",
                    "network": "http: ^0.15.0",
                    "authentication": "firebase_auth: ^4.0.0",
                    "database": "cloud_firestore: ^4.0.0",
                    "ui": "flutter_svg: ^2.0.0"
                }

                deps_to_add = []
                for feature in features:
                    if feature in feature_deps:
                        deps_to_add.append(f"  {feature_deps[feature]}")

                if deps_to_add:
                    lines = content.split('\n')
                    new_lines = []
                    dependencies_added = False

                    for line in lines:
                        new_lines.append(line)
                        if line.strip() == "dependencies:" and not dependencies_added:
                            new_lines.extend(deps_to_add)
                            dependencies_added = True

                    with open(pubspec_path, 'w') as f:
                        f.write('\n'.join(new_lines))

            lib_dir = project_path / "lib"

            if "authentication" in features:
                auth_dir = lib_dir / "screens" / "auth"
                auth_dir.mkdir(parents=True, exist_ok=True)

                login_content = '''
import 'package:flutter/material.dart';

class LoginScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Login')),
      body: Padding(
        padding: EdgeInsets.all(16.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            TextField(
              decoration: InputDecoration(hintText: 'Email'),
            ),
            SizedBox(height: 16),
            TextField(
              decoration: InputDecoration(hintText: 'Password'),
              obscureText: true,
            ),
            SizedBox(height: 24),
            ElevatedButton(
              onPressed: () {
                // Handle login
              },
              child: Text('Login'),
            ),
          ],
        ),
      ),
    );
  }
}
'''
                with open(auth_dir / "login_screen.dart", 'w') as f:
                    f.write(login_content)

            if "camera" in features:
                camera_content = '''
import 'package:camera/camera.dart';
import 'package:flutter/material.dart';

class CameraScreen extends StatefulWidget {
  @override
  _CameraScreenState createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> {
  late List<CameraDescription> _cameras;
  late CameraController _controller;

  @override
  void initState() {
    super.initState();
    _initializeCamera();
  }

  Future<void> _initializeCamera() async {
    _cameras = await availableCameras();
    _controller = CameraController(_cameras[0], ResolutionPreset.medium);
    await _controller.initialize();
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    if (!_controller.value.isInitialized) {
      return Container();
    }

    return Scaffold(
      body: CameraPreview(_controller),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          // Capture photo
        },
        child: Icon(Icons.camera),
      ),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }
}
'''
                with open(lib_dir / "camera_screen.dart", 'w') as f:
                    f.write(camera_content)

        except Exception as e:
            log.error("App customization error: %s", e)

    def build_app(self, project_name: str, target_platform: str = "apk") -> bool:
        """Build the app for specified platform"""
        if project_name not in self.projects:
            log.error("Project %s not found", project_name)
            return False

        project = self.projects[project_name]
        project_path = Path(project.project_path)

        try:
            log.info("Building %s for %s", project_name, target_platform)

            if project.type == "flutter":
                original_dir = os.getcwd()
                os.chdir(project_path)

                if target_platform == "apk":
                    build_cmd = ['flutter', 'build', 'apk']
                elif target_platform == "appbundle":
                    build_cmd = ['flutter', 'build', 'appbundle']
                elif target_platform == "ios":
                    build_cmd = ['flutter', 'build', 'ios']
                else:
                    build_cmd = ['flutter', 'build', target_platform]

                result = subprocess.run(build_cmd,
                                        capture_output=True, text=True, timeout=600)

                os.chdir(original_dir)

                if result.returncode == 0:
                    log.info("Build successful for %s", project_name)
                    return True
                else:
                    log.error("Build failed: %s", result.stderr)
                    return False

            else:
                log.error("Build not supported for %s projects", project.type)
                return False

        except subprocess.TimeoutExpired:
            log.error("Build timed out")
            return False
        except Exception as e:
            log.error("Build error: %s", e)
            return False

    def add_feature(self, project_name: str, feature: str) -> bool:
        """Add a feature to existing app"""
        if project_name not in self.projects:
            log.error("Project %s not found", project_name)
            return False

        project = self.projects[project_name]
        if feature not in project.features:
            project.features.append(feature)

        project_path = Path(project.project_path)
        self._customize_flutter_app(project_path, [feature])

        self._save_project_config(project)
        log.info("Added %s to %s", feature, project_name)
        return True

    def get_project_info(self, project_name: str) -> Optional[Dict]:
        """Get detailed information about a project"""
        if project_name not in self.projects:
            return None

        project = self.projects[project_name]
        return asdict(project)

    def list_projects(self) -> List[str]:
        """List all projects"""
        return list(self.projects.keys())

    def _save_project_config(self, project: AppProject):
        """Save project configuration to file"""
        try:
            config_path = Path(project.project_path) / ".apex_config.json"
            with open(config_path, 'w') as f:
                json.dump(asdict(project), f, indent=2)
        except Exception as e:
            log.error("Failed to save project config: %s", e)

    def load_projects(self):
        """Load existing projects from workspace"""
        try:
            for project_dir in self.workspace_dir.iterdir():
                if project_dir.is_dir():
                    config_file = project_dir / ".apex_config.json"
                    if config_file.exists():
                        with open(config_file, 'r') as f:
                            config = json.load(f)
                        project = AppProject(**config)
                        self.projects[project.name] = project
                        log.info("Loaded project: %s", project.name)
        except Exception as e:
            log.error("Failed to load projects: %s", e)


_app_development_assistant = None


def get_app_development_assistant() -> AppDevelopmentAssistant:
    """Get or create the singleton AppDevelopmentAssistant instance"""
    global _app_development_assistant
    if _app_development_assistant is None:
        _app_development_assistant = AppDevelopmentAssistant()
        _app_development_assistant.load_projects()
    return _app_development_assistant


def register_tools(registry) -> None:
    """Register app development tools with the agent registry"""
    assistant = get_app_development_assistant()

    registry.register("tools_create_flutter_app", assistant.create_flutter_app)
    registry.register("tools_build_app", assistant.build_app)
    registry.register("tools_add_feature", assistant.add_feature)
    registry.register("tools_get_project_info", assistant.get_project_info)
    registry.register("tools_list_projects", assistant.list_projects)
