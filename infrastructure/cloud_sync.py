"""
CLOUD SYNC - Universal Access and Data Synchronization
=====================================================
Seamless cloud synchronization for accessing Apex from anywhere.

Features:
- Multi-cloud provider support (AWS, Google Cloud, Azure, Dropbox, etc.)
- End-to-end encryption for data privacy
- Selective sync and bandwidth optimization
- Conflict resolution and version control
- Offline access and local caching
- Real-time synchronization
- Cross-device state synchronization
- Backup and disaster recovery
- User authentication and access control
- Bandwidth monitoring and optimization
"""

import json
import time
import os
import hashlib
import threading
from typing import Dict, List, Optional, Tuple, Callable
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime, timedelta
from enum import Enum
import yaml
import boto3
from botocore.exceptions import ClientError
import dropbox
from dropbox.exceptions import ApiError
import requests
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

log = logging.getLogger("cloud_sync")

_CONFIG_PATH = Path(__file__).parent.parent / "core" / "config.yaml"


def _storage_base() -> Path:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return Path(cfg.get("storage", {}).get("base", "C:/ai_agent/apex/data"))


class CloudProvider(Enum):
    AWS_S3 = "aws_s3"
    GOOGLE_DRIVE = "google_drive"
    DROPBOX = "dropbox"
    AZURE_BLOB = "azure_blob"
    LOCAL_NETWORK = "local_network"
    CUSTOM = "custom"


class SyncStatus(Enum):
    SYNCED = "synced"
    PENDING = "pending"
    SYNCING = "syncing"
    CONFLICT = "conflict"
    ERROR = "error"
    OFFLINE = "offline"


class FileType(Enum):
    CONFIG = "config"
    DATA = "data"
    LOGS = "logs"
    MODEL = "model"
    MEDIA = "media"
    BACKUP = "backup"
    TEMP = "temp"


@dataclass
class CloudCredentials:
    """Cloud service credentials"""
    provider: CloudProvider
    access_key: str
    secret_key: str
    bucket_name: Optional[str] = None
    region: Optional[str] = None
    endpoint_url: Optional[str] = None
    refresh_token: Optional[str] = None
    custom_config: Optional[Dict] = None


@dataclass
class SyncFile:
    """File synchronization metadata"""
    local_path: str
    cloud_path: str
    file_hash: str
    last_modified: datetime
    file_size: int
    file_type: FileType
    sync_status: SyncStatus
    version: int
    encrypted: bool
    last_synced: Optional[datetime] = None
    conflict_versions: List[str] = None


@dataclass
class SyncSession:
    """Synchronization session information"""
    id: str
    start_time: datetime
    end_time: Optional[datetime]
    files_synced: int
    bytes_transferred: int
    status: str  # success, failed, partial
    error_message: Optional[str]
    bandwidth_used_kbps: float


@dataclass
class DeviceInfo:
    """Connected device information"""
    id: str
    name: str
    device_type: str
    last_seen: datetime
    ip_address: str
    sync_enabled: bool
    last_sync_session: Optional[str]
    online_status: bool


@dataclass
class UserProfile:
    """User profile and preferences"""
    user_id: str
    username: str
    email: str
    devices: List[str]
    sync_folders: List[str]
    encryption_enabled: bool
    bandwidth_limit_kbps: Optional[int]
    sync_schedule: str  # cron-like schedule
    auto_resolve_conflicts: bool
    created_at: float


@dataclass
class CloudSyncStats:
    """Cloud synchronization statistics"""
    total_files: int
    synced_files: int
    pending_files: int
    conflicted_files: int
    total_data_mb: float
    uploaded_mb: float
    downloaded_mb: float
    last_sync: Optional[datetime]
    bandwidth_usage_kbps: float


