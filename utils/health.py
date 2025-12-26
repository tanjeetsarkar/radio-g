"""
Health check utilities for production monitoring
"""

import logging
from typing import Dict, Optional
from datetime import datetime
import redis
from confluent_kafka.admin import AdminClient

logger = logging.getLogger(__name__)


class HealthChecker:
    """Health check manager for all services"""
    
    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        kafka_config: Optional[Dict] = None
    ):
        self.redis_client = redis_client
        self.kafka_config = kafka_config
        self.start_time = datetime.utcnow()
    
    def check_redis(self) -> Dict:
        """Check Redis connectivity"""
        try:
            if not self.redis_client:
                return {
                    "status": "unconfigured",
                    "healthy": False,
                    "message": "Redis client not configured"
                }
            
            # Ping Redis
            self.redis_client.ping()
            
            # Get info
            info = self.redis_client.info()
            
            return {
                "status": "healthy",
                "healthy": True,
                "connected_clients": info.get('connected_clients', 0),
                "used_memory_human": info.get('used_memory_human', 'unknown'),
                "uptime_seconds": info.get('uptime_in_seconds', 0)
            }
            
        except redis.ConnectionError as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "healthy": False,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Redis health check error: {e}")
            return {
                "status": "error",
                "healthy": False,
                "error": str(e)
            }
    
    def check_kafka(self) -> Dict:
        """Check Kafka connectivity"""
        try:
            if not self.kafka_config:
                return {
                    "status": "unconfigured",
                    "healthy": False,
                    "message": "Kafka config not provided"
                }
            
            # Create admin client
            admin_client = AdminClient(self.kafka_config)
            
            # Get cluster metadata (with timeout)
            metadata = admin_client.list_topics(timeout=5)
            
            return {
                "status": "healthy",
                "healthy": True,
                "broker_count": len(metadata.brokers),
                "topic_count": len(metadata.topics),
                "topics": list(metadata.topics.keys())[:10]  # First 10 topics
            }
            
        except Exception as e:
            logger.error(f"Kafka health check failed: {e}")
            return {
                "status": "unhealthy",
                "healthy": False,
                "error": str(e)
            }
    
    def check_disk_space(self) -> Dict:
        """Check available disk space"""
        try:
            import shutil
            
            total, used, free = shutil.disk_usage("/")
            
            # Convert to GB
            total_gb = total // (2**30)
            used_gb = used // (2**30)
            free_gb = free // (2**30)
            usage_percent = (used / total) * 100
            
            is_healthy = usage_percent < 90  # Alert if >90% used
            
            return {
                "status": "healthy" if is_healthy else "warning",
                "healthy": is_healthy,
                "total_gb": total_gb,
                "used_gb": used_gb,
                "free_gb": free_gb,
                "usage_percent": round(usage_percent, 2)
            }
            
        except Exception as e:
            logger.error(f"Disk space check failed: {e}")
            return {
                "status": "error",
                "healthy": False,
                "error": str(e)
            }
    
    def check_memory(self) -> Dict:
        """Check memory usage"""
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            
            is_healthy = memory.percent < 90  # Alert if >90% used
            
            return {
                "status": "healthy" if is_healthy else "warning",
                "healthy": is_healthy,
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_percent": memory.percent
            }
            
        except ImportError:
            # psutil not installed
            return {
                "status": "unavailable",
                "healthy": True,
                "message": "psutil not installed"
            }
        except Exception as e:
            logger.error(f"Memory check failed: {e}")
            return {
                "status": "error",
                "healthy": False,
                "error": str(e)
            }
    
    def get_uptime(self) -> Dict:
        """Get service uptime"""
        uptime = datetime.utcnow() - self.start_time
        
        return {
            "start_time": self.start_time.isoformat(),
            "uptime_seconds": int(uptime.total_seconds()),
            "uptime_human": str(uptime)
        }
    
    def full_health_check(self) -> Dict:
        """Run all health checks"""
        redis_health = self.check_redis()
        kafka_health = self.check_kafka()
        disk_health = self.check_disk_space()
        memory_health = self.check_memory()
        uptime_info = self.get_uptime()
        
        # Overall health
        all_healthy = all([
            redis_health.get('healthy', False),
            kafka_health.get('healthy', False),
            disk_health.get('healthy', False),
            memory_health.get('healthy', False)
        ])
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime": uptime_info,
            "checks": {
                "redis": redis_health,
                "kafka": kafka_health,
                "disk": disk_health,
                "memory": memory_health
            }
        }
    
    def readiness_check(self) -> bool:
        """
        Readiness check for K8s/Cloud Run
        Returns True if service is ready to accept traffic
        """
        redis_ok = self.check_redis().get('healthy', False)
        kafka_ok = self.check_kafka().get('healthy', False)
        
        return redis_ok and kafka_ok
    
    def liveness_check(self) -> bool:
        """
        Liveness check for K8s/Cloud Run
        Returns True if service is alive (should not be restarted)
        """
        # Basic check - is the process running?
        return True


# Singleton instance
_health_checker: Optional[HealthChecker] = None


def get_health_checker(
    redis_client: Optional[redis.Redis] = None,
    kafka_config: Optional[Dict] = None
) -> HealthChecker:
    """Get global health checker instance"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker(redis_client, kafka_config)
    return _health_checker


# Example usage
if __name__ == "__main__":
    # Initialize
    checker = HealthChecker()
    
    # Run checks
    health = checker.full_health_check()
    
    print("Health Status:")
    print(f"  Overall: {health['status']}")
    print(f"  Uptime: {health['uptime']['uptime_human']}")
    print(f"  Redis: {health['checks']['redis']['status']}")
    print(f"  Kafka: {health['checks']['kafka']['status']}")
    print(f"  Disk: {health['checks']['disk']['status']}")
    print(f"  Memory: {health['checks']['memory']['status']}")