import logging
from typing import Dict, List, Optional, Union
from datetime import datetime

from services.kafka_consumer import NewsKafkaConsumer
from services.kafka_producer import NewsKafkaProducer
from services.translation_service import TranslationService
from services.tts_service import TTSService
from services.language_manager import get_language_manager
from models.news_item import NewsItem, ProcessedNewsItem
from models.dlq_event import DLQEvent
from config.config import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NewsProcessingConsumer:
    def __init__(
        self,
        kafka_config: Union[str, Dict] = "localhost:9093",
        translation_provider: str = "mock",
        tts_provider: str = "mock",
        translation_api_key: Optional[str] = None,
        tts_api_key: Optional[str] = None,
        output_dir: str = "audio_output",
    ):
        logger.info("INITIALIZING NEWS PROCESSING CONSUMER")
        
        self.language_manager = get_language_manager()

        # Initialize Consumer with full config (SASL enabled)
        self.consumer = NewsKafkaConsumer(
            bootstrap_servers=kafka_config,
            group_id="news-processing-group",
            auto_offset_reset="earliest",
        )
        self.consumer.subscribe(["raw-news-feed"])

        # Initialize Producer with full config
        self.producer = NewsKafkaProducer(bootstrap_servers=kafka_config)

        self.translation_service = TranslationService(
            provider=translation_provider,
            api_key=translation_api_key,
            model="gemini-2.5-flash",
        )

        self.tts_service = TTSService(
            provider=tts_provider, 
            api_key=tts_api_key, 
            output_dir=output_dir
        )

        self.stats = {
            "messages_processed": 0,
            "messages_failed": 0,
            "dlq_events_sent": 0,
            "by_language": {
                lang: 0 for lang in self.language_manager.get_language_list()
            },
        }

        logger.info("✓ Processing Consumer initialized")
        logger.info("=" * 80 + "\n")

    def process_news_item(self, news_item: NewsItem) -> List[ProcessedNewsItem]:
        processed_items = []
        languages_config = self.language_manager.get_config()

        logger.info(f"\n{'=' * 60}")
        logger.info(f"Processing: {news_item.title[:60]}...")
        logger.info(f"Source: {news_item.source} | Category: {news_item.category}")
        logger.info(f"{'=' * 60}")

        text_to_process = news_item.content or news_item.description

        logger.info(f"Processing: {news_item.title[:40]}... (Langs: {list(languages_config.keys())})")

        for lang_code, config in languages_config.items():
            if not config.get("enabled", True):
                continue
            logger.info(f"\n[{lang_code.upper()}] Processing...")

            # Step 1: Translate and summarize
            try:
                # 1. Translate
                result = self.translation_service.translate_and_summarize(
                    text=text_to_process, target_language=lang_code, max_length=200
                )
            except Exception as e:
                logger.error(f"  ✗ [{lang_code.upper()}] Translation failed: {e}")
                dlq_event = DLQEvent(
                    original_id=news_item.id,
                    source=news_item.source,
                    stage=f"translation_{lang_code}",
                    error_message=str(e),
                    payload={
                        "language": lang_code,
                        "news_item": news_item.to_dict(),
                    },
                )
                self.producer.produce_dlq_event("dlq-processing", dlq_event)
                self.stats["messages_failed"] += 1
                self.stats["dlq_events_sent"] += 1
                continue

            translated_summary = result["translated_summary"]

            # Step 2: Generate audio
            try:
                voice_id = config.get("voice_id")
                audio_filename = f"news_{news_item.id}_{lang_code}.mp3"
                audio_path = self.tts_service.save_speech(
                    text=translated_summary,
                    language=lang_code,
                    filename=audio_filename,
                    voice_id=voice_id,
                )
            except Exception as e:
                logger.error(f"  ✗ [{lang_code.upper()}] TTS failed: {e}")
                dlq_event = DLQEvent(
                    original_id=news_item.id,
                    source=news_item.source,
                    stage=f"tts_{lang_code}",
                    error_message=str(e),
                    payload={
                        "language": lang_code,
                        "news_item": news_item.to_dict(),
                        "translated_summary": translated_summary,
                    },
                )
                self.producer.produce_dlq_event("dlq-processing", dlq_event)
                self.stats["messages_failed"] += 1
                self.stats["dlq_events_sent"] += 1
                continue

            # Calculate duration
            word_count = len(translated_summary.split())
            estimated_duration = (word_count / 150) * 60

            processed_item = ProcessedNewsItem(
                original_id=news_item.id,
                original_title=news_item.title,
                original_url=news_item.url,
                category=news_item.category,
                source=news_item.source,
                published_date=news_item.published_date.isoformat(),
                language=lang_code,
                summary=result["summary"],
                translated_summary=translated_summary,
                audio_file=audio_path,
                audio_duration=round(estimated_duration, 2),
                processed_at=datetime.now().isoformat(),
                processing_provider=self.translation_service.provider_name,
                tts_provider=self.tts_service.provider_name,
            )

            processed_items.append(processed_item)
            self.stats["by_language"][lang_code] += 1
            logger.info(f"  ✓ [{lang_code.upper()}] Processing complete")

        return processed_items

    def produce_processed_items(self, processed_items: List[ProcessedNewsItem]):
        for item in processed_items:
            lang_config = self.language_manager.get_config().get(item.language, {})
            lang_name = lang_config.get("name", item.language).lower()
            topic = f"news-{lang_name}"
            
            try:
                self.producer.producer.produce(
                    topic=topic,
                    key=item.original_id.encode("utf-8"),
                    value=item.to_json().encode("utf-8"),
                    callback=self.producer._delivery_callback,
                )
            except Exception as e:
                logger.error(f"Produce failed for {item.language}: {e}")

    def run_continuous(self, batch_size: int = 5):
        """Run continuous processing loop"""
        logger.info("\n" + "=" * 80)
        logger.info("STARTING CONTINUOUS PROCESSING")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 80 + "\n")

        try:
            while self.consumer.running:
                logger.info("Waiting for messages from raw-news-feed...")
                news_item = self.consumer.consume_message(timeout=5.0)

                if news_item is None:
                    continue

                self.stats["messages_processed"] += 1

                # Process the news item (internally handles DLQ for individual languages)
                processed_items = self.process_news_item(news_item)

                if processed_items:
                    self.produce_processed_items(processed_items)
                    self.producer.producer.poll(0)

                # IMPORTANT: We commit the offset even if some languages failed,
                # because the failures are safely in the DLQ. We don't want to get stuck.

        except KeyboardInterrupt:
            logger.info("\n\nShutting down processing consumer...")
        finally:
            self.shutdown()

    def process_batch(self, max_messages: int = 10):
        """Process a batch of messages then exit"""
        logger.info(f"BATCH PROCESSING: {max_messages} messages")
        processed_count = 0

        for i in range(max_messages):
            news_item = self.consumer.consume_message(timeout=10.0)
            if news_item is None:
                break

            self.stats["messages_processed"] += 1
            processed_count += 1
            processed_items = self.process_news_item(news_item)

            if processed_items:
                self.produce_processed_items(processed_items)
                self.producer.producer.poll(0)

        self.producer.producer.flush(timeout=10)
        return processed_count

    def get_stats(self) -> Dict:
        return {
            "messages_processed": self.stats["messages_processed"],
            "messages_failed": self.stats["messages_failed"],
            "dlq_events": self.stats["dlq_events_sent"],
            "by_language": self.stats["by_language"],
            "translation_service": self.translation_service.get_stats(),
            "tts_service": self.tts_service.get_stats(),
        }

    def shutdown(self):
        logger.info("Flushing Kafka producer...")
        self.producer.close()
        logger.info("Closing Kafka consumer...")
        self.consumer.close()
        logger.info("✓ Processing consumer shutdown complete")


def main():
    import argparse
    config = get_config()

    parser = argparse.ArgumentParser(description="News Processing Consumer")
    parser.add_argument("--mode", choices=["batch", "continuous"], default="batch")
    parser.add_argument("--max", type=int, default=5)
    parser.add_argument("--kafka", default=config.kafka.bootstrap_servers)
    parser.add_argument(
        "--translation-provider", default=config.api.translation_provider
    )
    parser.add_argument("--tts-provider", default=config.api.tts_provider)
    args = parser.parse_args()

    # Determine correct Kafka config (String vs Dict)
    kafka_config = args.kafka
    if args.kafka == config.kafka.bootstrap_servers:
        kafka_config = config.kafka.connection_config

    consumer = NewsProcessingConsumer(
        kafka_config=kafka_config,
        translation_provider=args.translation_provider,
        tts_provider=args.tts_provider,
        translation_api_key=config.api.gemini_api_key,
        tts_api_key=config.api.elevenlabs_api_key,
        output_dir=config.app.audio_output_dir,
    )

    if args.mode == "batch":
        consumer.process_batch(max_messages=args.max)
    else:
        consumer.run_continuous()

if __name__ == "__main__":
    main()