#!/usr/bin/env python3
"""
Bolt AI — Enhanced Notification System
Multi-channel notifications: Discord, Email, Telegram, Console
"""

import json
import logging
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("bolt.notifications")


class NotificationLevel(Enum):
    """Notification importance levels."""
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4


@dataclass
class Notification:
    """Notification message."""
    title: str
    message: str
    level: NotificationLevel = NotificationLevel.INFO
    channel: str = "all"
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class NotificationManager:
    """
    Multi-channel notification manager.
    Supports Discord, Email, Telegram, and Console logging.
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.enabled_channels = []
        
        # Check which channels are configured
        self._check_channels()
    
    def _check_channels(self) -> None:
        """Check which notification channels are configured."""
        apis = self.config.get("apis", {})
        
        # Discord
        discord_webhook = apis.get("discord_webhook_url", "")
        if discord_webhook and not discord_webhook.startswith("YOUR_"):
            self.enabled_channels.append("discord")
        
        # Email
        email_config = self.config.get("notifications", {}).get("email", {})
        if email_config.get("enabled") and email_config.get("smtp_server"):
            self.enabled_channels.append("email")
        
        # Telegram
        telegram_config = self.config.get("notifications", {}).get("telegram", {})
        if telegram_config.get("enabled") and telegram_config.get("bot_token"):
            self.enabled_channels.append("telegram")
        
        # Console is always enabled
        self.enabled_channels.append("console")
        
        logger.info(f"📢 Notification channels enabled: {self.enabled_channels}")
    
    def send(self, notification: Notification) -> Dict:
        """
        Send notification to all enabled channels.
        
        Args:
            notification: Notification to send
            
        Returns:
            Dict with results for each channel
        """
        results = {}
        
        for channel in self.enabled_channels:
            try:
                if channel == "discord":
                    results[channel] = self._send_discord(notification)
                elif channel == "email":
                    results[channel] = self._send_email(notification)
                elif channel == "telegram":
                    results[channel] = self._send_telegram(notification)
                elif channel == "console":
                    results[channel] = self._send_console(notification)
            except Exception as e:
                logger.error(f"Failed to send {channel} notification: {e}")
                results[channel] = {"success": False, "error": str(e)}
        
        return results
    
    def _send_discord(self, notification: Notification) -> Dict:
        """Send Discord webhook notification."""
        apis = self.config.get("apis", {})
        webhook_url = apis.get("discord_webhook_url", "")
        
        if not webhook_url or webhook_url.startswith("YOUR_"):
            return {"success": False, "error": "Discord webhook not configured"}
        
        # Determine color based on level
        colors = {
            NotificationLevel.DEBUG: 0x95A5A6,
            NotificationLevel.INFO: 0x3498DB,
            NotificationLevel.WARNING: 0xF39C12,
            NotificationLevel.ERROR: 0xE74C3C,
            NotificationLevel.CRITICAL: 0xFF0000,
        }
        
        embed = {
            "title": notification.title,
            "description": notification.message,
            "color": colors.get(notification.level, 0x3498DB),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "footer": {"text": "Bolt AI Content Creator"},
        }
        
        # Add metadata as fields if present
        if notification.metadata:
            fields = []
            for key, value in notification.metadata.items():
                fields.append({"name": key, "value": str(value), "inline": True})
            if fields:
                embed["fields"] = fields
        
        try:
            response = requests.post(
                webhook_url,
                json={"embeds": [embed]},
                timeout=10
            )
            response.raise_for_status()
            return {"success": True, "message": "Discord notification sent"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _send_email(self, notification: Notification) -> Dict:
        """Send email notification."""
        email_config = self.config.get("notifications", {}).get("email", {})
        
        smtp_server = email_config.get("smtp_server")
        smtp_port = email_config.get("smtp_port", 587)
        username = email_config.get("username")
        password = email_config.get("password")
        recipients = email_config.get("recipients", [])
        
        if not all([smtp_server, username, password, recipients]):
            return {"success": False, "error": "Email not fully configured"}
        
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[Bolt AI] {notification.title}"
        msg["From"] = username
        msg["To"] = ", ".join(recipients)
        
        # Plain text version
        text_content = f"""
{notification.title}
{'=' * len(notification.title)}

{notification.message}

---
Bolt AI Content Creator
{datetime.now().isoformat()}
        """
        
        # HTML version
        html_content = f"""
<html>
<body style="font-family: Arial, sans-serif;">
    <h2 style="color: #0047AB;">{notification.title}</h2>
    <hr>
    <p>{notification.message.replace('\n', '<br>')}</p>
    <hr>
    <p style="color: #666; font-size: 12px;">
        Bolt AI Content Creator<br>
        {datetime.now().isoformat()}
    </p>
