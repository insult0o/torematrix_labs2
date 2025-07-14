"""Alert system for metadata extraction monitoring."""

from typing import Dict, List, Any, Optional
import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass


@dataclass
class Alert:
    """Alert information."""
    alert_id: str
    level: str  # critical, warning, info
    component: str
    message: str
    timestamp: datetime
    metadata: Dict[str, Any]


class MetadataAlertSystem:
    """Alert system for metadata extraction monitoring."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.active_alerts: List[Alert] = []
        
    async def check_error_rate_alert(self, error_rate: float) -> Optional[Alert]:
        """Check if error rate exceeds threshold."""
        threshold = self.config.get("error_rate_threshold", 0.05)
        
        if error_rate > threshold:
            return Alert(
                alert_id=f"error_rate_{int(datetime.utcnow().timestamp())}",
                level="critical" if error_rate > threshold * 2 else "warning",
                component="metadata_extraction",
                message=f"Error rate {error_rate:.2%} exceeds threshold {threshold:.2%}",
                timestamp=datetime.utcnow(),
                metadata={"error_rate": error_rate, "threshold": threshold}
            )
        return None
        
    async def check_response_time_alert(self, avg_response_time: float) -> Optional[Alert]:
        """Check if response time exceeds threshold."""
        threshold = self.config.get("response_time_threshold", 5.0)
        
        if avg_response_time > threshold:
            return Alert(
                alert_id=f"response_time_{int(datetime.utcnow().timestamp())}",
                level="warning",
                component="metadata_extraction",
                message=f"Average response time {avg_response_time:.2f}s exceeds threshold {threshold}s",
                timestamp=datetime.utcnow(),
                metadata={"response_time": avg_response_time, "threshold": threshold}
            )
        return None
        
    async def send_alert(self, alert: Alert):
        """Send alert notification."""
        self.active_alerts.append(alert)
        self.logger.warning(f"ALERT [{alert.level.upper()}] {alert.component}: {alert.message}")
        
        # In production, this would send to webhook, email, etc.
        webhook_url = self.config.get("webhook_url")
        if webhook_url:
            # Would send HTTP request to webhook
            pass
            
    async def get_active_alerts(self) -> List[Alert]:
        """Get currently active alerts."""
        return self.active_alerts.copy()
        
    async def clear_alert(self, alert_id: str):
        """Clear an active alert."""
        self.active_alerts = [
            alert for alert in self.active_alerts 
            if alert.alert_id != alert_id
        ]