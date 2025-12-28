import logging
from typing import Dict, List, Any, Optional
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

    def __init__(self, bootstrap_servers: str = "localhost:9093"):
        self.bootstrap_servers = bootstrap_servers
        self.producer_config = {
            "bootstrap.servers": bootstrap_servers,
            "client.id": "news-producer",
            "linger.ms": 100,  # Small delay to allow batching
            "compression.type": "gzip",
            "retries": 3,
        }

        try:
            self.producer = Producer(self.producer_config)
            logger.info(f"Kafka Producer initialized (servers: {bootstrap_servers})")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka Producer: {e}")
            raise

    def _delivery_callback(self, err, msg):
        """Callback called when message is delivered or fails"""
        if err:
            logger.error(f"Message delivery failed: {err}")
        else:
            # logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}]")
            pass

    def create_topics_if_not_exist(self, topics: Optional[List[str]] = None):
        """Create Kafka topics if they don't exist"""
        if topics is None:
            topics = [
                "raw-news-feed",
                "news-english",
                "news-hindi",
                "news-bengali",
                "dlq-ingestion",  # NEW
                "dlq-processing",  # NEW
            ]

        admin_client = AdminClient({"bootstrap.servers": self.bootstrap_servers})

        try:
            # Check existing topics
            cluster_metadata = admin_client.list_topics(timeout=10)
            existing_topics = cluster_metadata.topics

            new_topics = []
            for topic in topics:
                if topic not in existing_topics:
                    # Create topic with default settings
                    new_topics.append(
                        NewTopic(topic, num_partitions=3, replication_factor=1)
                    )

            if new_topics:
                fs = admin_client.create_topics(new_topics)

                # Wait for each operation to finish
                for topic, f in fs.items():
                    try:
                        f.result()  # The result itself is None
                        logger.info(f"Topic '{topic}' created")
                    except Exception as e:
                        logger.error(f"Failed to create topic '{topic}': {e}")
            else:
                logger.info("All topics already exist")

        except Exception as e:
            logger.error(f"Error managing topics: {e}")

    def produce_news_item(self, topic: str, news_item: NewsItem):
        """Produce a single news item to a topic"""
        try:
            # Serialize
            key = news_item.id
            value = news_item.to_json()

            self.producer.produce(
                topic=topic,
                key=key.encode("utf-8"),
                value=value.encode("utf-8"),
                callback=self._delivery_callback,
            )

            # Trigger poll to serve delivery callbacks
            self.producer.poll(0)
            return True

        except Exception as e:
            logger.error(f"Failed to produce message: {e}")
            return False

    def produce_dlq_event(self, topic: str, event: Any):
        """Produce a DLQ event (accepts DLQEvent object)"""
        try:
            # Serialize
            key = event.event_id
            value = event.to_json()

            self.producer.produce(
                topic=topic,
                key=key.encode("utf-8"),
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
        """
        Produce a list of news items to the raw-news-feed topic.
        Returns statistics about the operation.
        """
        stats = {}

        # Group by category (though we currently send all to raw-news-feed)
        # We keep the structure for stats reporting

        for item in news_items:
            category = item.category
            if category not in stats:
                stats[category] = {"total": 0, "delivered": 0, "failed": 0}

            stats[category]["total"] += 1

            # Send to raw processing topic
            success = self.produce_news_item("raw-news-feed", item)

            if success:
                stats[category]["delivered"] += 1
            else:
                stats[category]["failed"] += 1

        # Calculate rates
        for cat in stats:
            total = stats[cat]["total"]
            if total > 0:
                stats[cat]["success_rate"] = (stats[cat]["delivered"] / total) * 100
            else:
                stats[cat]["success_rate"] = 0

        # Flush to ensure all messages are sent
        self.producer.flush()

        return stats

    def get_stats(self):
        """Get producer statistics (simplified)"""
        return {"queue_depth": len(self.producer)}

    def health_check(self) -> Dict:
        """Check connection to Kafka"""
        try:
            admin_client = AdminClient({"bootstrap.servers": self.bootstrap_servers})
            metadata = admin_client.list_topics(timeout=5)
            broker_count = len(metadata.brokers)
            return {
                "connected": broker_count > 0,
                "brokers": broker_count,
                "topics": len(metadata.topics),
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}

    def close(self):
        """Flush and close producer"""
        self.producer.flush()
