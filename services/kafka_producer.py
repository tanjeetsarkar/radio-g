import logging
from typing import Dict, List, Any, Optional, Union
from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient, NewTopic
from models.news_item import NewsItem

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NewsKafkaProducer:
    """
    Producer service for publishing news items to Kafka topics.
    Handles serialization and delivery callbacks.
    """

    def __init__(self, bootstrap_servers: Union[str, Dict] = "localhost:9093"):
        # Handle configuration: if dict, use it; if str, wrap it
        if isinstance(bootstrap_servers, dict):
            self.producer_config = bootstrap_servers.copy()
            self.bootstrap_servers = self.producer_config.get(
                "bootstrap.servers", "unknown"
            )
        else:
            self.bootstrap_servers = bootstrap_servers
            self.producer_config = {"bootstrap.servers": bootstrap_servers}

        # Add producer-specific defaults if not already present
        defaults = {
            "client.id": "news-producer",
            "linger.ms": 100,
            "compression.type": "gzip",
            "retries": 3,
        }
        for k, v in defaults.items():
            if k not in self.producer_config:
                self.producer_config[k] = v

        try:
            # Log config (masking password)
            log_config = self.producer_config.copy()
            if "sasl.password" in log_config:
                log_config["sasl.password"] = "***"

            logger.info(f"Kafka Producer initialized with config: {log_config}")
            self.producer = Producer(self.producer_config)
        except Exception as e:
            logger.error(f"Failed to initialize Kafka Producer: {e}")
            raise

    def _delivery_callback(self, err, msg):
        """Callback called when message is delivered or fails"""
        if err:
            logger.error(f"Message delivery failed: {err}")
        else:
            pass

    def create_topics_if_not_exist(self, topics: Optional[List[str]] = None):
        """Create Kafka topics if they don't exist"""
        if topics is None:
            topics = [
                "raw-news-feed",
                "news-english",
                "news-hindi",
                "news-bengali",
                "dlq-ingestion",
                "dlq-processing",
            ]

        # Use full config for AdminClient (needed for SASL auth)
        admin_client = AdminClient(self.producer_config)

        try:
            # Check existing topics
            cluster_metadata = admin_client.list_topics(timeout=10)
            existing_topics = cluster_metadata.topics

            new_topics = []
            for topic in topics:
                if topic not in existing_topics:
                    new_topics.append(
                        NewTopic(topic, num_partitions=3, replication_factor=3)
                    )

            if new_topics:
                fs = admin_client.create_topics(new_topics)
                for topic, f in fs.items():
                    try:
                        f.result()
                        logger.info(f"Topic '{topic}' created")
                    except Exception as e:
                        logger.error(f"Failed to create topic '{topic}': {e}")
            else:
                logger.info("All topics already exist")

        except Exception as e:
            logger.error(f"Error managing topics: {e}")

    def produce_news_item(self, news_item: NewsItem, topic: str = "raw-news-feed"):
        """Produce a single news item to a topic"""
        try:
            key = news_item.id
            value = news_item.to_json()

            self.producer.produce(
                topic=topic,
                key=key.encode("utf-8"),
                value=value.encode("utf-8"),
                callback=self._delivery_callback,
            )
            self.producer.poll(0)
            return True

        except Exception as e:
            logger.error(f"Failed to produce message: {e}")
            return False

    def produce_batch(
        self, news_items: List[NewsItem], topic: str = "raw-news-feed"
    ) -> Dict[str, Any]:
        stats = {"total": len(news_items), "delivered": 0, "failed": 0}
        for item in news_items:
            success = self.produce_news_item(item, topic=topic)
            if success:
                stats["delivered"] += 1
            else:
                stats["failed"] += 1

        stats["success_rate"] = (
            (stats["delivered"] / stats["total"]) * 100 if stats["total"] else 0
        )
        self.producer.flush()
        return stats

    def produce_dlq_event(self, topic: str, event: Any):
        try:
            # Handle both DLQEvent object or dict
            if hasattr(event, "to_json"):
                value = event.to_json()
                key = event.event_id if hasattr(event, "event_id") else None
            else:
                import json

                value = json.dumps(event)
                key = None

            self.producer.produce(
                topic=topic,
                key=key.encode("utf-8") if key else None,
                value=value.encode("utf-8"),
                callback=self._delivery_callback,
            )
            self.producer.poll(0)
            self.producer.flush()
            return True
        except Exception as e:
            logger.error(f"Failed to produce DLQ event: {e}")
            return False

    def produce_by_category(self, news_items: List[NewsItem]) -> Dict:
        stats = {}
        for item in news_items:
            category = item.category
            if category not in stats:
                stats[category] = {"total": 0, "delivered": 0, "failed": 0}
            stats[category]["total"] += 1

            success = self.produce_news_item(item, topic="raw-news-feed")
            if success:
                stats[category]["delivered"] += 1
            else:
                stats[category]["failed"] += 1

        for cat in stats:
            total = stats[cat]["total"]
            stats[cat]["success_rate"] = (
                (stats[cat]["delivered"] / total) * 100 if total > 0 else 0
            )

        self.producer.flush()
        return stats

    def get_stats(self):
        return {"queue_depth": len(self.producer)}

    def health_check(self) -> Dict:
        try:
            # Use full config for auth
            admin_client = AdminClient(self.producer_config)
            metadata = admin_client.list_topics(timeout=5)
            broker_count = len(metadata.brokers)
            topic_names = list(metadata.topics.keys())
            return {
                "connected": broker_count > 0,
                "status": "healthy" if broker_count > 0 else "unhealthy",
                "broker_count": broker_count,
                "topic_count": len(topic_names),
                "topics": topic_names,
            }
        except Exception as e:
            return {"connected": False, "status": "unhealthy", "error": str(e)}

    def close(self):
        self.producer.flush()
