from confluent_kafka import Consumer, KafkaException, KafkaError
import json
import logging
from typing import Optional, Callable, List
from models.news_item import NewsItem
import signal

logger = logging.getLogger(__name__)


class NewsKafkaConsumer:
    """
    Consumes news items from Kafka topics
    Used for testing and monitoring news flow
    """

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9093",
        group_id: str = "news-consumer-group",
        auto_offset_reset: str = "earliest",
        manage_signals: bool = True,
        return_raw: bool = False,
    ):
        """
        Initialize Kafka consumer

        Args:
            bootstrap_servers: Kafka broker addresses
            group_id: Consumer group ID
            auto_offset_reset: Where to start consuming ('earliest' or 'latest')
        """
        self.bootstrap_servers = bootstrap_servers
        self.return_raw = return_raw
        self.group_id = group_id
        self.running = True

        # Consumer configuration
        self.config = {
            "bootstrap.servers": bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": auto_offset_reset,
            "enable.auto.commit": True,
            "auto.commit.interval.ms": 5000,
            "session.timeout.ms": 6000,
            "max.poll.interval.ms": 300000,
        }

        # Initialize consumer
        try:
            self.consumer = Consumer(self.config)
            logger.info(f"✓ Kafka Consumer initialized: {bootstrap_servers}")
        except KafkaException as e:
            logger.error(f"Failed to initialize Kafka Consumer: {e}")
            raise

        # Statistics
        self.stats = {"messages_consumed": 0, "errors": 0}

        # Setup graceful shutdown
        if manage_signals:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info("Shutdown signal received")
        self.running = False

    def subscribe(self, topics: List[str]):
        """
        Subscribe to topics

        Args:
            topics: List of topic names to subscribe to
        """
        try:
            self.consumer.subscribe(topics)
            logger.info(f"✓ Subscribed to topics: {topics}")
        except KafkaException as e:
            logger.error(f"Failed to subscribe to topics: {e}")
            raise

    def consume_message(self, timeout: float = 1.0) -> Optional[NewsItem]:
        """
        Consume a single message

        Args:
            timeout: Timeout in seconds

        Returns:
            NewsItem if message received, None otherwise
        """
        try:
            msg = self.consumer.poll(timeout=timeout)

            if msg is None:
                return None

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    # End of partition, not an error
                    logger.debug(f"Reached end of partition {msg.partition()}")
                else:
                    logger.error(f"Consumer error: {msg.error()}")
                    self.stats["errors"] += 1
                return None

            # Parse message
            value = msg.value().decode("utf-8")
            news_data = json.loads(value)

            if self.return_raw:
                self.stats['messages_consumed'] += 1
                return news_data

            news_item = NewsItem.from_dict(news_data)

            self.stats["messages_consumed"] += 1

            logger.debug(
                f"Consumed: {news_item.title[:50]}... "
                f"from {msg.topic()} [partition {msg.partition()}]"
            )

            return news_item

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message: {e}")
            self.stats["errors"] += 1
            return None
        except Exception as e:
            logger.error(f"Error consuming message: {e}")
            self.stats["errors"] += 1
            return None

    def consume_batch(
        self, max_messages: int = 100, timeout: float = 5.0
    ) -> List[NewsItem]:
        """
        Consume multiple messages

        Args:
            max_messages: Maximum number of messages to consume
            timeout: Total timeout in seconds

        Returns:
            List of NewsItem objects
        """
        messages = []

        logger.info(f"Consuming up to {max_messages} messages...")

        for _ in range(max_messages):
            if not self.running:
                break

            news_item = self.consume_message(timeout=timeout / max_messages)
            if news_item:
                messages.append(news_item)
            else:
                # No more messages available
                break

        logger.info(f"✓ Consumed {len(messages)} messages")
        return messages

    def consume_continuous(
        self, callback: Callable[[NewsItem], None], max_messages: Optional[int] = None
    ):
        """
        Consume messages continuously with callback

        Args:
            callback: Function to call for each message
            max_messages: Stop after consuming this many (None = infinite)
        """
        logger.info("Starting continuous consumption...")
        consumed = 0

        try:
            while self.running:
                if max_messages and consumed >= max_messages:
                    logger.info(f"Reached max messages limit: {max_messages}")
                    break

                news_item = self.consume_message(timeout=1.0)

                if news_item:
                    try:
                        callback(news_item)
                        consumed += 1
                    except Exception as e:
                        logger.error(f"Error in callback: {e}")

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            logger.info(f"✓ Consumed {consumed} messages total")

    def get_stats(self) -> dict:
        """Get consumer statistics"""
        return {
            "messages_consumed": self.stats["messages_consumed"],
            "errors": self.stats["errors"],
        }

    def seek_to_beginning(self, topic: str, partition: int = 0):
        """Seek to beginning of topic partition"""
        from confluent_kafka import TopicPartition

        tp = TopicPartition(topic, partition, 0)
        self.consumer.seek(tp)
        logger.info(f"Seeked to beginning of {topic} partition {partition}")

    def close(self):
        """Close consumer"""
        logger.info("Closing Kafka consumer...")
        self.consumer.close()
        logger.info("✓ Consumer closed")


def print_news_item(news_item: NewsItem):
    """Pretty print news item (callback example)"""
    print("\n" + "=" * 80)
    print(f"📰 {news_item.source} - {news_item.category.upper()}")
    print(f"Title: {news_item.title}")
    print(f"URL: {news_item.url}")
    print(f"Published: {news_item.published_date}")
    print(
        f"Content: {news_item.content[:200] if news_item.content else news_item.content}..."
    )
    print("=" * 80)


# Example usage
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Kafka News Consumer")
    parser.add_argument(
        "--topic", default="raw-news-feed", help="Topic to consume from"
    )
    parser.add_argument(
        "--max", type=int, default=None, help="Maximum messages to consume"
    )
    parser.add_argument(
        "--continuous", action="store_true", help="Consume continuously"
    )

    args = parser.parse_args()

    # Initialize consumer
    consumer = NewsKafkaConsumer(
        bootstrap_servers="localhost:9093", group_id="test-consumer"
    )

    # Subscribe to topic
    consumer.subscribe([args.topic])

    print(f"\n🔍 Consuming from topic: {args.topic}")
    print("Press Ctrl+C to stop\n")

    try:
        if args.continuous:
            # Continuous consumption with callback
            consumer.consume_continuous(print_news_item, max_messages=args.max)
        else:
            # Batch consumption
            messages = consumer.consume_batch(max_messages=args.max or 10, timeout=5.0)

            # Print messages
            for msg in messages:
                print_news_item(msg)

            # Print stats
            stats = consumer.get_stats()
            print(f"\n📊 Stats: {stats}")

    finally:
        consumer.close()
