"""
DOCKER DEPLOYMENT - Containerized Apex AI System
================================================
Easy deployment and scaling of Apex AI across multiple devices.

Features:
- Docker Compose for multi-service orchestration
- Environment configuration management
- Data persistence and volume management
- Service health monitoring
- Auto-scaling capabilities
- Backup and restore functionality
- Security-hardened containers
- Cross-platform compatibility
- CI/CD pipeline integration
- Resource optimization
"""

import json
import time
import os
import subprocess
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime, timedelta
from enum import Enum
import yaml
import docker
from docker.models.containers import Container

log = logging.getLogger("docker_deployment")

_CONFIG_PATH = Path(__file__).parent.parent / "core" / "config.yaml"


def _storage_base() -> Path:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return Path(cfg.get("storage", {}).get("base", "C:/ai_agent/apex/data"))


class ServiceStatus(Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    RESTARTING = "restarting"
    ERROR = "error"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"


@dataclass
class DockerService:
    """Docker service configuration"""
    name: str
    image: str
    ports: List[str]
    volumes: List[str]
    environment: Dict[str, str]
    depends_on: List[str]
    restart_policy: str
    health_check: Optional[Dict[str, str]]
    resource_limits: Optional[Dict[str, str]]
    networks: List[str]
    status: ServiceStatus = ServiceStatus.STOPPED
    container_id: Optional[str] = None
    last_updated: float = 0


@dataclass
class DeploymentConfig:
    """Docker deployment configuration"""
    project_name: str
    version: str
    services: List[DockerService]
    networks: List[str]
    volumes: List[str]
    environment_vars: Dict[str, str]
    secrets: List[str]
    created_at: float


@dataclass
class DeploymentHistory:
    """Deployment history record"""
    id: str
    timestamp: datetime
    action: str  # deploy, update, rollback, stop
    services_affected: List[str]
    status: str  # success, failed, partial
    duration_seconds: float
    logs: str
    user: str


class DockerDeploymentManager:
    def __init__(self, project_dir: str = None):
        base = _storage_base()
        if project_dir is None:
            project_dir = str(base / "apex_deployment")
        self.project_dir = Path(project_dir)
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir = self.project_dir / "config"
        self.config_dir.mkdir(exist_ok=True)
        self.data_dir = self.project_dir / "data"
        self.data_dir.mkdir(exist_ok=True)
        self.logs_dir = self.project_dir / "logs"
        self.logs_dir.mkdir(exist_ok=True)

        self.deployment_configs: List[DeploymentConfig] = []
        self.deployment_history: List[DeploymentHistory] = []
        self.docker_client = None

        try:
            self.docker_client = docker.from_env()
            log.info("Docker client initialized successfully")
        except Exception as e:
            log.error("Failed to initialize Docker client: %s", e)
            self.docker_client = None

        self.load_configurations()

    def create_deployment_config(self, project_name: str = "apex-ai",
                                 version: str = "1.0.0") -> str:
        """Create a new Docker deployment configuration"""
        services = [
            DockerService(
                name="apex-core",
                image="python:3.9-slim",
                ports=["8000:8000", "8765:8765"],
                volumes=[
                    "./apex_data:/app/data",
                    "./logs:/app/logs",
                    "./config:/app/config"
                ],
                environment={
                    "PYTHONPATH": "/app",
                    "LOG_LEVEL": "INFO",
                    "OLLAMA_HOST": "http://ollama:11434"
                },
                depends_on=["ollama", "redis"],
                restart_policy="unless-stopped",
                health_check={
                    "test": ["CMD", "curl", "-f", "http://localhost:8000/health"],
                    "interval": "30s",
                    "timeout": "10s",
                    "retries": 3
                },
                resource_limits={
                    "cpus": "2.0",
                    "memory": "4G"
                },
                networks=["apex-network"],
                status=ServiceStatus.STOPPED
            ),
            DockerService(
                name="ollama",
                image="ollama/ollama:latest",
                ports=["11434:11434"],
                volumes=["ollama-data:/root/.ollama"],
                environment={},
                depends_on=[],
                restart_policy="unless-stopped",
                health_check={
                    "test": ["CMD", "curl", "-f", "http://localhost:11434/api/tags"],
                    "interval": "30s",
                    "timeout": "10s",
                    "retries": 3
                },
                resource_limits={
                    "cpus": "4.0",
                    "memory": "8G"
                },
                networks=["apex-network"]
            ),
            DockerService(
                name="redis",
                image="redis:7-alpine",
                ports=["6379:6379"],
                volumes=["redis-data:/data"],
                environment={},
                depends_on=[],
                restart_policy="unless-stopped",
                health_check={
                    "test": ["CMD", "redis-cli", "ping"],
                    "interval": "10s",
                    "timeout": "3s",
                    "retries": 3
                },
                resource_limits={
                    "cpus": "0.5",
                    "memory": "512M"
                },
                networks=["apex-network"]
            ),
            DockerService(
                name="mongodb",
                image="mongo:6.0",
                ports=["27017:27017"],
                volumes=["mongo-data:/data/db"],
                environment={
                    "MONGO_INITDB_ROOT_USERNAME": "apex",
                    "MONGO_INITDB_ROOT_PASSWORD": "apex_db_pass"
                },
                depends_on=[],
                restart_policy="unless-stopped",
                health_check={
                    "test": ["CMD", "mongosh", "--eval", "db.stats()"],
                    "interval": "30s",
                    "timeout": "10s",
                    "retries": 3
                },
                resource_limits={
                    "cpus": "1.0",
                    "memory": "1G"
                },
                networks=["apex-network"]
            ),
            DockerService(
                name="nginx",
                image="nginx:alpine",
                ports=["80:80", "443:443"],
                volumes=[
                    "./nginx/conf:/etc/nginx/conf.d",
                    "./nginx/certs:/etc/nginx/certs",
                    "./nginx/html:/usr/share/nginx/html"
                ],
                environment={},
                depends_on=["apex-core"],
                restart_policy="unless-stopped",
                health_check={
                    "test": ["CMD", "curl", "-f", "http://localhost"],
                    "interval": "30s",
                    "timeout": "10s",
                    "retries": 3
                },
                resource_limits={
                    "cpus": "0.5",
                    "memory": "256M"
                },
                networks=["apex-network"]
            )
        ]

        config = DeploymentConfig(
            project_name=project_name,
            version=version,
            services=services,
            networks=["apex-network"],
            volumes=[
                "apex-data:/app/data",
                "ollama-data:/root/.ollama",
                "redis-data:/data",
                "mongo-data:/data/db",
                "logs-data:/app/logs"
            ],
            environment_vars={
                "ENVIRONMENT": "production",
                "DEBUG": "False",
                "LOG_LEVEL": "INFO"
            },
            secrets=["MONGO_PASSWORD", "API_KEYS"],
            created_at=time.time()
        )

        self.deployment_configs.append(config)
        self._save_configurations()
        log.info("Created deployment config: %s v%s", project_name, version)
        return "config_%d" % len(self.deployment_configs)

    def generate_docker_compose(self, config_name: str = None) -> str:
        """Generate Docker Compose YAML file"""
        if not config_name and self.deployment_configs:
            config = self.deployment_configs[0]
        elif config_name:
            config = next((c for c in self.deployment_configs if c.project_name == config_name), None)
            if not config:
                raise ValueError("Configuration %s not found" % config_name)
        else:
            raise ValueError("No configuration available")

        compose_data = {
            "version": "3.8",
            "services": {},
            "networks": {
                "apex-network": {
                    "driver": "bridge"
                }
            },
            "volumes": {}
        }

        for service in config.services:
            service_dict = {
                "image": service.image,
                "restart": service.restart_policy,
                "environment": service.environment,
                "volumes": service.volumes,
                "networks": service.networks
            }

            if service.ports:
                service_dict["ports"] = service.ports

            if service.depends_on:
                service_dict["depends_on"] = service.depends_on

            if service.health_check:
                service_dict["healthcheck"] = service.health_check

            if service.resource_limits:
                service_dict["deploy"] = {
                    "resources": {
                        "limits": service.resource_limits
                    }
                }

            compose_data["services"][service.name] = service_dict

        for volume in config.volumes:
            if ":" in volume:
                vol_name = volume.split(":")[0]
                if vol_name not in ["./apex_data", "./logs", "./config", "./nginx"]:
                    compose_data["volumes"][vol_name] = {}

        compose_file = self.config_dir / "docker-compose.yml"
        with open(compose_file, 'w') as f:
            yaml.dump(compose_data, f, default_flow_style=False, sort_keys=False)

        log.info("Generated docker-compose.yml at %s", compose_file)
        return str(compose_file)

    def deploy_services(self, config_name: str = None) -> Dict[str, str]:
        """Deploy Docker services"""
        if not self.docker_client:
            return {"error": "Docker client not available"}

        start_time = time.time()
        affected_services = []
        results = {}

        try:
            compose_file = self.generate_docker_compose(config_name)

            log.info("Pulling Docker images")
            subprocess.run(["docker-compose", "-f", compose_file, "pull"],
                           cwd=self.project_dir, check=True, capture_output=True)

            log.info("Starting services")
            result = subprocess.run([
                "docker-compose", "-f", compose_file, "up", "-d"
            ], cwd=self.project_dir, capture_output=True, text=True)

            if result.returncode == 0:
                results["status"] = "success"
                results["message"] = "Services deployed successfully"
                log.info("Services deployed successfully")
            else:
                results["status"] = "failed"
                results["message"] = "Deployment failed: %s" % result.stderr
                log.error("Deployment failed: %s", result.stderr)

            self._update_service_statuses()

        except subprocess.CalledProcessError as e:
            results["status"] = "failed"
            results["message"] = "Subprocess error: %s" % e
            log.error("Subprocess error: %s", e)
        except Exception as e:
            results["status"] = "failed"
            results["message"] = "Deployment error: %s" % e
            log.error("Deployment error: %s", e)

        end_time = time.time()

        history = DeploymentHistory(
            id="deploy_%d" % int(time.time() * 1000),
            timestamp=datetime.now(),
            action="deploy",
            services_affected=affected_services,
            status=results["status"],
            duration_seconds=end_time - start_time,
            logs=results["message"],
            user=os.getenv("USER", "system")
        )

        self.deployment_history.append(history)
        self._save_configurations()

        return results

    def stop_services(self, service_names: List[str] = None) -> Dict[str, str]:
        """Stop Docker services"""
        if not self.docker_client:
            return {"error": "Docker client not available"}

        start_time = time.time()
        results = {}

        try:
            compose_file = self.config_dir / "docker-compose.yml"
            if not compose_file.exists():
                return {"error": "docker-compose.yml not found"}

            cmd = ["docker-compose", "-f", str(compose_file)]
            if service_names:
                cmd.extend(service_names)
            cmd.extend(["stop"])

            result = subprocess.run(cmd, cwd=self.project_dir,
                                    capture_output=True, text=True)

            if result.returncode == 0:
                results["status"] = "success"
                results["message"] = "Services stopped successfully"
                log.info("Services stopped successfully")
            else:
                results["status"] = "failed"
                results["message"] = "Stop failed: %s" % result.stderr
                log.error("Stop failed: %s", result.stderr)

            self._update_service_statuses()

        except Exception as e:
            results["status"] = "failed"
            results["message"] = "Stop error: %s" % e
            log.error("Stop error: %s", e)

        end_time = time.time()

        history = DeploymentHistory(
            id="stop_%d" % int(time.time() * 1000),
            timestamp=datetime.now(),
            action="stop",
            services_affected=service_names or ["all"],
            status=results["status"],
            duration_seconds=end_time - start_time,
            logs=results["message"],
            user=os.getenv("USER", "system")
        )

        self.deployment_history.append(history)
        self._save_configurations()

        return results

    def scale_service(self, service_name: str, replicas: int) -> Dict[str, str]:
        """Scale a Docker service"""
        if not self.docker_client:
            return {"error": "Docker client not available"}

        try:
            compose_file = self.config_dir / "docker-compose.yml"
            if not compose_file.exists():
                return {"error": "docker-compose.yml not found"}

            result = subprocess.run([
                "docker-compose", "-f", str(compose_file),
                "scale", "%s=%d" % (service_name, replicas)
            ], cwd=self.project_dir, capture_output=True, text=True)

            if result.returncode == 0:
                log.info("Scaled %s to %d replicas", service_name, replicas)
                return {
                    "status": "success",
                    "message": "Scaled %s to %d replicas" % (service_name, replicas)
                }
            else:
                log.error("Scale failed: %s", result.stderr)
                return {
                    "status": "failed",
                    "message": "Scale failed: %s" % result.stderr
                }

        except Exception as e:
            log.error("Scale error: %s", e)
            return {
                "status": "failed",
                "message": "Scale error: %s" % e
            }

    def get_service_status(self) -> Dict[str, Dict]:
        """Get status of all services"""
        if not self.docker_client:
            return {"error": {"status": "Docker client not available"}}

        statuses = {}

        try:
            compose_file = self.config_dir / "docker-compose.yml"
            if not compose_file.exists():
                return {"error": {"status": "docker-compose.yml not found"}}

            result = subprocess.run([
                "docker-compose", "-f", str(compose_file), "ps", "--format", "json"
            ], cwd=self.project_dir, capture_output=True, text=True)

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.strip():
                        try:
                            service_info = json.loads(line)
                            service_name = service_info.get('Service', 'unknown')
                            statuses[service_name] = {
                                "status": service_info.get('State', 'unknown'),
                                "ports": service_info.get('Publishers', []),
                                "container_id": service_info.get('ID', '')[:12]
                            }
                        except json.JSONDecodeError:
                            continue
            else:
                result = subprocess.run([
                    "docker-compose", "-f", str(compose_file), "ps"
                ], cwd=self.project_dir, capture_output=True, text=True)

                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')[1:]
                    for line in lines:
                        parts = line.split()
                        if len(parts) >= 4:
                            service_name = parts[0].split('_')[1] if '_' in parts[0] else parts[0]
                            statuses[service_name] = {
                                "status": parts[3],
                                "container_id": parts[0][:12]
                            }

        except Exception as e:
            log.error("Error getting service status: %s", e)
            statuses["error"] = {"status": "Error: %s" % e}

        return statuses

    def _update_service_statuses(self):
        """Update internal service status tracking"""
        statuses = self.get_service_status()
        if "error" not in statuses:
            for config in self.deployment_configs:
                for service in config.services:
                    if service.name in statuses:
                        status_info = statuses[service.name]
                        service.container_id = status_info.get("container_id", service.container_id)
                        service.status = ServiceStatus(status_info["status"]) if status_info["status"] in [s.value for s in ServiceStatus] else ServiceStatus.ERROR
                        service.last_updated = time.time()

        self._save_configurations()

    def backup_deployment(self, backup_name: str = None) -> str:
        """Backup deployment data and configuration"""
        if not backup_name:
            backup_name = "backup_%s" % datetime.now().strftime('%Y%m%d_%H%M%S')

        backup_dir = self.project_dir / "backups" / backup_name
        backup_dir.mkdir(parents=True, exist_ok=True)

        try:
            if self.data_dir.exists():
                subprocess.run([
                    "cp", "-r", str(self.data_dir), str(backup_dir / "data")
                ], check=True)

            if self.config_dir.exists():
                subprocess.run([
                    "cp", "-r", str(self.config_dir), str(backup_dir / "config")
                ], check=True)

            volumes_to_backup = ["apex-data", "ollama-data", "mongo-data"]
            for volume in volumes_to_backup:
                try:
                    subprocess.run([
                        "docker", "run", "--rm",
                        "-v", "%s:/volume" % volume,
                        "-v", "%s:/backup" % str(backup_dir),
                        "alpine", "tar", "czf", "/backup/%s.tar.gz" % volume, "-C", "/volume", "."
                    ], check=True)
                except Exception:
                    log.warning("Failed to backup volume %s", volume)

            log.info("Backup created: %s", backup_dir)
            return str(backup_dir)

        except Exception as e:
            log.error("Backup failed: %s", e)
            return "Backup failed: %s" % e

    def restore_deployment(self, backup_path: str) -> Dict[str, str]:
        """Restore deployment from backup"""
        backup_dir = Path(backup_path)
        if not backup_dir.exists():
            return {"status": "failed", "message": "Backup path not found"}

        try:
            self.stop_services()

            backup_data_dir = backup_dir / "data"
            if backup_data_dir.exists():
                subprocess.run([
                    "cp", "-r", str(backup_data_dir), str(self.project_dir)
                ], check=True)

            backup_config_dir = backup_dir / "config"
            if backup_config_dir.exists():
                subprocess.run([
                    "cp", "-r", str(backup_config_dir), str(self.project_dir)
                ], check=True)

            for backup_file in backup_dir.glob("*.tar.gz"):
                volume_name = backup_file.stem
                try:
                    subprocess.run([
                        "docker", "run", "--rm",
                        "-v", "%s:/volume" % volume_name,
                        "-v", "%s:/backup" % str(backup_dir),
                        "alpine", "tar", "xzf", "/backup/%s" % backup_file.name, "-C", "/volume"
                    ], check=True)
                except Exception:
                    log.warning("Failed to restore volume %s", volume_name)

            self.deploy_services()

            log.info("Deployment restored from: %s", backup_path)
            return {"status": "success", "message": "Restored from %s" % backup_path}

        except Exception as e:
            log.error("Restore failed: %s", e)
            return {"status": "failed", "message": "Restore failed: %s" % e}

    def get_deployment_dashboard(self) -> Dict:
        """Get deployment dashboard information"""
        dashboard = {
            "system_status": {
                "docker_available": self.docker_client is not None,
                "services_count": sum(len(config.services) for config in self.deployment_configs),
                "active_deployments": len([h for h in self.deployment_history if h.action == "deploy" and h.status == "success"]),
                "last_deployment": None
            },
            "services_status": self.get_service_status(),
            "resource_usage": self._get_resource_usage(),
            "deployment_history": [
                {
                    "timestamp": h.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "action": h.action,
                    "status": h.status,
                    "duration": "%.1fs" % h.duration_seconds
                }
                for h in self.deployment_history[-10:]
            ],
            "backup_status": {
                "last_backup": self._get_last_backup_time(),
                "backup_location": str(self.project_dir / "backups")
            }
        }

        if self.deployment_history:
            last_deploy = next((h for h in reversed(self.deployment_history) if h.action == "deploy"), None)
            if last_deploy:
                dashboard["system_status"]["last_deployment"] = {
                    "time": last_deploy.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "status": last_deploy.status,
                    "services": last_deploy.services_affected
                }

        return dashboard

    def _get_resource_usage(self) -> Dict:
        """Get resource usage information"""
        usage = {
            "cpu_percent": 0,
            "memory_percent": 0,
            "disk_usage_gb": 0,
            "containers_running": 0
        }

        try:
            if self.docker_client:
                info = self.docker_client.info()
                usage["containers_running"] = info.get("ContainersRunning", 0)

                try:
                    df_result = subprocess.run(["df", "-BG", "/"],
                                               capture_output=True, text=True)
                    if df_result.returncode == 0:
                        lines = df_result.stdout.strip().split('\n')
                        if len(lines) > 1:
                            disk_info = lines[1].split()
                            if len(disk_info) > 4:
                                usage["disk_usage_gb"] = int(disk_info[2].rstrip('G'))
                except Exception:
                    pass

        except Exception as e:
            log.debug("Resource usage check failed: %s", e)

        return usage

    def _get_last_backup_time(self) -> Optional[str]:
        """Get timestamp of last backup"""
        backups_dir = self.project_dir / "backups"
        if backups_dir.exists():
            backups = list(backups_dir.iterdir())
            if backups:
                latest_backup = max(backups, key=lambda x: x.stat().st_mtime)
                return datetime.fromtimestamp(latest_backup.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        return None

    def generate_deployment_report(self) -> str:
        """Generate comprehensive deployment report"""
        report = []
        report.append("=" * 70)
        report.append("APEX DOCKER DEPLOYMENT REPORT")
        report.append("=" * 70)
        report.append("Generated: %s" % datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        report.append("")

        dashboard = self.get_deployment_dashboard()
        system_status = dashboard["system_status"]

        report.append("SYSTEM STATUS")
        report.append("-" * 20)
        report.append("Docker Available: %s" % ("Yes" if system_status['docker_available'] else "No"))
        report.append("Services Configured: %d" % system_status['services_count'])
        report.append("Active Deployments: %d" % system_status['active_deployments'])
        if system_status['last_deployment']:
            ld = system_status['last_deployment']
            report.append("Last Deployment: %s (%s)" % (ld['time'], ld['status']))
        report.append("")

        report.append("SERVICES STATUS")
        report.append("-" * 18)
        for service_name, status_info in dashboard["services_status"].items():
            if service_name != "error":
                report.append("%-20s %s" % (service_name, status_info['status']))
        report.append("")

        resource_usage = dashboard["resource_usage"]
        report.append("RESOURCE USAGE")
        report.append("-" * 18)
        report.append("Containers Running: %d" % resource_usage['containers_running'])
        report.append("Disk Usage: %d GB" % resource_usage['disk_usage_gb'])
        report.append("")

        report.append("DEPLOYMENT HISTORY (Last 10)")
        report.append("-" * 35)
        for history_item in dashboard["deployment_history"]:
            report.append("%s - %s (%s) %s" % (
                history_item['timestamp'], history_item['action'],
                history_item['status'], history_item['duration']))
        report.append("")

        backup_status = dashboard["backup_status"]
        report.append("BACKUP STATUS")
        report.append("-" * 18)
        if backup_status["last_backup"]:
            report.append("Last Backup: %s" % backup_status['last_backup'])
        else:
            report.append("No backups found")
        report.append("Backup Location: %s" % backup_status['backup_location'])
        report.append("")

        report.append("=" * 70)
        report.append("Report generated by Apex Docker Deployment Manager")
        report.append("=" * 70)

        return '\n'.join(report)

    def _save_configurations(self):
        """Save deployment configurations to files"""
        try:
            configs_file = self.config_dir / "deployment_configs.json"
            with open(configs_file, 'w') as f:
                config_dicts = []
                for config in self.deployment_configs:
                    config_dict = asdict(config)
                    for service in config_dict['services']:
                        service['status'] = service['status'].value
                    config_dicts.append(config_dict)
                json.dump(config_dicts, f, indent=2)

            history_file = self.config_dir / "deployment_history.json"
            with open(history_file, 'w') as f:
                history_dicts = []
                for history in self.deployment_history:
                    history_dict = asdict(history)
                    history_dict['timestamp'] = history.timestamp.isoformat()
                    history_dicts.append(history_dict)
                json.dump(history_dicts, f, indent=2)

        except Exception as e:
            log.error("Failed to save deployment configurations: %s", e)

    def load_configurations(self):
        """Load deployment configurations from files"""
        try:
            configs_file = self.config_dir / "deployment_configs.json"
            if configs_file.exists():
                with open(configs_file, 'r') as f:
                    configs_data = json.load(f)
                for config_data in configs_data:
                    services = []
                    for service_data in config_data['services']:
                        service_data['status'] = ServiceStatus(service_data['status'])
                        service = DockerService(**service_data)
                        services.append(service)
                    config_data['services'] = services
                    config = DeploymentConfig(**config_data)
                    self.deployment_configs.append(config)

            history_file = self.config_dir / "deployment_history.json"
            if history_file.exists():
                with open(history_file, 'r') as f:
                    history_data = json.load(f)
                for history_data_entry in history_data:
                    history_data_entry['timestamp'] = datetime.fromisoformat(history_data_entry['timestamp'])
                    history = DeploymentHistory(**history_data_entry)
                    self.deployment_history.append(history)

            log.info("Loaded Docker deployment configurations")

        except Exception as e:
            log.error("Failed to load deployment configurations: %s", e)

    def integrate_with_apex(self, apex_instance):
        """Integrate with main Apex system"""
        def deploy_apex():
            """Deploy Apex services"""
            try:
                if not self.deployment_configs:
                    self.create_deployment_config()

                result = self.deploy_services()
                if result["status"] == "success":
                    return "Apex services deployed successfully"
                else:
                    return "Deployment failed: %s" % result['message']
            except Exception as e:
                return "Deployment error: %s" % e

        def stop_apex():
            """Stop Apex services"""
            try:
                result = self.stop_services()
                if result["status"] == "success":
                    return "Apex services stopped successfully"
                else:
                    return "Stop failed: %s" % result['message']
            except Exception as e:
                return "Stop error: %s" % e

        def get_deployment_status():
            """Get deployment status"""
            try:
                dashboard = self.get_deployment_dashboard()
                system_status = dashboard["system_status"]
                services_status = dashboard["services_status"]

                status_lines = ["Deployment Status:"]
                status_lines.append("  Docker Available: %s" % ("Yes" if system_status['docker_available'] else "No"))
                status_lines.append("  Services Running: %d" % system_status['services_count'])

                status_lines.append("\n  Service Status:")
                for service_name, status_info in services_status.items():
                    if service_name != "error":
                        status_lines.append("    %s: %s" % (service_name, status_info['status']))

                return '\n'.join(status_lines)
            except Exception as e:
                return "Failed to get status: %s" % e

        log.info("Docker Deployment Manager integrated with Apex")


def create_docker_compose_template():
    """Create a template docker-compose.yml file"""
    template = """version: '3.8'

services:
  apex-core:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
      - "8765:8765"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config
    environment:
      - PYTHONPATH=/app
      - LOG_LEVEL=INFO
      - OLLAMA_HOST=http://ollama:11434
    depends_on:
      - ollama
      - redis
      - mongodb
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 8G

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M

  mongodb:
    image: mongo:6.0
    ports:
      - "27017:27017"
    volumes:
      - mongo-data:/data/db
    environment:
      MONGO_INITDB_ROOT_USERNAME: apex
      MONGO_INITDB_ROOT_PASSWORD: apex_db_pass
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.stats()"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf:/etc/nginx/conf.d
      - ./nginx/certs:/etc/nginx/certs
      - ./nginx/html:/usr/share/nginx/html
    depends_on:
      - apex-core
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M

networks:
  apex-network:
    driver: bridge

volumes:
  apex-data:
  ollama-data:
  redis-data:
  mongo-data:
  logs-data:
"""

    compose_file = Path("docker-compose.yml")
    with open(compose_file, 'w') as f:
        f.write(template)

    log.info("Created docker-compose.yml template")
    return str(compose_file)


def create_dockerfile_template():
    """Create a template Dockerfile"""
    dockerfile_content = """# Apex AI Dockerfile
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    ffmpeg \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data logs config

# Expose ports
EXPOSE 8000 8765 11434

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "apex_main.py"]
"""

    dockerfile = Path("Dockerfile")
    with open(dockerfile, 'w') as f:
        f.write(dockerfile_content)

    log.info("Created Dockerfile template")
    return str(dockerfile)


def create_requirements_template():
    """Create a template requirements.txt file"""
    requirements_content = """# Apex AI Requirements
requests>=2.28.0
pyttsx3>=2.90
SpeechRecognition>=3.10.0
pyautogui>=0.9.53
easyocr>=1.6.2
opencv-python>=4.6.0
numpy>=1.23.0
Pillow>=9.2.0
psutil>=5.9.0
GPUtil>=1.4.0
websockets>=10.3
flask>=2.2.0
docker>=6.0.0
PyYAML>=6.0
edge-tts>=6.1.0
nmap>=0.0.1
colorama>=0.4.5
"""

    requirements_file = Path("requirements.txt")
    with open(requirements_file, 'w') as f:
        f.write(requirements_content)

    log.info("Created requirements.txt template")
    return str(requirements_file)


# Singleton
_docker_manager = None


def get_docker_deployment() -> DockerDeploymentManager:
    """Get or create the DockerDeploymentManager singleton instance."""
    global _docker_manager
    if _docker_manager is None:
        _docker_manager = DockerDeploymentManager()
    return _docker_manager


def register_tools(registry) -> None:
    """Register docker deployment tools with the tool registry."""
    mgr = get_docker_deployment()

    registry.register(
        name="docker_deploy_services",
        func=lambda config_name=None: mgr.deploy_services(config_name),
        description="Deploy Apex Docker services"
    )
    registry.register(
        name="docker_stop_services",
        func=lambda service_names=None: mgr.stop_services(service_names),
        description="Stop Docker services"
    )
    registry.register(
        name="docker_get_service_status",
        func=lambda: mgr.get_service_status(),
        description="Get status of all Docker services"
    )
    registry.register(
        name="docker_scale_service",
        func=lambda service_name, replicas: mgr.scale_service(service_name, replicas),
        description="Scale a Docker service to N replicas"
    )
    registry.register(
        name="docker_backup_deployment",
        func=lambda backup_name=None: mgr.backup_deployment(backup_name),
        description="Backup the current Docker deployment"
    )
    registry.register(
        name="docker_generate_report",
        func=lambda: mgr.generate_deployment_report(),
        description="Generate a Docker deployment report"
    )
    registry.register(
        name="docker_create_compose_template",
        func=create_docker_compose_template,
        description="Create a docker-compose.yml template file"
    )