</body>
</html>
        """
        
        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))
        
        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
            server.quit()
            return {"success": True, "message": f"Email sent to {len(recipients)} recipients"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _send_telegram(self, notification: Notification) -> Dict:
        """Send Telegram notification."""
        telegram_config = self.config.get("notifications", {}).get("telegram", {})
        
        bot_token = telegram_config.get("bot_token")
        chat_id = telegram_config.get("chat_id")
        
        if not all([bot_token, chat_id]):
            return {"success": False, "error": "Telegram not configured"}
        
        # Format message
        emoji = {
            NotificationLevel.DEBUG: "🔍",
            NotificationLevel.INFO: "ℹ️",
            NotificationLevel.WARNING: "⚠️",
            NotificationLevel.ERROR: "❌",
            NotificationLevel.CRITICAL: "🚨",
        }
        
        text = f"""
{emoji.get(notification.level, 'ℹ️')} *{notification.title}*

{notification.message}

---
🤖 Bolt AI | {datetime.now().strftime('%Y-%m-%d %H:%M')}
        """
        
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown"
            }
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            return {"success": True, "message": "Telegram notification sent"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _send_console(self, notification: Notification) -> Dict:
        """Log to console."""
        # Use appropriate logging level
        level_emoji = {
            NotificationLevel.DEBUG: "🔍",
            NotificationLevel.INFO: "ℹ️",
            NotificationLevel.WARNING: "⚠️",
            NotificationLevel.ERROR: "❌",
            NotificationLevel.CRITICAL: "🚨",
        }
        
        emoji = level_emoji.get(notification.level, "ℹ️")
        print(f"\n{emoji} {notification.title}")
        print(f"   {notification.message}\n")
        
        return {"success": True, "message": "Logged to console"}
    
    # Convenience methods for common notifications
    
    def notify_pipeline_start(self, config: Dict = None) -> Dict:
        """Notify that pipeline has started."""
        notification = Notification(
            title="🚀 Pipeline Started",
            message="Bolt AI daily content pipeline has begun.",
            level=NotificationLevel.INFO,
            metadata=config or {}
        )
        return self.send(notification)
    
    def notify_pipeline_complete(self, elapsed_seconds: float, config: Dict = None) -> Dict:
        """Notify that pipeline completed."""
        notification = Notification(
            title="✅ Pipeline Complete",
            message=f"Content pipeline finished in {elapsed_seconds:.0f} seconds.",
            level=NotificationLevel.INFO,
            metadata=config or {}
        )
        return self.send(notification)
    
    def notify_error(self, step: str, error: str, config: Dict = None) -> Dict:
        """Notify about an error."""
        notification = Notification(
            title=f"❌ {step} Failed",
            message=error,
            level=NotificationLevel.ERROR,
            metadata=config or {}
        )
        return self.send(notification)
    
    def notify_quality_alert(self, score: float, script: str, config: Dict = None) -> Dict:
        """Notify about quality gate alert."""
        status = "✅ PASSED" if score >= 8.5 else "⚠️ NEEDS REVIEW"
        notification = Notification(
            title=f"📝 Quality Check {status}",
            message=f"Score: {score:.1f}/10\nScript preview: {script[:100]}...",
            level=NotificationLevel.WARNING if score < 8.5 else NotificationLevel.INFO,
            metadata=config or {}
        )
        return self.send(notification)
    
    def notify_published(self, platforms: List[str], config: Dict = None) -> Dict:
        """Notify about successful publishing."""
        platform_str = ", ".join([p.title() for p in platforms])
        notification = Notification(
            title="🚀 Content Published",
            message=f"Successfully published to: {platform_str}",
            level=NotificationLevel.INFO,
            metadata=config or {}
        )
        return self.send(notification)
    
    def notify_backup(self, backup_info: Dict, config: Dict = None) -> Dict:
        """Notify about backup completion."""
        notification = Notification(
            title="💾 Backup Complete",
            message=f"Backup created: {backup_info.get('size_mb', 0)} MB",
            level=NotificationLevel.INFO,
            metadata=config or {}
        )
        return self.send(notification)


# Singleton instance
_notification_manager = None

def get_notification_manager(config: Dict = None) -> NotificationManager:
    """Get or create notification manager singleton."""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager(config)
    return _notification_manager


# Convenience function for simple notifications
def send_notification(title: str, message: str, level: str = "info") -> Dict:
    """Simple notification function."""
    level_map = {
        "debug": NotificationLevel.DEBUG,
        "info": NotificationLevel.INFO,
        "warning": NotificationLevel.WARNING,
        "error": NotificationLevel.ERROR,
        "critical": NotificationLevel.CRITICAL,
    }
    
    notification = Notification(
        title=title,
        message=message,
        level=level_map.get(level.lower(), NotificationLevel.INFO)
    )
    
    manager = get_notification_manager()
    return manager.send(notification)


if __name__ == "__main__":
    # Test notifications
    print("📢 Bolt AI Notification System Test")
    
    # Test with default config (console only)
    manager = NotificationManager()
    
    # Send test notifications
    print("\n1. Testing INFO notification:")
    manager.send(Notification(
        title="Test Info",
        message="This is a test info message from Bolt AI.",
        level=NotificationLevel.INFO
    ))
    
    print("\n2. Testing WARNING notification:")
    manager.send(Notification(
        title="Test Warning", 
        message="This is a test warning message.",
        level=NotificationLevel.WARNING
    ))
    
    print("\n3. Testing ERROR notification:")
    manager.send(Notification(
        title="Test Error",
        message="This is a test error message.",
        level=NotificationLevel.ERROR
    ))
