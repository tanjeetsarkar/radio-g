
import logging
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from services.kafka_consumer import NewsKafkaConsumer
from services.kafka_producer import NewsKafkaProducer
from services.translation_service import TranslationService
from services.tts_service import TTSService
from models.news_item import NewsItem
from config.config import get_config


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ProcessedNewsItem:
    """Processed news item with translations and audio"""
    
    # Original data
    original_id: str
    original_title: str
    original_url: str
    category: str
    source: str
    published_date: str
    
    # Processed data
    language: str
    summary: str
    translated_summary: str
    audio_file: str
    audio_duration: float
    
    # Metadata
    processed_at: str
    processing_provider: str
    tts_provider: str
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(asdict(self))
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ProcessedNewsItem':
        """Create from dictionary"""
        return cls(**data)


class NewsProcessingConsumer:
    """
    Consumes raw news, processes it (translate + TTS), and produces to language topics
    """
    
    def __init__(
        self,
        kafka_bootstrap_servers: str = "localhost:9093",
        translation_provider: str = "mock",
        tts_provider: str = "mock",
        translation_api_key: Optional[str] = None,
        tts_api_key: Optional[str] = None,
        target_languages: Optional[List[str]] = None,
        output_dir: str = "audio_output"
    ):
        """
        Initialize processing consumer
        
        Args:
            kafka_bootstrap_servers: Kafka servers
            translation_provider: 'mock' or 'gemini'
            tts_provider: 'mock' or 'elevenlabs'
            translation_api_key: API key for translation
            tts_api_key: API key for TTS
            target_languages: List of language codes (default: ['en', 'hi', 'bn'])
            output_dir: Directory for audio files
        """
        logger.info("="*80)
        logger.info("INITIALIZING NEWS PROCESSING CONSUMER")
        logger.info("="*80)
        
        # Default languages
        self.target_languages = target_languages or ['en', 'hi', 'bn']
        
        # Initialize Kafka consumer
        logger.info("Initializing Kafka Consumer...")
        self.consumer = NewsKafkaConsumer(
            bootstrap_servers=kafka_bootstrap_servers,
            group_id="news-processing-group",
            auto_offset_reset="earliest"
        )
        self.consumer.subscribe(['raw-news-feed'])
        
        # Initialize Kafka producer
        logger.info("Initializing Kafka Producer...")
        self.producer = NewsKafkaProducer(bootstrap_servers=kafka_bootstrap_servers)
        
        # Initialize translation service
        logger.info(f"Initializing Translation Service ({translation_provider})...")
        self.translation_service = TranslationService(
            provider=translation_provider,
            api_key=translation_api_key,
            model="gemini-2.5-flash"
        )
        
        # Initialize TTS service
        logger.info(f"Initializing TTS Service ({tts_provider})...")
        self.tts_service = TTSService(
            provider=tts_provider,
            api_key=tts_api_key,
            output_dir=output_dir
        )
        
        # Statistics
        self.stats = {
            'messages_processed': 0,
            'messages_failed': 0,
            'by_language': {lang: 0 for lang in self.target_languages}
        }
        
        logger.info("✓ Processing Consumer initialized")
        logger.info(f"  Target languages: {', '.join(self.target_languages)}")
        logger.info("="*80 + "\n")
    
    def process_news_item(self, news_item: NewsItem) -> List[ProcessedNewsItem]:
        """
        Process a single news item for all target languages
        
        Args:
            news_item: Original news item
            
        Returns:
            List of processed items (one per language)
        """
        processed_items = []
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {news_item.title[:60]}...")
        logger.info(f"Source: {news_item.source} | Category: {news_item.category}")
        logger.info(f"{'='*60}")
        
        # Use content or description
        text_to_process = news_item.content or news_item.description
        
        for language in self.target_languages:
            try:
                logger.info(f"\n[{language.upper()}] Processing...")
                
                # Step 1: Translate and summarize
                logger.info(f"  → Translating and summarizing...")
                result = self.translation_service.translate_and_summarize(
                    text=text_to_process,
                    target_language=language,
                    max_length=200  # ~30-60 seconds when spoken
                )
                
                translated_summary = result['translated_summary']
                logger.info(f"  ✓ Summary ({len(translated_summary)} chars)")
                
                # Step 2: Generate audio
                logger.info(f"  → Generating audio...")
                audio_filename = f"news_{news_item.id}_{language}.mp3"
                audio_path = self.tts_service.save_speech(
                    text=translated_summary,
                    language=language,
                    filename=audio_filename
                )
                logger.info(f"  ✓ Audio saved: {audio_path}")
                
                # Calculate duration (rough estimate: 150 words/min)
                word_count = len(translated_summary.split())
                estimated_duration = (word_count / 150) * 60
                
                # Create processed item
                processed_item = ProcessedNewsItem(
                    original_id=news_item.id,
                    original_title=news_item.title,
                    original_url=news_item.url,
                    category=news_item.category,
                    source=news_item.source,
                    published_date=news_item.published_date.isoformat(),
                    language=language,
                    summary=result['summary'],
                    translated_summary=translated_summary,
                    audio_file=audio_path,
                    audio_duration=round(estimated_duration, 2),
                    processed_at=datetime.now().isoformat(),
                    processing_provider=self.translation_service.provider_name,
                    tts_provider=self.tts_service.provider_name
                )
                
                processed_items.append(processed_item)
                self.stats['by_language'][language] += 1
                
                logger.info(f"  ✓ [{language.upper()}] Processing complete")
                
            except Exception as e:
                logger.error(f"  ✗ [{language.upper()}] Processing failed: {e}")
                self.stats['messages_failed'] += 1
        
        return processed_items
    
    def produce_processed_items(self, processed_items: List[ProcessedNewsItem]):
        """
        Produce processed items to language-specific Kafka topics
        
        Args:
            processed_items: List of processed news items
        """
        topic_mapping = {
            'en': 'news-english',
            'hi': 'news-hindi',
            'bn': 'news-bengali'
        }
        
        for item in processed_items:
            topic = topic_mapping.get(item.language)
            if not topic:
                logger.warning(f"No topic mapping for language: {item.language}")
                continue
            
            try:
                # Convert to JSON
                message_value = item.to_json()
                
                # Produce to Kafka
                self.producer.producer.produce(
                    topic=topic,
                    key=item.original_id.encode('utf-8'),
                    value=message_value.encode('utf-8'),
                    callback=self.producer._delivery_callback
                )
                
                logger.debug(f"Produced {item.language} item to {topic}")
                
            except Exception as e:
                logger.error(f"Failed to produce {item.language} item: {e}")
    
    def run_continuous(self, batch_size: int = 5):
        """
        Run continuous processing loop
        
        Args:
            batch_size: Number of messages to process in each batch
        """
        logger.info("\n" + "="*80)
        logger.info("STARTING CONTINUOUS PROCESSING")
        logger.info(f"Batch size: {batch_size} messages")
        logger.info("Press Ctrl+C to stop")
        logger.info("="*80 + "\n")
        
        try:
            while self.consumer.running:
                # Consume batch of messages
                logger.info(f"Waiting for messages from raw-news-feed...")
                news_item = self.consumer.consume_message(timeout=5.0)
                
                if news_item is None:
                    continue
                
                self.stats['messages_processed'] += 1
                
                # Process the news item
                processed_items = self.process_news_item(news_item)
                
                # Produce to language topics
                if processed_items:
                    self.produce_processed_items(processed_items)
                    self.producer.producer.poll(0)  # Trigger callbacks
                
                # Log progress
                logger.info(f"\n{'='*60}")
                logger.info(f"✓ Processed message #{self.stats['messages_processed']}")
                logger.info(f"  Generated {len(processed_items)} audio files")
                logger.info(f"{'='*60}\n")
                
        except KeyboardInterrupt:
            logger.info("\n\nShutting down processing consumer...")
        finally:
            self.shutdown()
    
    def process_batch(self, max_messages: int = 10):
        """
        Process a batch of messages then exit
        
        Args:
            max_messages: Maximum messages to process
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"BATCH PROCESSING: {max_messages} messages")
        logger.info(f"{'='*80}\n")
        
        processed_count = 0
        
        for i in range(max_messages):
            news_item = self.consumer.consume_message(timeout=10.0)
            
            if news_item is None:
                logger.info("No more messages available")
                break
            
            self.stats['messages_processed'] += 1
            processed_count += 1
            
            # Process
            processed_items = self.process_news_item(news_item)
            
            # Produce
            if processed_items:
                self.produce_processed_items(processed_items)
                self.producer.producer.poll(0)
        
        # Flush producer
        self.producer.producer.flush(timeout=10)
        
        logger.info(f"\n{'='*80}")
        logger.info(f"✓ Batch complete: {processed_count} messages processed")
        logger.info(f"{'='*80}\n")
        
        return processed_count
    
    def get_stats(self) -> Dict:
        """Get processing statistics"""
        translation_stats = self.translation_service.get_stats()
        tts_stats = self.tts_service.get_stats()
        
        return {
            'messages_processed': self.stats['messages_processed'],
            'messages_failed': self.stats['messages_failed'],
            'by_language': self.stats['by_language'],
            'translation_service': translation_stats,
            'tts_service': tts_stats
        }
    
    def shutdown(self):
        """Gracefully shutdown"""
        logger.info("Flushing Kafka producer...")
        self.producer.close()
        
        logger.info("Closing Kafka consumer...")
        self.consumer.close()
        
        # Print final stats
        stats = self.get_stats()
        logger.info("\n" + "="*80)
        logger.info("PROCESSING STATISTICS")
        logger.info("="*80)
        logger.info(f"Messages Processed: {stats['messages_processed']}")
        logger.info(f"Messages Failed: {stats['messages_failed']}")
        logger.info(f"By Language: {stats['by_language']}")
        logger.info(f"Translation Calls: {stats['translation_service']['total_calls']}")
        logger.info(f"TTS Calls: {stats['tts_service']['total_calls']}")
        logger.info("="*80 + "\n")
        
        logger.info("✓ Processing consumer shutdown complete")


def main():
    """Main entry point"""
    import argparse
    
    # Load config to get defaults from .env
    config = get_config()
    
    parser = argparse.ArgumentParser(description='News Processing Consumer')
    parser.add_argument('--mode', choices=['batch', 'continuous'], default='batch')
    parser.add_argument('--max', type=int, default=5)
    parser.add_argument('--kafka', default=config.kafka.bootstrap_servers)
    
    # Use Config values as defaults!
    parser.add_argument(
        '--translation-provider',
        choices=['mock', 'gemini'],
        default=config.api.translation_provider, 
        help='Translation provider'
    )
    parser.add_argument(
        '--tts-provider',
        choices=['mock', 'elevenlabs'],
        default=config.api.tts_provider,
        help='TTS provider'
    )
    
    args = parser.parse_args()
    
    # Initialize consumer with keys from Config
    consumer = NewsProcessingConsumer(
        kafka_bootstrap_servers=args.kafka,
        translation_provider=args.translation_provider,
        tts_provider=args.tts_provider,
        # Pass keys directly from config
        translation_api_key=config.api.gemini_api_key,
        tts_api_key=config.api.elevenlabs_api_key,
        output_dir=config.app.audio_output_dir
    )
    
    if args.mode == 'batch':
        consumer.process_batch(max_messages=args.max)
    else:
        consumer.run_continuous()

if __name__ == "__main__":
    main()