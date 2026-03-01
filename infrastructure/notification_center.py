"""
NOTIFICATION CENTER - Centralized Alert Management
=================================================
Unified notification system for all Apex alerts and messages.

Features:
- Multi-channel notifications (desktop, mobile, email, SMS)
- Priority-based alert routing
- Notification history and logging
- Custom notification rules
- Do Not Disturb scheduling
- Alert grouping and consolidation
- Rich notification formatting
- Integration with external services
"""

import json
import time
from typing import Dict, List, Optional, Callable
import logging
import yaml
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import threading

log = logging.getLogger("notification_center")

_CONFIG_PATH = Path(__file__).parent.parent / "core" / "config.yaml"


def _storage_base() -> Path:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return Path(cfg.get("storage", {}).get("base", "C:/ai_agent/apex/data"))


class NotificationPriority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class NotificationChannel(Enum):
    DESKTOP = "desktop"
    MOBILE = "mobile"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    AUDIO = "audio"
    VISUAL = "visual"


class NotificationStatus(Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"


@dataclass
class Notification:
    """Individual notification"""
    id: str
    title: str
    message: str
    priority: NotificationPriority
    channels: List[NotificationChannel]
    source: str  # What generated the notification
    category: str  # e.g., system, security, schedule, reminder
    timestamp: datetime
    status: NotificationStatus
    acknowledged_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None
    metadata: Optional[Dict[str, any]] = None
    snoozed_until: Optional[datetime] = None

    def to_dict(self) -> Dict:
        """Convert notification to dictionary for serialization"""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat() if self.timestamp else None
        result['acknowledged_at'] = self.acknowledged_at.isoformat() if self.acknowledged_at else None
        result['dismissed_at'] = self.dismissed_at.isoformat() if self.dismissed_at else None
        result['snoozed_until'] = self.snoozed_until.isoformat() if self.snoozed_until else None
        result['priority'] = self.priority.value
        result['status'] = self.status.value
        result['channels'] = [channel.value for channel in self.channels]
        return result


@dataclass
class NotificationRule:
    """Rules for automatic notification handling"""
    name: str
    condition: Callable[[Notification], bool]
    action: Callable[[Notification], None]
    enabled: bool = True
    priority_filter: Optional[List[NotificationPriority]] = None
    category_filter: Optional[List[str]] = None


class DNDPeriod:
    """Do Not Disturb period configuration"""
    def __init__(self, start_time: str, end_time: str, days: List[int] = None):
        self.start_time = datetime.strptime(start_time, "%H:%M").time()
        self.end_time = datetime.strptime(end_time, "%H:%M").time()
        self.days = days or list(range(7))  # 0=Monday, 6=Sunday

    def is_active(self) -> bool:
        """Check if DND period is currently active"""
        now = datetime.now()
        current_day = now.weekday()
        current_time = now.time()

        if current_day not in self.days:
            return False

        if self.start_time <= self.end_time:
            return self.start_time <= current_time <= self.end_time
        else:
            return current_time >= self.start_time or current_time <= self.end_time


class NotificationCenter:
    """Main notification management system"""

    def __init__(self, storage_path: Optional[str] = None):
        if storage_path is None:
            storage_path = str(_storage_base() / "notifications" / "notifications.json")
        self.notifications: List[Notification] = []
        self.rules: List[NotificationRule] = []
        self.dnd_periods: List[DNDPeriod] = []
        self.channel_handlers: Dict[NotificationChannel, Callable] = {}
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

        if self.storage_path.exists():
            self._load_notifications()

    def add_channel_handler(self, channel: NotificationChannel, handler: Callable):
        """Register a handler function for a notification channel"""
        self.channel_handlers[channel] = handler

    def add_rule(self, rule: NotificationRule):
        """Add an automatic notification handling rule"""
        self.rules.append(rule)

    def add_dnd_period(self, dnd_period: DNDPeriod):
        """Add a do-not-disturb period"""
        self.dnd_periods.append(dnd_period)

    def _is_dnd_active(self) -> bool:
        """Check if any DND period is currently active"""
        return any(period.is_active() for period in self.dnd_periods)

    def create_notification(self,
                            title: str,
                            message: str,
                            priority: NotificationPriority,
                            channels: List[NotificationChannel],
                            source: str = "system",
                            category: str = "general",
                            metadata: Optional[Dict] = None) -> Notification:
        """Create a new notification"""
        notification_id = hashlib.md5(("%s%s%s" % (title, message, datetime.now())).encode()).hexdigest()

        notification = Notification(
            id=notification_id,
            title=title,
            message=message,
            priority=priority,
            channels=channels,
            source=source,
            category=category,
            timestamp=datetime.now(),
            status=NotificationStatus.PENDING,
            metadata=metadata
        )

        return notification

    def send_notification(self, notification: Notification) -> bool:
        """Send notification through configured channels"""
        if self._is_dnd_active() and notification.priority != NotificationPriority.CRITICAL:
            log.info("DND active, delaying non-critical notification: %s", notification.title)
            return False

        success = True
        sent_channels = []

        for channel in notification.channels:
            if channel in self.channel_handlers:
                try:
                    self.channel_handlers[channel](notification)
                    sent_channels.append(channel)
                except Exception as e:
                    log.error("Failed to send notification via %s: %s", channel, e)
                    success = False

        if sent_channels:
            notification.status = NotificationStatus.SENT

        self._apply_rules(notification)

        with self._lock:
            self.notifications.append(notification)
            if self.storage_path:
                self._save_notifications()

        return success

    def _apply_rules(self, notification: Notification):
        """Apply automatic rules to notification"""
        for rule in self.rules:
            if not rule.enabled:
                continue

            if rule.priority_filter and notification.priority not in rule.priority_filter:
                continue
            if rule.category_filter and notification.category not in rule.category_filter:
                continue

            if rule.condition(notification):
                try:
                    rule.action(notification)
                except Exception as e:
                    log.error("Rule '%s' failed: %s", rule.name, e)

    def acknowledge_notification(self, notification_id: str) -> bool:
        """Mark notification as acknowledged"""
        with self._lock:
            for notification in self.notifications:
                if notification.id == notification_id:
                    notification.status = NotificationStatus.ACKNOWLEDGED
                    notification.acknowledged_at = datetime.now()
                    if self.storage_path:
                        self._save_notifications()
                    return True
        return False

    def dismiss_notification(self, notification_id: str) -> bool:
        """Dismiss notification"""
        with self._lock:
            for notification in self.notifications:
                if notification.id == notification_id:
                    notification.status = NotificationStatus.DISMISSED
                    notification.dismissed_at = datetime.now()
                    if self.storage_path:
                        self._save_notifications()
                    return True
        return False

    def snooze_notification(self, notification_id: str, until: datetime) -> bool:
        """Snooze notification until specified time"""
        with self._lock:
            for notification in self.notifications:
                if notification.id == notification_id:
                    notification.snoozed_until = until
                    notification.status = NotificationStatus.PENDING
                    if self.storage_path:
                        self._save_notifications()
                    return True
        return False

    def get_notifications(self,
                          priority: Optional[NotificationPriority] = None,
                          category: Optional[str] = None,
                          status: Optional[NotificationStatus] = None,
                          limit: Optional[int] = None) -> List[Notification]:
        """Get filtered notifications"""
        with self._lock:
            filtered = self.notifications.copy()

        if priority:
            filtered = [n for n in filtered if n.priority == priority]
        if category:
            filtered = [n for n in filtered if n.category == category]
        if status:
            filtered = [n for n in filtered if n.status == status]

        filtered.sort(key=lambda x: x.timestamp, reverse=True)

        if limit:
            filtered = filtered[:limit]

        return filtered

    def clear_notifications(self, older_than: Optional[timedelta] = None):
        """Clear old notifications"""
        with self._lock:
            if older_than:
                cutoff = datetime.now() - older_than
                self.notifications = [
                    n for n in self.notifications
                    if n.timestamp > cutoff
                ]
            else:
                self.notifications.clear()

            if self.storage_path:
                self._save_notifications()

    def _save_notifications(self):
        """Save notifications to persistent storage"""
        if not self.storage_path:
            return

        try:
            data = {
                'notifications': [n.to_dict() for n in self.notifications[-1000:]],
                'saved_at': datetime.now().isoformat()
            }

            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            log.error("Failed to save notifications: %s", e)

    def _load_notifications(self):
        """Load notifications from persistent storage"""
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)

            for notif_data in data.get('notifications', []):
                for key in ['timestamp', 'acknowledged_at', 'dismissed_at', 'snoozed_until']:
                    if notif_data.get(key):
                        notif_data[key] = datetime.fromisoformat(notif_data[key])

                notif_data['priority'] = NotificationPriority(notif_data['priority'])
                notif_data['status'] = NotificationStatus(notif_data['status'])
                notif_data['channels'] = [NotificationChannel(c) for c in notif_data['channels']]

                notification = Notification(**notif_data)
                self.notifications.append(notification)

        except Exception as e:
            log.error("Failed to load notifications: %s", e)


