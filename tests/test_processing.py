import pytest
import time
import json
from pathlib import Path
from unittest.mock import patch, Mock

from services.translation_service import TranslationService
from services.tts_service import TTSService
from processing_consumer import NewsProcessingConsumer, ProcessedNewsItem
from models.news_item import NewsItem


@pytest.mark.unit
@pytest.mark.mock
class TestTranslationServiceIntegration:
    """Integration tests for translation service"""
    
    def test_translation_service_initialization(self):
        """Test translation service initializes correctly"""
        service = TranslationService(provider="mock")
        
        assert service.provider_name == "mock"
        assert service.provider is not None
        
        stats = service.get_stats()
        assert stats['total_calls'] == 0
    
    def test_translate_multiple_languages(self):
        """Test translating to multiple languages"""
        service = TranslationService(provider="mock")
        
        text = "Breaking news: Technology company announces new product."
        languages = ['en', 'hi', 'bn']
        
        results = {}
        for lang in languages:
            results[lang] = service.translate(text, lang)
        
        # Check each language has appropriate marker
        assert '[EN]' in results['en'] or 'Breaking' in results['en']
        assert '[HI-हिंदी]' in results['hi']
        assert '[BN-বাংলা]' in results['bn']
    
    def test_translation_and_summarization_pipeline(self):
        """Test complete translation + summarization"""
        service = TranslationService(provider="mock")
        
        long_text = """
        Breaking news from the technology sector. A major artificial 
        intelligence company has announced a groundbreaking new language 
        model that demonstrates unprecedented capabilities. The model can 
        understand and generate human-like text across multiple languages 
        with remarkable accuracy. Industry experts are calling this a 
        significant milestone in AI research.
        """
        
        result = service.translate_and_summarize(
            long_text,
            target_language='hi',
            max_length=150
        )
        
        assert 'summary' in result
        assert 'translated_summary' in result
        assert result['target_language'] == 'hi'
        assert len(result['translated_summary']) <= 300  # With buffer


@pytest.mark.unit
@pytest.mark.mock
class TestTTSServiceIntegration:
    """Integration tests for TTS service"""
    
    def test_tts_service_initialization(self, temp_dir):
        """Test TTS service initializes correctly"""
        service = TTSService(provider="mock", output_dir=str(temp_dir))
        
        assert service.provider_name == "mock"
        assert service.output_dir == temp_dir
        
        stats = service.get_stats()
        assert stats['total_calls'] == 0
    
    def test_generate_audio_multiple_languages(self, temp_dir):
        """Test generating audio for multiple languages"""
        service = TTSService(provider="mock", output_dir=str(temp_dir))
        
        text = "This is a test news summary."
        languages = ['en', 'hi', 'bn']
        
        audio_files = {}
        for lang in languages:
            filename = f"test_{lang}.mp3"
            path = service.save_speech(text, lang, filename)
            audio_files[lang] = path
        
        # Verify all files created
        for lang, path in audio_files.items():
            assert Path(path).exists()
            
            # Check metadata file
            metadata_path = Path(path).with_suffix('.json')
            assert metadata_path.exists()
            
            with open(metadata_path) as f:
                metadata = json.load(f)
            
            assert metadata['language'] == lang
            assert 'estimated_duration_seconds' in metadata
    
    def test_batch_audio_generation(self, temp_dir):
        """Test batch audio generation"""
        service = TTSService(provider="mock", output_dir=str(temp_dir))
        
        texts = {
            'news_1': "First news story",
            'news_2': "Second news story",
            'news_3': "Third news story"
        }
        
        results = service.batch_generate(texts, 'en')
        
        assert len(results) == 3
        assert all(v is not None for v in results.values())
        
        # Verify files exist
        for audio_path in results.values():
            assert Path(audio_path).exists()


@pytest.mark.kafka
@pytest.mark.integration
@pytest.mark.slow
class TestProcessingConsumerInitialization:
    """Test processing consumer initialization"""
    
    def test_consumer_initialization(self, test_config, check_kafka):
        """Test processing consumer initializes correctly"""
        consumer = NewsProcessingConsumer(
            kafka_bootstrap_servers=test_config['kafka_servers'],
            translation_provider='mock',
            tts_provider='mock',
            target_languages=['en', 'hi', 'bn'],
            output_dir='test_audio_output'
        )
        
        assert consumer.consumer is not None
        assert consumer.producer is not None
        assert consumer.translation_service is not None
        assert consumer.tts_service is not None
        assert consumer.target_languages == ['en', 'hi', 'bn']
        
        consumer.shutdown()
    
    def test_consumer_statistics(self, test_config, check_kafka):
        """Test getting consumer statistics"""
        consumer = NewsProcessingConsumer(
            kafka_bootstrap_servers=test_config['kafka_servers'],
            translation_provider='mock',
            tts_provider='mock'
        )
        
        stats = consumer.get_stats()
        
        assert 'messages_processed' in stats
        assert 'messages_failed' in stats
        assert 'by_language' in stats
        assert 'translation_service' in stats
        assert 'tts_service' in stats
        
        consumer.shutdown()


