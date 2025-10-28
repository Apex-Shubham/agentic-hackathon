"""
Self-Healing System
Monitors bot health, handles errors, and implements auto-recovery mechanisms
"""
import time
import traceback
from typing import Dict, Optional
from datetime import datetime, timedelta, timezone
import requests
from config import ALERT_WEBHOOK_URL


class HealthMonitor:
    """Monitors system health and implements self-healing mechanisms"""
    
    def __init__(self):
        self.last_successful_cycle = datetime.now(timezone.utc)
        self.error_count = 0
        self.consecutive_errors = 0
        self.api_health = {
            'binance': True,
            'deepseek': True
        }
        self.last_health_check = datetime.now(timezone.utc)
        self.recovery_attempts = 0
        self.max_recovery_attempts = 5
        self.critical_errors = []
    
    def monitor_health(self) -> Dict[str, bool]:
        """
        Check overall system health
        Returns: Dictionary of health indicators
        """
        current_time = datetime.now(timezone.utc)
        
        # Check if main loop is stuck
        time_since_cycle = (current_time - self.last_successful_cycle).total_seconds()
        loop_healthy = time_since_cycle < 600  # Should cycle at least every 10 minutes
        
        # Check error rate
        error_rate_healthy = self.consecutive_errors < 5
        
        # Check API health
        apis_healthy = all(self.api_health.values())
        
        # Overall health
        is_healthy = loop_healthy and error_rate_healthy and apis_healthy
        
        health_status = {
            'overall': is_healthy,
            'loop_running': loop_healthy,
            'error_rate_ok': error_rate_healthy,
            'apis_ok': apis_healthy,
            'time_since_cycle': time_since_cycle,
            'consecutive_errors': self.consecutive_errors,
            'total_errors': self.error_count
        }
        
        self.last_health_check = current_time
        
        return health_status
    
    def handle_error(self, error: Exception, context: Dict = None):
        """
        Handle an error with recovery logic
        """
        self.error_count += 1
        self.consecutive_errors += 1
        
        error_info = {
            'type': type(error).__name__,
            'message': str(error),
            'context': context or {},
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'traceback': traceback.format_exc()
        }
        
        # Log error
        from logger import get_logger
        logger = get_logger()
        logger.log_error(error, context)
        
        # Determine error severity
        if self._is_critical_error(error):
            self.critical_errors.append(error_info)
            self._handle_critical_error(error, context)
        else:
            self._handle_recoverable_error(error, context)
    
    def _is_critical_error(self, error: Exception) -> bool:
        """Determine if error is critical"""
        critical_keywords = [
            'authentication',
            'authorization',
            'invalid api key',
            'permission denied',
            'insufficient balance'
        ]
        
        error_str = str(error).lower()
        return any(keyword in error_str for keyword in critical_keywords)
    
    def _handle_critical_error(self, error: Exception, context: Dict):
        """Handle critical errors"""
        print(f"🚨 CRITICAL ERROR: {error}")
        self.send_critical_alert(f"Critical Error: {error}")
        
        # Don't attempt too many recoveries
        if self.recovery_attempts >= self.max_recovery_attempts:
            print("⚠️ Max recovery attempts reached. Manual intervention may be required.")
            return
        
        self.recovery_attempts += 1
    
    def _handle_recoverable_error(self, error: Exception, context: Dict):
        """Handle recoverable errors"""
        print(f"⚠️ Recoverable error: {error}")
        
        # Implement backoff strategy
        backoff_time = min(2 ** self.consecutive_errors, 60)  # Max 60 seconds
        print(f"   Backing off for {backoff_time}s before retry...")
        time.sleep(backoff_time)
    
    def handle_api_failure(self, service: str, error: Exception):
        """
        Handle API failures with specific recovery logic
        """
        print(f"📡 API failure detected: {service}")
        
        self.api_health[service] = False
        
        # Try to recover based on service
        if service == 'binance':
            self._recover_binance_connection()
        elif service == 'deepseek':
            self._recover_deepseek_connection()
        
        # If recovery successful, mark as healthy
        # This will be updated on next successful call
    
    def _recover_binance_connection(self):
        """Attempt to recover Binance connection"""
        print("   Attempting to recover Binance connection...")
        
        try:
            from data_pipeline import DataPipeline
            pipeline = DataPipeline()
            
            if pipeline.test_connection():
                self.api_health['binance'] = True
                print("   ✅ Binance connection recovered")
                return True
            else:
                print("   ❌ Binance connection recovery failed")
                return False
                
        except Exception as e:
            print(f"   ❌ Error recovering Binance connection: {e}")
            return False
    
    def _recover_deepseek_connection(self):
        """Attempt to recover DeepSeek connection"""
        print("   Attempting to recover DeepSeek connection...")
        
        try:
            # Simple test query
            from deepseek_agent import get_deepseek_agent
            agent = get_deepseek_agent()
            
            # Try a simple decision
            test_decision = agent._get_hold_decision("Connection test")
            if test_decision:
                self.api_health['deepseek'] = True
                print("   ✅ DeepSeek connection recovered")
                return True
            
        except Exception as e:
            print(f"   ❌ Error recovering DeepSeek connection: {e}")
            return False
    
    def validate_data_integrity(self, data: Dict) -> bool:
        """
        Validate that data is complete and not corrupted
        """
        if not data:
            return False
        
        # Check for error flags
        if 'error' in data:
            return False
        
        # Check for required fields (for market data)
        if 'symbol' in data:
            required_fields = ['price', 'indicators', 'regime']
            if not all(field in data for field in required_fields):
                print(f"⚠️ Incomplete market data for {data.get('symbol')}")
                return False
        
        # Check for NaN or invalid values
        if 'indicators' in data:
            indicators = data['indicators']
            for key, value in indicators.items():
                if value is None or (isinstance(value, float) and (value != value)):  # NaN check
                    print(f"⚠️ Invalid indicator value: {key} = {value}")
                    return False
        
        return True
    
    def record_successful_cycle(self):
        """Record that a trading cycle completed successfully"""
        self.last_successful_cycle = datetime.now(timezone.utc)
        self.consecutive_errors = 0
        self.recovery_attempts = 0
    
    def auto_restart_on_crash(self):
        """
        Detect if bot needs to restart and prepare for it
        This is called from within the main loop
        """
        health = self.monitor_health()
        
        if not health['overall']:
            print("⚠️ Health check failed, attempting recovery...")
            
            # Try auto-healing
            if self._attempt_auto_heal():
                print("✅ Auto-healing successful")
                return False  # Don't need to restart
            else:
                print("❌ Auto-healing failed, restart may be needed")
                return True  # Signal that restart is needed
        
        return False
    
    def _attempt_auto_heal(self) -> bool:
        """Attempt automatic healing of known issues"""
        print("🔧 Attempting auto-heal...")
        
        # Check and fix API connections
        for service, healthy in self.api_health.items():
            if not healthy:
                if service == 'binance':
                    if self._recover_binance_connection():
                        continue
                    else:
                        return False
                elif service == 'deepseek':
                    if self._recover_deepseek_connection():
                        continue
                    else:
                        # DeepSeek down is not fatal - we have fallback
                        print("   ℹ️ DeepSeek unavailable, will use fallback logic")
        
        # Clear error counters if we made it this far
        self.consecutive_errors = 0
        
        return True
    
    def send_critical_alert(self, message: str):
        """Send critical alert via webhook (if configured)"""
        if not ALERT_WEBHOOK_URL:
            return
        
        try:
            payload = {
                'text': f'🚨 TRADING BOT ALERT 🚨\n{message}',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            response = requests.post(
                ALERT_WEBHOOK_URL,
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                print(f"   📤 Alert sent: {message}")
            else:
                print(f"   ⚠️ Failed to send alert: {response.status_code}")
                
        except Exception as e:
            print(f"   ⚠️ Error sending alert: {e}")
    
    def get_health_summary(self) -> Dict:
        """Get comprehensive health summary"""
        health = self.monitor_health()
        
        return {
            'status': 'HEALTHY' if health['overall'] else 'UNHEALTHY',
            'uptime_seconds': (datetime.now(timezone.utc) - self.last_successful_cycle).total_seconds(),
            'total_errors': self.error_count,
            'consecutive_errors': self.consecutive_errors,
            'critical_errors': len(self.critical_errors),
            'api_status': self.api_health,
            'recovery_attempts': self.recovery_attempts
        }
    
    def reset_error_counters(self):
        """Reset error counters (called after successful operation)"""
        self.consecutive_errors = 0
        self.recovery_attempts = 0


# Global health monitor instance
_monitor_instance = None

def get_health_monitor() -> HealthMonitor:
    """Get or create health monitor instance"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = HealthMonitor()
    return _monitor_instance