# Example channel handlers
def desktop_notification_handler(notification: Notification):
    """Example desktop notification handler"""
    print("[DESKTOP] %s: %s (Priority: %s)" % (
        notification.title, notification.message, notification.priority.value))


def email_notification_handler(notification: Notification):
    """Example email notification handler"""
    print("[EMAIL] To: user@example.com - %s" % notification.title)


def sms_notification_handler(notification: Notification):
    """Example SMS notification handler"""
    print("[SMS] To: +1234567890 - %s" % notification.message)


# Singleton
_notification_center = None


def get_notification_center() -> NotificationCenter:
    """Get or create the NotificationCenter singleton instance."""
    global _notification_center
    if _notification_center is None:
        _notification_center = NotificationCenter()
    return _notification_center


def register_tools(registry) -> None:
    """Register notification tools with the tool registry."""
    nc = get_notification_center()

    registry.register(
        name="notify_send",
        func=lambda title, message, priority="normal", source="system", category="general": nc.send_notification(
            nc.create_notification(
                title=title,
                message=message,
                priority=NotificationPriority(priority),
                channels=[NotificationChannel.DESKTOP],
                source=source,
                category=category
            )
        ),
        description="Send a notification via configured channels"
    )
    registry.register(
        name="notify_acknowledge",
        func=lambda notification_id: nc.acknowledge_notification(notification_id),
        description="Acknowledge a notification by ID"
    )
    registry.register(
        name="notify_dismiss",
        func=lambda notification_id: nc.dismiss_notification(notification_id),
        description="Dismiss a notification by ID"
    )
    registry.register(
        name="notify_get_recent",
        func=lambda limit=20: nc.get_notifications(limit=limit),
        description="Get recent notifications"
    )
    registry.register(
        name="notify_clear_old",
        func=lambda days=7: nc.clear_notifications(older_than=timedelta(days=days)),
        description="Clear notifications older than N days"
    )