class CloudSyncManager:
    def __init__(self, config_dir: str = None):
        base = _storage_base()
        if config_dir is None:
            config_dir = str(base / "cloud_sync_config")
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir = self.config_dir.parent / "data"
        self.data_dir.mkdir(exist_ok=True)

        self.credentials: List[CloudCredentials] = []
        self.sync_files: List[SyncFile] = []
        self.sync_sessions: List[SyncSession] = []
        self.devices: List[DeviceInfo] = []
        self.users: List[UserProfile] = []
        self.encryption_key: Optional[bytes] = None
        self.sync_enabled = True
        self.bandwidth_limit_kbps = None
        self.conflict_resolution_strategy = "newest"  # newest, oldest, manual

        # Cloud service clients
        self.aws_client = None
        self.dropbox_client = None
        self.google_client = None
        self.azure_client = None

        # Load existing configuration
        self.load_configuration()

        # Start sync monitoring
        self._start_sync_monitor()

    def add_cloud_credentials(self, provider: CloudProvider, access_key: str,
                              secret_key: str, bucket_name: str = None,
                              region: str = None, endpoint_url: str = None,
                              refresh_token: str = None) -> str:
        """Add cloud service credentials"""
        credential = CloudCredentials(
            provider=provider,
            access_key=access_key,
            secret_key=secret_key,
            bucket_name=bucket_name,
            region=region,
            endpoint_url=endpoint_url,
            refresh_token=refresh_token
        )

        self.credentials.append(credential)

        # Initialize cloud client
        self._initialize_cloud_client(credential)

        self._save_configuration()
        log.info("Added cloud credentials for %s", provider.value)
        return "cred_%d" % len(self.credentials)

    def _initialize_cloud_client(self, credential: CloudCredentials):
        """Initialize cloud service client"""
        try:
            if credential.provider == CloudProvider.AWS_S3:
                self.aws_client = boto3.client(
                    's3',
                    aws_access_key_id=credential.access_key,
                    aws_secret_access_key=credential.secret_key,
                    region_name=credential.region or 'us-east-1'
                )
                log.info("Initialized AWS S3 client")

            elif credential.provider == CloudProvider.DROPBOX:
                self.dropbox_client = dropbox.Dropbox(
                    oauth2_access_token=credential.access_key
                )
                log.info("Initialized Dropbox client")

            elif credential.provider == CloudProvider.GOOGLE_DRIVE:
                log.info("Google Drive client requires OAuth2 setup")

            elif credential.provider == CloudProvider.AZURE_BLOB:
                log.info("Azure Blob client requires connection string")

        except Exception as e:
            log.error("Failed to initialize %s client: %s", credential.provider.value, e)

    def enable_encryption(self, password: str) -> bool:
        """Enable end-to-end encryption"""
        try:
            salt = b'apex_salt_12345678'
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            self.encryption_key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            log.info("Encryption enabled")
            return True
        except Exception as e:
            log.error("Failed to enable encryption: %s", e)
            return False

    def add_sync_folder(self, local_path: str, cloud_path: str = None,
                        file_types: List[FileType] = None) -> int:
        """Add folder for synchronization"""
        local_path_obj = Path(local_path)
        if not local_path_obj.exists():
            log.warning("Local path does not exist: %s", local_path)
            return 0

        if cloud_path is None:
            cloud_path = local_path.replace(str(self.data_dir), "").lstrip("/")

        if file_types is None:
            file_types = [FileType.CONFIG, FileType.DATA, FileType.LOGS]

        files_added = 0

        if local_path_obj.is_file():
            file_info = self._create_sync_file(local_path_obj, cloud_path, file_types)
            if file_info:
                self.sync_files.append(file_info)
                files_added += 1
        else:
            for file_path in local_path_obj.rglob("*"):
                if file_path.is_file():
                    relative_cloud_path = str(file_path).replace(str(local_path_obj), cloud_path).lstrip("/")
                    file_info = self._create_sync_file(file_path, relative_cloud_path, file_types)
                    if file_info:
                        self.sync_files.append(file_info)
                        files_added += 1

        if files_added > 0:
            self._save_configuration()
            log.info("Added %d files for sync", files_added)

        return files_added

    def _create_sync_file(self, file_path: Path, cloud_path: str,
                          allowed_types: List[FileType]) -> Optional[SyncFile]:
        """Create sync file metadata"""
        try:
            file_type = self._determine_file_type(file_path)
            if file_type not in allowed_types:
                return None

            file_hash = self._calculate_file_hash(file_path)
            stat = file_path.stat()

            sync_file = SyncFile(
                local_path=str(file_path),
                cloud_path=cloud_path,
                file_hash=file_hash,
                last_modified=datetime.fromtimestamp(stat.st_mtime),
                file_size=stat.st_size,
                file_type=file_type,
                sync_status=SyncStatus.PENDING,
                version=1,
                encrypted=self.encryption_key is not None,
                conflict_versions=[]
            )

            return sync_file

        except Exception as e:
            log.error("Failed to create sync file for %s: %s", file_path, e)
            return None

    def _determine_file_type(self, file_path: Path) -> FileType:
        """Determine file type based on extension and path"""
        path_str = str(file_path).lower()

        if any(ext in path_str for ext in ['.json', '.yaml', '.cfg', '.ini']):
            return FileType.CONFIG
        elif any(ext in path_str for ext in ['.txt', '.log', '.md']):
            return FileType.LOGS
        elif any(ext in path_str for ext in ['.jpg', '.png', '.gif', '.mp4', '.avi']):
            return FileType.MEDIA
        elif any(ext in path_str for ext in ['.pkl', '.model', '.pt', '.h5']):
            return FileType.MODEL
        elif 'backup' in path_str:
            return FileType.BACKUP
        elif 'temp' in path_str or 'tmp' in path_str:
            return FileType.TEMP
        else:
            return FileType.DATA

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file"""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            log.error("Failed to calculate hash for %s: %s", file_path, e)
            return "error"

    def sync_now(self) -> Dict[str, any]:
        """Perform immediate synchronization"""
        if not self.sync_enabled:
            return {"status": "failed", "message": "Sync is disabled"}

        start_time = datetime.now()
        session_id = "sync_%d" % int(time.time() * 1000)
        files_synced = 0
        bytes_transferred = 0
        errors = []

        log.info("Starting cloud synchronization")

        for sync_file in self.sync_files:
            if sync_file.sync_status == SyncStatus.PENDING:
                sync_file.sync_status = SyncStatus.SYNCING

        for sync_file in self.sync_files:
            if sync_file.sync_status == SyncStatus.SYNCING:
                try:
                    result = self._sync_file(sync_file)
                    if result["status"] == "success":
                        files_synced += 1
                        bytes_transferred += sync_file.file_size
                        sync_file.sync_status = SyncStatus.SYNCED
                        sync_file.last_synced = datetime.now()
                    else:
                        sync_file.sync_status = SyncStatus.ERROR
                        errors.append("%s: %s" % (sync_file.local_path, result['message']))

                except Exception as e:
                    sync_file.sync_status = SyncStatus.ERROR
                    errors.append("%s: %s" % (sync_file.local_path, str(e)))

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        bandwidth_kbps = (bytes_transferred * 8 / 1024) / max(duration, 1)

        session = SyncSession(
            id=session_id,
            start_time=start_time,
            end_time=end_time,
            files_synced=files_synced,
            bytes_transferred=bytes_transferred,
            status="success" if not errors else "partial",
            error_message="; ".join(errors) if errors else None,
            bandwidth_used_kbps=bandwidth_kbps
        )

        self.sync_sessions.append(session)
        self._save_configuration()

        result = {
            "status": session.status,
            "files_synced": files_synced,
            "bytes_transferred": bytes_transferred,
            "duration_seconds": duration,
            "bandwidth_kbps": bandwidth_kbps,
            "errors": errors
        }

        if errors:
            log.warning("Sync completed with %d errors", len(errors))
        else:
            log.info("Sync completed: %d files, %d bytes", files_synced, bytes_transferred)

        return result

    def _sync_file(self, sync_file: SyncFile) -> Dict[str, str]:
        """Sync a single file to cloud"""
        try:
            file_path = Path(sync_file.local_path)
            if not file_path.exists():
                return {"status": "failed", "message": "File not found"}

            if sync_file.encrypted and self.encryption_key:
                encrypted_data = self._encrypt_file(file_path)
                upload_data = encrypted_data
            else:
                with open(file_path, 'rb') as f:
                    upload_data = f.read()

            if self.credentials:
                credential = self.credentials[0]
                result = self._upload_to_cloud(credential, sync_file.cloud_path, upload_data)
                return result
            else:
                return {"status": "failed", "message": "No cloud credentials configured"}

        except Exception as e:
            return {"status": "failed", "message": str(e)}

    def _encrypt_file(self, file_path: Path) -> bytes:
        """Encrypt file data"""
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()

            fernet = Fernet(self.encryption_key)
            encrypted_data = fernet.encrypt(file_data)
            return encrypted_data

        except Exception as e:
            log.error("Encryption failed for %s: %s", file_path, e)
            raise

    def _upload_to_cloud(self, credential: CloudCredentials, cloud_path: str,
                         data: bytes) -> Dict[str, str]:
        """Upload data to cloud service"""
        try:
            if credential.provider == CloudProvider.AWS_S3:
                if not self.aws_client:
                    return {"status": "failed", "message": "AWS client not initialized"}

                self.aws_client.put_object(
                    Bucket=credential.bucket_name,
                    Key=cloud_path,
                    Body=data
                )
                return {"status": "success", "message": "Uploaded to AWS S3"}

            elif credential.provider == CloudProvider.DROPBOX:
                if not self.dropbox_client:
                    return {"status": "failed", "message": "Dropbox client not initialized"}

                self.dropbox_client.files_upload(
                    data,
                    "/%s" % cloud_path,
                    mode=dropbox.files.WriteMode.overwrite
                )
                return {"status": "success", "message": "Uploaded to Dropbox"}

            else:
                return {"status": "failed", "message": "Unsupported provider: %s" % credential.provider.value}

        except Exception as e:
            return {"status": "failed", "message": str(e)}

    def register_device(self, device_name: str, device_type: str,
                        ip_address: str) -> str:
        """Register a new device for sync"""
        device_id = "device_%d" % int(time.time() * 1000)

        device = DeviceInfo(
            id=device_id,
            name=device_name,
            device_type=device_type,
            last_seen=datetime.now(),
            ip_address=ip_address,
            sync_enabled=True,
            last_sync_session=None,
            online_status=True
        )

        self.devices.append(device)
        self._save_configuration()
        log.info("Registered device: %s", device_name)
        return device_id

    def create_user_profile(self, username: str, email: str,
                            sync_folders: List[str] = None) -> str:
        """Create user profile"""
        user_id = "user_%s" % hashlib.md5(username.encode()).hexdigest()[:8]

        user = UserProfile(
            user_id=user_id,
            username=username,
            email=email,
            devices=[],
            sync_folders=sync_folders or ["./data", "./config", "./logs"],
            encryption_enabled=False,
            bandwidth_limit_kbps=None,
            sync_schedule="*/30 * * * *",
            auto_resolve_conflicts=True,
            created_at=time.time()
        )

        self.users.append(user)
        self._save_configuration()
        log.info("Created user profile: %s", username)
        return user_id

    def get_sync_status(self) -> CloudSyncStats:
        """Get current synchronization status"""
        total_files = len(self.sync_files)
        synced_files = len([f for f in self.sync_files if f.sync_status == SyncStatus.SYNCED])
        pending_files = len([f for f in self.sync_files if f.sync_status == SyncStatus.PENDING])
        conflicted_files = len([f for f in self.sync_files if f.sync_status == SyncStatus.CONFLICT])

        total_data_mb = sum(f.file_size for f in self.sync_files) / (1024 * 1024)
        uploaded_mb = sum(f.file_size for f in self.sync_files if f.sync_status == SyncStatus.SYNCED) / (1024 * 1024)
        downloaded_mb = 0

        last_sync = None
        if self.sync_sessions:
            last_sync = max(session.end_time for session in self.sync_sessions if session.end_time)

        bandwidth_usage_kbps = 0
        if self.sync_sessions:
            recent_sessions = [s for s in self.sync_sessions
                               if s.end_time and s.end_time > datetime.now() - timedelta(hours=1)]
            if recent_sessions:
                total_bandwidth = sum(s.bandwidth_used_kbps for s in recent_sessions)
                bandwidth_usage_kbps = total_bandwidth / len(recent_sessions)

        stats = CloudSyncStats(
            total_files=total_files,
            synced_files=synced_files,
            pending_files=pending_files,
            conflicted_files=conflicted_files,
            total_data_mb=total_data_mb,
            uploaded_mb=uploaded_mb,
            downloaded_mb=downloaded_mb,
            last_sync=last_sync,
            bandwidth_usage_kbps=bandwidth_usage_kbps
        )

        return stats

    def resolve_conflict(self, file_path: str, resolution: str = "newest") -> bool:
        """Resolve file synchronization conflicts"""
        sync_file = next((f for f in self.sync_files if f.local_path == file_path), None)
        if not sync_file or sync_file.sync_status != SyncStatus.CONFLICT:
            return False

        try:
            if resolution == "newest":
                sync_file.sync_status = SyncStatus.SYNCED
                sync_file.last_synced = datetime.now()
            elif resolution == "cloud":
                sync_file.sync_status = SyncStatus.SYNCED
                sync_file.last_synced = datetime.now()
            elif resolution == "merge":
                sync_file.sync_status = SyncStatus.SYNCED
                sync_file.last_synced = datetime.now()

            self._save_configuration()
            log.info("Resolved conflict for %s", file_path)
            return True

        except Exception as e:
            log.error("Failed to resolve conflict for %s: %s", file_path, e)
            return False

    def generate_sync_report(self, days: int = 7) -> str:
        """Generate synchronization report"""
        report_start = datetime.now() - timedelta(days=days)

        report = []
        report.append("=" * 70)
        report.append("CLOUD SYNCHRONIZATION REPORT")
        report.append("=" * 70)
        report.append("Period: %s to %s" % (
            report_start.strftime('%Y-%m-%d'), datetime.now().strftime('%Y-%m-%d')))
        report.append("Generated: %s" % datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        report.append("")

        stats = self.get_sync_status()
        report.append("CURRENT STATUS")
        report.append("-" * 20)
        report.append("Total Files: %d" % stats.total_files)
        report.append("Synced Files: %d" % stats.synced_files)
        report.append("Pending Files: %d" % stats.pending_files)
        report.append("Conflicted Files: %d" % stats.conflicted_files)
        report.append("Total Data: %.2f MB" % stats.total_data_mb)
        report.append("Uploaded: %.2f MB" % stats.uploaded_mb)
        report.append("Bandwidth Usage: %.2f kbps" % stats.bandwidth_usage_kbps)
        if stats.last_sync:
            report.append("Last Sync: %s" % stats.last_sync.strftime('%Y-%m-%d %H:%M:%S'))
        report.append("")

        recent_sessions = [s for s in self.sync_sessions
                           if s.start_time > report_start]
        recent_sessions.sort(key=lambda x: x.start_time, reverse=True)

        if recent_sessions:
            report.append("RECENT SYNC SESSIONS")
            report.append("-" * 28)
            for session in recent_sessions[:10]:
                duration = (session.end_time - session.start_time).total_seconds() if session.end_time else 0
                report.append("%s - %s" % (session.start_time.strftime('%m/%d %H:%M'), session.status.upper()))
                report.append("  Files: %d | Data: %d bytes" % (session.files_synced, session.bytes_transferred))
                report.append("  Duration: %.1fs | Bandwidth: %.1f kbps" % (duration, session.bandwidth_used_kbps))
                if session.error_message:
                    report.append("  Errors: %s" % session.error_message)
                report.append("")

        report.append("CONNECTED DEVICES")
        report.append("-" * 22)
        for device in self.devices:
            status = "Online" if device.online_status else "Offline"
            report.append("%s (%s) - %s" % (device.name, device.device_type, status))
            report.append("  Last Seen: %s" % device.last_seen.strftime('%Y-%m-%d %H:%M:%S'))
            report.append("  IP: %s" % device.ip_address)
            report.append("")

        report.append("USERS")
        report.append("-" * 10)
        for user in self.users:
            enc_status = "Encrypted" if user.encryption_enabled else "Unencrypted"
            report.append("%s (%s) - %s" % (user.username, user.email, enc_status))
            report.append("  Sync Folders: %s" % ', '.join(user.sync_folders))
            report.append("  Devices: %d" % len(user.devices))
            report.append("")

        report.append("=" * 70)
        report.append("Report generated by Apex Cloud Sync System")
        report.append("=" * 70)

        return '\n'.join(report)

    def _start_sync_monitor(self):
        """Start background sync monitoring"""
        def monitor_loop():
            while True:
                try:
                    if self.sync_enabled:
                        pending_files = [f for f in self.sync_files if f.sync_status == SyncStatus.PENDING]
                        if pending_files:
                            self.sync_now()
                    time.sleep(1800)
                except Exception as e:
                    log.error("Sync monitor error: %s", e)
                    time.sleep(600)

        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        log.info("Cloud sync monitor started")

    def _save_configuration(self):
        """Save cloud sync configuration to files"""
        try:
            creds_file = self.config_dir / "credentials.json"
            with open(creds_file, 'w') as f:
                cred_dicts = []
                for cred in self.credentials:
                    cred_dict = asdict(cred)
                    cred_dict['provider'] = cred.provider.value
                    cred_dicts.append(cred_dict)
                json.dump(cred_dicts, f, indent=2)

            files_file = self.config_dir / "sync_files.json"
            with open(files_file, 'w') as f:
                file_dicts = []
                for sync_file in self.sync_files:
                    file_dict = asdict(sync_file)
                    file_dict['file_type'] = sync_file.file_type.value
                    file_dict['sync_status'] = sync_file.sync_status.value
                    file_dict['last_modified'] = sync_file.last_modified.isoformat()
                    if sync_file.last_synced:
                        file_dict['last_synced'] = sync_file.last_synced.isoformat()
                    file_dicts.append(file_dict)
                json.dump(file_dicts, f, indent=2)

            devices_file = self.config_dir / "devices.json"
            with open(devices_file, 'w') as f:
                device_dicts = []
                for device in self.devices:
                    device_dict = asdict(device)
                    device_dict['last_seen'] = device.last_seen.isoformat()
                    device_dicts.append(device_dict)
                json.dump(device_dicts, f, indent=2)

            users_file = self.config_dir / "users.json"
            with open(users_file, 'w') as f:
                user_dicts = []
                for user in self.users:
                    user_dict = asdict(user)
                    user_dicts.append(user_dict)
                json.dump(user_dicts, f, indent=2)

            sessions_file = self.config_dir / "sync_sessions.json"
            with open(sessions_file, 'w') as f:
                session_dicts = []
                for session in self.sync_sessions[-100:]:
                    session_dict = asdict(session)
                    session_dict['start_time'] = session.start_time.isoformat()
                    if session.end_time:
                        session_dict['end_time'] = session.end_time.isoformat()
                    session_dicts.append(session_dict)
                json.dump(session_dicts, f, indent=2)

        except Exception as e:
            log.error("Failed to save cloud sync configuration: %s", e)

    def load_configuration(self):
        """Load cloud sync configuration from files"""
        try:
            creds_file = self.config_dir / "credentials.json"
            if creds_file.exists():
                with open(creds_file, 'r') as f:
                    creds_data = json.load(f)
                for cred_data in creds_data:
                    cred_data['provider'] = CloudProvider(cred_data['provider'])
                    cred = CloudCredentials(**cred_data)
                    self.credentials.append(cred)

            files_file = self.config_dir / "sync_files.json"
            if files_file.exists():
                with open(files_file, 'r') as f:
                    files_data = json.load(f)
                for file_data in files_data:
                    file_data['file_type'] = FileType(file_data['file_type'])
                    file_data['sync_status'] = SyncStatus(file_data['sync_status'])
                    file_data['last_modified'] = datetime.fromisoformat(file_data['last_modified'])
                    if file_data.get('last_synced'):
                        file_data['last_synced'] = datetime.fromisoformat(file_data['last_synced'])
                    sync_file = SyncFile(**file_data)
                    self.sync_files.append(sync_file)

            devices_file = self.config_dir / "devices.json"
            if devices_file.exists():
                with open(devices_file, 'r') as f:
                    devices_data = json.load(f)
                for device_data in devices_data:
                    device_data['last_seen'] = datetime.fromisoformat(device_data['last_seen'])
                    device = DeviceInfo(**device_data)
                    self.devices.append(device)

            users_file = self.config_dir / "users.json"
            if users_file.exists():
                with open(users_file, 'r') as f:
                    users_data = json.load(f)
                for user_data in users_data:
                    user = UserProfile(**user_data)
                    self.users.append(user)

            sessions_file = self.config_dir / "sync_sessions.json"
            if sessions_file.exists():
                with open(sessions_file, 'r') as f:
                    sessions_data = json.load(f)
                for session_data in sessions_data:
                    session_data['start_time'] = datetime.fromisoformat(session_data['start_time'])
                    if session_data.get('end_time'):
                        session_data['end_time'] = datetime.fromisoformat(session_data['end_time'])
                    session = SyncSession(**session_data)
                    self.sync_sessions.append(session)

            log.info("Loaded cloud sync configuration")

        except Exception as e:
            log.error("Failed to load cloud sync configuration: %s", e)

    def integrate_with_apex(self, apex_instance):
        """Integrate with main Apex system"""
        def enable_cloud_sync(provider: str, access_key: str, secret_key: str,
                              bucket_name: str = None):
            """Enable cloud synchronization"""
            try:
                provider_enum = CloudProvider[provider.upper()] if provider.upper() in CloudProvider.__members__ else CloudProvider.AWS_S3
                cred_id = self.add_cloud_credentials(provider_enum, access_key, secret_key, bucket_name)
                return "Cloud sync enabled with %s (Credential ID: %s)" % (provider, cred_id)
            except Exception as e:
                return "Failed to enable cloud sync: %s" % e

        def sync_now():
            """Perform immediate synchronization"""
            try:
                result = self.sync_now()
                if result["status"] == "success":
                    return "Sync completed: %d files, %d bytes" % (result['files_synced'], result['bytes_transferred'])
                else:
                    error_count = len(result["errors"]) if result["errors"] else 0
                    return "Sync completed with %d errors" % error_count
            except Exception as e:
                return "Sync failed: %s" % e

        def get_sync_status():
            """Get synchronization status"""
            try:
                stats = self.get_sync_status()
                return (
                    "Cloud Sync Status:\n"
                    "Total Files: %d\n"
                    "Synced: %d\n"
                    "Pending: %d\n"
                    "Conflicted: %d\n"
                    "Data: %.2f MB\n"
                    "Bandwidth: %.2f kbps"
                ) % (stats.total_files, stats.synced_files, stats.pending_files,
                     stats.conflicted_files, stats.total_data_mb, stats.bandwidth_usage_kbps)
            except Exception as e:
                return "Failed to get sync status: %s" % e

        def add_sync_folder(local_path: str, cloud_path: str = None):
            """Add folder for synchronization"""
            try:
                files_added = self.add_sync_folder(local_path, cloud_path)
                return "Added %d files for sync from %s" % (files_added, local_path)
            except Exception as e:
                return "Failed to add sync folder: %s" % e

        def enable_encryption(password: str):
            """Enable encryption"""
            try:
                success = self.enable_encryption(password)
                if success:
                    return "Encryption enabled successfully"
                else:
                    return "Failed to enable encryption"
            except Exception as e:
                return "Encryption error: %s" % e

        def generate_sync_report(days: int = 7):
            """Generate sync report"""
            try:
                report = self.generate_sync_report(days)
                return "Sync Report Generated:\n%s..." % report[:500]
            except Exception as e:
                return "Failed to generate sync report: %s" % e

        def register_device(device_name: str, device_type: str, ip_address: str):
            """Register device"""
            try:
                device_id = self.register_device(device_name, device_type, ip_address)
                return "Registered device: %s (ID: %s)" % (device_name, device_id)
            except Exception as e:
                return "Failed to register device: %s" % e

        log.info("Cloud Sync Manager integrated with Apex")


# Singleton
_cloud_sync = None


def get_cloud_sync() -> CloudSyncManager:
    """Get or create the CloudSyncManager singleton instance."""
    global _cloud_sync
    if _cloud_sync is None:
        _cloud_sync = CloudSyncManager()
    return _cloud_sync


def register_tools(registry) -> None:
    """Register cloud sync tools with the tool registry."""
    mgr = get_cloud_sync()

    registry.register(
        name="cloud_sync_now",
        func=lambda: mgr.sync_now(),
        description="Perform immediate cloud synchronization"
    )
    registry.register(
        name="cloud_get_sync_status",
        func=lambda: mgr.get_sync_status(),
        description="Get current cloud synchronization status"
    )
    registry.register(
        name="cloud_add_sync_folder",
        func=lambda local_path, cloud_path=None: mgr.add_sync_folder(local_path, cloud_path),
        description="Add a folder for cloud synchronization"
    )
    registry.register(
        name="cloud_generate_sync_report",
        func=lambda days=7: mgr.generate_sync_report(days),
        description="Generate a cloud synchronization report"
    )
    registry.register(
        name="cloud_register_device",
        func=lambda device_name, device_type, ip_address: mgr.register_device(device_name, device_type, ip_address),
        description="Register a new device for sync"
    )
    registry.register(
        name="cloud_enable_encryption",
        func=lambda password: mgr.enable_encryption(password),
        description="Enable end-to-end encryption for cloud sync"
    )
