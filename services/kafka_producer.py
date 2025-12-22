from confluent_kafka import Producer, KafkaException
from confluent_kafka.admin import AdminClient, NewTopic
import logging
from typing import List, Dict, Any, Optional
from models.news_item import NewsItem
import socket

logger = logging.getLogger(__name__)


class NewsKafkaProducer:
    """
    Produces news items to Kafka topics
    Handles topic creation and message delivery
    """
    
    def __init__(
        self,
        bootstrap_servers: str = "localhost:9093",
        client_id: str = "news-producer"
    ):
        """
        Initialize Kafka producer
        
        Args:
            bootstrap_servers: Kafka broker addresses
            client_id: Client identifier
        """
        self.bootstrap_servers = bootstrap_servers
        self.client_id = client_id
        
        # Producer configuration
        self.config = {
            'bootstrap.servers': bootstrap_servers,
            'client.id': f"{client_id}-{socket.gethostname()}",
            'acks': 'all',  # Wait for all replicas to acknowledge
            'retries': 3,
            'retry.backoff.ms': 1000,
            'compression.type': 'gzip',  # Compress messages
            'linger.ms': 100,  # Batch messages for efficiency
            'batch.size': 32768,  # 32KB batch size
        }
        
        # Initialize producer
        try:
            self.producer = Producer(self.config)
            logger.info(f"✓ Kafka Producer initialized: {bootstrap_servers}")
        except KafkaException as e:
            logger.error(f"Failed to initialize Kafka Producer: {e}")
            raise
        
        # Initialize admin client for topic management
        self.admin_client = AdminClient({'bootstrap.servers': bootstrap_servers})
        
        # Topic names
        self.topics = {
            'raw': 'raw-news-feed',
            'english': 'news-english',
            'hindi': 'news-hindi',
            'bengali': 'news-bengali'
        }
        
        # Delivery statistics
        self.stats = {
            'delivered': 0,
            'failed': 0
        }
    
    def create_topics_if_not_exist(self, num_partitions: int = 3, replication_factor: int = 1):
        """
        Create Kafka topics if they don't exist
        
        Args:
            num_partitions: Number of partitions per topic
            replication_factor: Replication factor (1 for single broker)
        """
        existing_topics = self.admin_client.list_topics(timeout=10).topics
        
        topics_to_create = []
        for topic_name in self.topics.values():
            if topic_name not in existing_topics:
                topics_to_create.append(
                    NewTopic(
                        topic=topic_name,
                        num_partitions=num_partitions,
                        replication_factor=replication_factor
                    )
                )
        
        if topics_to_create:
            logger.info(f"Creating {len(topics_to_create)} topics...")
            fs = self.admin_client.create_topics(topics_to_create)
            
            for topic, f in fs.items():
                try:
                    f.result()  # Wait for topic creation
                    logger.info(f"✓ Created topic: {topic}")
                except Exception as e:
                    logger.error(f"Failed to create topic {topic}: {e}")
        else:
            logger.info("✓ All topics already exist")
    
    def _delivery_callback(self, err, msg):
        """
        Callback for message delivery confirmation
        """
        if err:
            logger.error(f"Message delivery failed: {err}")
            self.stats['failed'] += 1
        else:
            logger.debug(
                f"Message delivered to {msg.topic()} "
                f"[partition {msg.partition()}] at offset {msg.offset()}"
            )
            self.stats['delivered'] += 1
    
    def produce_news_item(
        self,
        news_item: NewsItem,
        topic: Optional[str] = None,
        key: Optional[str] = None
    ) -> bool:
        """
        Produce a single news item to Kafka
        
        Args:
            news_item: NewsItem to send
            topic: Topic name (defaults to 'raw-news-feed')
            key: Message key for partitioning
            
        Returns:
            True if successfully queued, False otherwise
        """
        if topic is None:
            topic = self.topics['raw']
        
        try:
            # Serialize news item to JSON
            message_value = news_item.to_json()
            
            # Use article ID as key for consistent partitioning
            message_key = key or news_item.id
            
            # Produce message
            self.producer.produce(
                topic=topic,
                key=message_key.encode('utf-8'),
                value=message_value.encode('utf-8'),
                callback=self._delivery_callback
            )
            
            # Trigger callbacks (non-blocking)
            self.producer.poll(0)
            
            return True
            
        except BufferError:
            logger.warning("Local queue full, waiting...")
            self.producer.flush()
            return self.produce_news_item(news_item, topic, key)
            
        except Exception as e:
            logger.error(f"Failed to produce message: {e}")
            self.stats['failed'] += 1
            return False
    
    def produce_batch(
        self,
        news_items: List[NewsItem],
        topic: str = None
    ) -> Dict[str, Any]:
        """
        Produce multiple news items in batch
        
        Args:
            news_items: List of NewsItem objects
            topic: Target topic (defaults to 'raw-news-feed')
            
        Returns:
            Dictionary with success/failure counts
        """
        if topic is None:
            topic = self.topics['raw']
        
        logger.info(f"Producing {len(news_items)} messages to topic '{topic}'...")
        
        # Reset stats
        initial_delivered = self.stats['delivered']
        initial_failed = self.stats['failed']
        
        # Produce all messages
        for news_item in news_items:
            self.produce_news_item(news_item, topic)
        
        # Wait for all messages to be delivered
        remaining = self.producer.flush(timeout=30)
        
        if remaining > 0:
            logger.warning(f"{remaining} messages were not delivered")
        
        # Calculate batch results
        delivered = self.stats['delivered'] - initial_delivered
        failed = self.stats['failed'] - initial_failed
        
        logger.info(
            f"✓ Batch complete: {delivered} delivered, {failed} failed"
        )
        
        return {
            'total': len(news_items),
            'delivered': delivered,
            'failed': failed,
            'success_rate': (delivered / len(news_items) * 100) if news_items else 0
        }
    
    def produce_by_category(
        self,
        news_items: List[NewsItem]
    ) -> Dict[str, Dict[str, int]]:
        """
        Produce news items grouped by category to raw topic
        
        Args:
            news_items: List of NewsItem objects
            
        Returns:
            Dictionary with results per category
        """
        # Group by category
        by_category = {}
        for item in news_items:
            if item.category not in by_category:
                by_category[item.category] = []
            by_category[item.category].append(item)
        
        results = {}
        
        # Produce each category
        for category, items in by_category.items():
            logger.info(f"Producing {len(items)} {category} articles...")
            result = self.produce_batch(items, self.topics['raw'])
            results[category] = result
        
        return results
    
    def get_stats(self) -> Dict:
        """Get producer statistics"""
        return {
            'total_delivered': self.stats['delivered'],
            'total_failed': self.stats['failed'],
            'success_rate': (
                self.stats['delivered'] / 
                (self.stats['delivered'] + self.stats['failed']) * 100
                if (self.stats['delivered'] + self.stats['failed']) > 0
                else 0
            )
        }
    
    def health_check(self) -> Dict:
        """
        Check Kafka connection health
        
        Returns:
            Health status dictionary
        """
        try:
            metadata = self.admin_client.list_topics(timeout=5)
            
            return {
                'status': 'healthy',
                'connected': True,
                'broker_count': len(metadata.brokers),
                'topic_count': len(metadata.topics),
                'topics': list(metadata.topics.keys())
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'connected': False,
                'error': str(e)
            }
    
    def close(self):
        """Close producer and flush remaining messages"""
        logger.info("Closing Kafka producer...")
        remaining = self.producer.flush(timeout=10)
        if remaining > 0:
            logger.warning(f"{remaining} messages were not delivered before close")
        logger.info("✓ Producer closed")


# Example usage
if __name__ == "__main__":
    from datetime import datetime, timezone
    
    # Initialize producer
    producer = NewsKafkaProducer(bootstrap_servers="localhost:9093")
    
    # Health check
    health = producer.health_check()
    print(f"Kafka Health: {health}")
    
    # Create topics
    producer.create_topics_if_not_exist()
    
    # Create sample news item
    sample_news = NewsItem(
        title="Test Article: Kafka Integration Working",
        description="This is a test article to verify Kafka integration",
        url="https://example.com/test",
        category="technology",
        source="Test Source",
        published_date=datetime.now(timezone.utc),
        fetched_at=datetime.now(timezone.utc),
        content="Full content of the test article goes here..."
    )
    
    # Produce single message
    print("\nProducing single message...")
    success = producer.produce_news_item(sample_news)
    print(f"Message queued: {success}")
    
    # Get stats
    stats = producer.get_stats()
    print(f"\nProducer Stats: {stats}")
    
    # Close
    producer.close()