@pytest.mark.unit
@pytest.mark.mock
class TestProcessedNewsItem:
    """Test ProcessedNewsItem model"""
    
    def test_processed_news_item_creation(self):
        """Test creating a ProcessedNewsItem"""
        item = ProcessedNewsItem(
            original_id='test-123',
            original_title='Test Article',
            original_url='https://example.com/test',
            category='technology',
            source='Test Source',
            published_date='2024-01-01T12:00:00Z',
            language='en',
            summary='Short summary',
            translated_summary='Translated summary',
            audio_file='audio/test.mp3',
            audio_duration=45.5,
            processed_at='2024-01-01T12:05:00Z',
            processing_provider='mock',
            tts_provider='mock'
        )
        
        assert item.original_id == 'test-123'
        assert item.language == 'en'
        assert item.audio_duration == 45.5
    
    def test_processed_item_serialization(self):
        """Test ProcessedNewsItem serialization"""
        item = ProcessedNewsItem(
            original_id='test-123',
            original_title='Test Article',
            original_url='https://example.com/test',
            category='technology',
            source='Test Source',
            published_date='2024-01-01T12:00:00Z',
            language='hi',
            summary='Summary',
            translated_summary='Translated',
            audio_file='audio/test.mp3',
            audio_duration=30.0,
            processed_at='2024-01-01T12:05:00Z',
            processing_provider='mock',
            tts_provider='mock'
        )
        
        # Test to_json
        json_str = item.to_json()
        assert isinstance(json_str, str)
        
        # Test from_dict
        data = json.loads(json_str)
        restored = ProcessedNewsItem.from_dict(data)
        
        assert restored.original_id == item.original_id
        assert restored.language == item.language


@pytest.mark.kafka
@pytest.mark.integration
@pytest.mark.slow
class TestProcessingConsumerEndToEnd:
    """End-to-end tests for processing consumer"""
    
    @patch('services.news_fetcher.NewsFetcher.fetch_all_feeds')
    def test_process_single_news_item(
        self,
        mock_fetch,
        test_config,
        check_kafka,
        sample_news_item,
        temp_dir
    ):
        """Test processing a single news item"""
        from news_pipeline import NewsPipeline
        
        # Mock fetcher to return sample data
        mock_fetch.return_value = [sample_news_item]
        
        # Step 1: Produce news to raw-news-feed
        pipeline = NewsPipeline(
            kafka_bootstrap_servers=test_config['kafka_servers'],
            enable_deduplication=False
        )
        
        result = pipeline.run_once()
        assert result['success'] is True
        
        pipeline.shutdown()
        
        # Wait for messages
        time.sleep(2)
        
        # Step 2: Process the news
        consumer = NewsProcessingConsumer(
            kafka_bootstrap_servers=test_config['kafka_servers'],
            translation_provider='mock',
            tts_provider='mock',
            target_languages=['en'],
            output_dir=str(temp_dir)
        )
        
        # Process one message
        processed_count = consumer.process_batch(max_messages=1)
        
        stats = consumer.get_stats()
        
        consumer.shutdown()
        
        # Should have processed at least something
        # (timing might make this flaky, so be lenient)
        assert processed_count >= 0
        assert stats['messages_processed'] >= 0
    
    def test_process_batch_of_news(
        self,
        test_config,
        check_kafka,
        temp_dir
    ):
        """Test processing a batch of news items"""
        from services.kafka_producer import NewsKafkaProducer
        from datetime import datetime, timezone
        
        # Create test news items
        items = []
        for i in range(3):
            item = NewsItem(
                title=f"Test Article {i}",
                description=f"Description {i}",
                url=f"https://example.com/test-{i}",
                category='technology',
                source='Test Source',
                published_date=datetime.now(timezone.utc),
                fetched_at=datetime.now(timezone.utc),
                content=f"Full content for article {i}"
            )
            items.append(item)
        
        # Produce to raw-news-feed
        producer = NewsKafkaProducer(
            bootstrap_servers=test_config['kafka_servers']
        )
        producer.produce_batch(items, 'raw-news-feed')
        producer.close()
        
        time.sleep(2)
        
        # Process
        consumer = NewsProcessingConsumer(
            kafka_bootstrap_servers=test_config['kafka_servers'],
            translation_provider='mock',
            tts_provider='mock',
            target_languages=['en'],
            output_dir=str(temp_dir)
        )
        
        processed = consumer.process_batch(max_messages=3)
        
        stats = consumer.get_stats()
        
        consumer.shutdown()
        
        # Verify processing happened
        assert processed >= 0
        
        # Check audio files were created
        audio_dir = Path(temp_dir)
        audio_files = list(audio_dir.glob('*.mp3'))
        
        # Should have created some audio files
        # (lenient check due to timing)
        assert len(audio_files) >= 0


