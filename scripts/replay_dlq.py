"""
Script to replay messages from Dead Letter Queues (DLQ)
back to the main processing pipeline.
"""
import sys
import os
import json
import logging
import argparse

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.kafka_consumer import NewsKafkaConsumer
from services.kafka_producer import NewsKafkaProducer
from models.dlq_event import DLQEvent
from models.news_item import NewsItem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DLQ-Replay")

def replay_messages(
    source_topic: str,
    target_topic: str,
    bootstrap_servers: str,
    max_messages: int = 10,
    dry_run: bool = False
):
    logger.info(f"Starting DLQ Replay: {source_topic} -> {target_topic}")
    logger.info(f"Max messages: {max_messages} | Dry run: {dry_run}")

    # Consumer for DLQ
    consumer = NewsKafkaConsumer(
        bootstrap_servers=bootstrap_servers,
        group_id="dlq-replay-group",
        auto_offset_reset="earliest",
        return_raw=True # We need the raw DLQEvent JSON
    )
    consumer.subscribe([source_topic])

    # Producer for Target
    producer = NewsKafkaProducer(bootstrap_servers=bootstrap_servers)

    replayed_count = 0

    try:
        while replayed_count < max_messages:
            msg = consumer.consumer.poll(1.0)
            
            if msg is None:
                logger.info("No more messages in DLQ.")
                break
            
            if msg.error():
                logger.error(f"Consumer error: {msg.error()}")
                continue

            # Parse DLQ Event
            try:
                value = msg.value().decode('utf-8')
                event_data = json.loads(value)
                dlq_event = DLQEvent.from_dict(event_data)
                
                logger.info(f"Read DLQ Event: {dlq_event.event_id} (Error: {dlq_event.error_message})")
                
                # Check if payload contains a valid NewsItem
                payload = dlq_event.payload or {}

                # Reconstruct NewsItem depending on what's in payload
                # We now nest the serialized NewsItem under 'news_item'
                news_payload = payload.get('news_item', payload)

                if isinstance(news_payload, dict) and 'url' in news_payload:
                    try:
                        # Prefer from_dict to restore datetimes
                        if 'published_date' in news_payload and 'fetched_at' in news_payload:
                            news_item = NewsItem.from_dict(news_payload)
                        else:
                            news_item = NewsItem(**news_payload)

                        if not dry_run:
                            producer.produce_news_item(news_item, topic=target_topic)
                            logger.info(f"-> Replayed item {news_item.id} to {target_topic}")
                        else:
                            logger.info(f"-> [DRY RUN] Would replay item {news_item.id}")

                        replayed_count += 1
                    except Exception as e:
                        logger.warning(
                            f"Skipping event {dlq_event.event_id}: cannot rebuild NewsItem ({e})"
                        )
                else:
                    logger.warning(
                        f"Skipping event {dlq_event.event_id}: Payload is not a valid NewsItem structure"
                    )

            except Exception as e:
                logger.error(f"Failed to process DLQ message: {e}")
                continue

        producer.producer.flush()
        logger.info(f"Replay complete. Processed {replayed_count} messages.")

    finally:
        consumer.close()
        producer.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Replay DLQ Messages')
    parser.add_argument('--topic', choices=['ingestion', 'processing'], required=True, help='Which DLQ to replay')
    parser.add_argument('--max', type=int, default=10, help='Max messages to replay')
    parser.add_argument('--dry-run', action='store_true', help='Preview without sending')
    parser.add_argument('--kafka', default='localhost:9093', help='Kafka servers')

    args = parser.parse_args()

    # Map easy names to actual topics
    TOPIC_MAP = {
        'ingestion': ('dlq-ingestion', 'raw-news-feed'),
        'processing': ('dlq-processing', 'raw-news-feed') 
    }
    
    source, target = TOPIC_MAP[args.topic]
    
    replay_messages(
        source_topic=source,
        target_topic=target,
        bootstrap_servers=args.kafka,
        max_messages=args.max,
        dry_run=args.dry_run
    )