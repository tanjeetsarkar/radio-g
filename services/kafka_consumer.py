from confluent_kafka import Consumer, KafkaException, KafkaError
import json
import logging
from typing import Optional, Callable, List, Union, Dict
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
        bootstrap_servers: Union[str, Dict] = "localhost:9093",
        group_id: str = "news-consumer-group",
        auto_offset_reset: str = "earliest",
        manage_signals: bool = True,
        return_raw: bool = False,
    ):
        self.return_raw = return_raw
        self.group_id = group_id
        self.running = True

        # Handle configuration: if dict, use it; if str, wrap it
        if isinstance(bootstrap_servers, dict):
            self.config = bootstrap_servers.copy()
            self.bootstrap_servers = self.config.get("bootstrap.servers", "unknown")
        else:
            self.bootstrap_servers = bootstrap_servers
            self.config = {"bootstrap.servers": bootstrap_servers}

        # Add consumer-specific config
        self.config.update(
            {
                "group.id": group_id,
                "auto.offset.reset": auto_offset_reset,
                "enable.auto.commit": True,
                "auto.commit.interval.ms": 5000,
                "session.timeout.ms": 6000,
                "max.poll.interval.ms": 300000,
            }
        )

        # Initialize consumer
        try:
            # Log config (masking password)
            log_config = self.config.copy()
            if "sasl.password" in log_config:
                log_config["sasl.password"] = "***"

            logger.info(f"✓ Kafka Consumer initialized with config: {log_config}")
            self.consumer = Consumer(self.config)
        except KafkaException as e:
            logger.error(f"Failed to initialize Kafka Consumer: {e}")
            raise

        self.stats = {"messages_consumed": 0, "errors": 0}

        if manage_signals:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        logger.info("Shutdown signal received")
        self.running = False

    def subscribe(self, topics: List[str]):
        try:
            self.consumer.subscribe(topics)
            logger.info(f"✓ Subscribed to topics: {topics}")
        except KafkaException as e:
            logger.error(f"Failed to subscribe to topics: {e}")
            raise

    def consume_message(self, timeout: float = 1.0) -> Optional[NewsItem]:
        try:
            msg = self.consumer.poll(timeout=timeout)

            if msg is None:
                return None

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    logger.debug(f"Reached end of partition {msg.partition()}")
                else:
                    logger.error(f"Consumer error: {msg.error()}")
                    self.stats["errors"] += 1
                return None

            value = msg.value().decode("utf-8")
            news_data = json.loads(value)

            if self.return_raw:
                self.stats["messages_consumed"] += 1
                return news_data

            news_item = NewsItem.from_dict(news_data)
            self.stats["messages_consumed"] += 1

            logger.debug(f"Consumed: {news_item.title[:50]}...")
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
        messages = []
        logger.info(f"Consuming up to {max_messages} messages...")
        for _ in range(max_messages):
            if not self.running:
                break
            news_item = self.consume_message(timeout=timeout / max_messages)
            if news_item:
                messages.append(news_item)
            else:
                break
        logger.info(f"✓ Consumed {len(messages)} messages")
        return messages

    def consume_continuous(
        self, callback: Callable[[NewsItem], None], max_messages: Optional[int] = None
    ):
        logger.info("Starting continuous consumption...")
        consumed = 0
        try:
            while self.running:
                if max_messages and consumed >= max_messages:
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
        return {
            "messages_consumed": self.stats["messages_consumed"],
            "errors": self.stats["errors"],
        }

    def close(self):
        logger.info("Closing Kafka consumer...")
        self.consumer.close()
        logger.info("✓ Consumer closed")