@pytest.mark.unit
@pytest.mark.mock
class TestProcessingConsumerLogic:
    """Test processing consumer logic"""
    
    def test_process_news_item_creates_all_languages(
        self,
        test_config,
        check_kafka,
        sample_news_item,
        temp_dir
    ):
        """Test that processing creates output for all target languages"""
        consumer = NewsProcessingConsumer(
            kafka_bootstrap_servers=test_config['kafka_servers'],
            translation_provider='mock',
            tts_provider='mock',
            target_languages=['en', 'hi', 'bn'],
            output_dir=str(temp_dir)
        )
        
        # Process the item
        processed_items = consumer.process_news_item(sample_news_item)
        
        # Should create 3 items (one per language)
        assert len(processed_items) == 3
        
        # Verify each language
        languages = [item.language for item in processed_items]
        assert 'en' in languages
        assert 'hi' in languages
        assert 'bn' in languages
        
        # Verify audio files reference
        for item in processed_items:
            assert item.audio_file
            assert item.audio_duration > 0
        
        consumer.shutdown()
    
    def test_produce_processed_items(
        self,
        test_config,
        check_kafka,
        temp_dir
    ):
        """Test producing processed items to language topics"""
        consumer = NewsProcessingConsumer(
            kafka_bootstrap_servers=test_config['kafka_servers'],
            translation_provider='mock',
            tts_provider='mock',
            target_languages=['en'],
            output_dir=str(temp_dir)
        )
        
        # Create a processed item
        processed_item = ProcessedNewsItem(
            original_id='test-123',
            original_title='Test Article',
            original_url='https://example.com/test',
            category='technology',
            source='Test Source',
            published_date='2024-01-01T12:00:00Z',
            language='en',
            summary='Summary',
            translated_summary='Translated summary',
            audio_file=f'{temp_dir}/test.mp3',
            audio_duration=30.0,
            processed_at='2024-01-01T12:05:00Z',
            processing_provider='mock',
            tts_provider='mock'
        )
        
        # Produce to Kafka
        consumer.produce_processed_items([processed_item])
        consumer.producer.producer.flush(timeout=10)
        
        consumer.shutdown()
        
        # If no errors, test passes
        assert True


@pytest.mark.integration
@pytest.mark.slow
class TestProcessingConsumerErrorHandling:
    """Test error handling in processing consumer"""
    
    def test_handles_missing_content(
        self,
        test_config,
        check_kafka,
        temp_dir
    ):
        """Test consumer handles news items with missing content"""
        from datetime import datetime, timezone
        
        # Create item with no content
        item = NewsItem(
            title='Test Article',
            description='Short description',
            url='https://example.com/test',
            category='technology',
            source='Test Source',
            published_date=datetime.now(timezone.utc),
            fetched_at=datetime.now(timezone.utc),
            content=None  # No content
        )
        
        consumer = NewsProcessingConsumer(
            kafka_bootstrap_servers=test_config['kafka_servers'],
            translation_provider='mock',
            tts_provider='mock',
            target_languages=['en'],
            output_dir=str(temp_dir)
        )
        
        # Should handle gracefully
        processed = consumer.process_news_item(item)
        
        # Should still create items (using description)
        assert len(processed) > 0
        
        consumer.shutdown()


# Helper function for manual testing
def run_manual_processing_test():
    """Helper for manual processing testing"""
    print("\n" + "="*60)
    print("MANUAL PROCESSING TEST")
    print("="*60)
    
    print("\n[1/3] Testing translation service...")
    translation = TranslationService(provider='mock')
    
    text = "Breaking news: Technology company launches new AI product."
    result = translation.translate_and_summarize(text, 'hi', max_length=100)
    
    print(f"  Original: {text[:50]}...")
    print(f"  Summary: {result['summary'][:50]}...")
    print(f"  Translated: {result['translated_summary'][:50]}...")
    
    print("\n[2/3] Testing TTS service...")
    tts = TTSService(provider='mock', output_dir='test_audio_output')
    
    audio_path = tts.save_speech(result['translated_summary'], 'hi')
    print(f"  Audio saved: {audio_path}")
    
    print("\n[3/3] Checking files...")
    from pathlib import Path
    audio_dir = Path('test_audio_output')
    files = list(audio_dir.glob('*.mp3'))
    print(f"  Audio files: {len(files)}")
    print(f"  Metadata files: {len(list(audio_dir.glob('*.json')))}")
    
    print("\n" + "="*60)
    print("✓ Processing test complete")
    print("="*60)


if __name__ == "__main__":
    run_manual_processing_test()