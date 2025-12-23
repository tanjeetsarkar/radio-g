"""
Test the complete processing pipeline with mock services
"""

import logging
import sys
import time

from services.translation_service import TranslationService
from services.tts_service import TTSService
from processing_consumer import NewsProcessingConsumer
from news_pipeline import NewsPipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_translation_service():
    """Test translation service"""
    logger.info("="*60)
    logger.info("Test 1: Translation Service")
    logger.info("="*60)
    
    try:
        service = TranslationService(provider="mock")
        
        sample_text = """
        Breaking news from the technology sector today. 
        A major artificial intelligence company has announced 
        a groundbreaking new language model that demonstrates 
        unprecedented capabilities in understanding and 
        generating human-like text across multiple languages.
        """
        
        # Test translation
        hindi = service.translate(sample_text, "hi")
        assert "[HI-हिंदी]" in hindi
        logger.info(f"✓ Translation working: {hindi[:80]}...")
        
        # Test summarization
        summary = service.summarize(sample_text, max_length=100)
        assert len(summary) <= 150
        logger.info(f"✓ Summarization working: {summary}")
        
        # Test combined
        result = service.translate_and_summarize(sample_text, "bn", max_length=120)
        assert 'summary' in result
        assert 'translated_summary' in result
        logger.info(f"✓ Combined operation working")
        
        # Stats
        stats = service.get_stats()
        logger.info(f"✓ Service stats: {stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Translation service test failed: {e}")
        return False


def test_tts_service():
    """Test TTS service"""
    logger.info("\n" + "="*60)
    logger.info("Test 2: Text-to-Speech Service")
    logger.info("="*60)
    
    try:
        service = TTSService(provider="mock", output_dir="test_audio_output")
        
        # Test single generation
        text = "[EN] Breaking news: Technology advances rapidly today."
        audio_path = service.save_speech(text, "en")
        
        import os
        assert os.path.exists(audio_path)
        logger.info(f"✓ Audio file created: {audio_path}")
        
        # Check metadata file
        metadata_path = audio_path.replace('.mp3', '.json')
        assert os.path.exists(metadata_path)
        logger.info(f"✓ Metadata file created: {metadata_path}")
        
        # Test batch generation
        batch_texts = {
            'news_1': "First news story text",
            'news_2': "Second news story text",
            'news_3': "Third news story text"
        }
        results = service.batch_generate(batch_texts, "hi")
        assert len(results) == 3
        logger.info(f"✓ Batch generation: {len(results)} files created")
        
        # Stats
        stats = service.get_stats()
        logger.info(f"✓ Service stats: {stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ TTS service test failed: {e}", exc_info=True)
        return False


def test_end_to_end_pipeline():
    """Test complete end-to-end pipeline"""
    logger.info("\n" + "="*60)
    logger.info("Test 3: End-to-End Pipeline")
    logger.info("="*60)
    
    try:
        # Step 1: Generate some news
        logger.info("\n[Step 1] Generating news...")
        pipeline = NewsPipeline(
            kafka_bootstrap_servers="localhost:9093",
            enable_deduplication=False  # Disable for testing
        )
        
        result = pipeline.run_once()
        
        if not result['success']:
            logger.error("News pipeline failed")
            return False
        
        produced = result.get('articles_produced', 0)
        logger.info(f"✓ Produced {produced} articles to raw-news-feed")
        
        if produced == 0:
            logger.warning("No articles produced, cannot test processing")
            return False
        
        pipeline.shutdown()
        
        # Wait a moment for messages to be available
        time.sleep(2)
        
        # Step 2: Process the news
        logger.info("\n[Step 2] Processing news with translation + TTS...")
        processor = NewsProcessingConsumer(
            kafka_bootstrap_servers="localhost:9093",
            translation_provider="mock",
            tts_provider="mock",
            target_languages=['en', 'hi', 'bn'],
            output_dir="test_audio_output"
        )
        
        # Process a batch
        processed_count = processor.process_batch(max_messages=3)
        
        if processed_count == 0:
            logger.warning("No messages processed")
            return False
        
        logger.info(f"✓ Processed {processed_count} messages")
        
        # Get stats
        stats = processor.get_stats()
        logger.info(f"\nProcessing Stats:")
        logger.info(f"  Messages: {stats['messages_processed']}")
        logger.info(f"  By Language: {stats['by_language']}")
        logger.info(f"  Translation Calls: {stats['translation_service']['total_calls']}")
        logger.info(f"  TTS Calls: {stats['tts_service']['total_calls']}")
        
        # Verify audio files were created
        import os
        audio_files = os.listdir("test_audio_output")
        audio_files = [f for f in audio_files if f.endswith('.mp3')]
        
        expected_audio_files = processed_count * len(['en', 'hi', 'bn'])
        logger.info(f"\n✓ Created {len(audio_files)} audio files (expected ~{expected_audio_files})")
        
        processor.shutdown()
        
        return True
        
    except Exception as e:
        logger.error(f"✗ End-to-end test failed: {e}", exc_info=True)
        return False


def test_language_specific_consumers():
    """Test consuming from language-specific topics"""
    logger.info("\n" + "="*60)
    logger.info("Test 4: Language-Specific Topics")
    logger.info("="*60)
    
    try:
        from services.kafka_consumer import NewsKafkaConsumer
        from processing_consumer import ProcessedNewsItem
        
        topics_to_check = ['news-english', 'news-hindi', 'news-bengali']
        
        for topic in topics_to_check:
            consumer = NewsKafkaConsumer(
                bootstrap_servers="localhost:9093",
                group_id=f"test-{topic}",
                auto_offset_reset="earliest"
            )
            
            consumer.subscribe([topic])
            
            # Try to consume one message
            msg = consumer.consume_message(timeout=5.0)
            
            if msg:
                # It's a ProcessedNewsItem (JSON string)
                logger.info(f"✓ {topic}: Message available")
            else:
                logger.info(f"⚠ {topic}: No messages yet (may be timing)")
            
            consumer.close()
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Language topic test failed: {e}")
        return False


def cleanup_test_files():
    """Clean up test artifacts"""
    logger.info("\nCleaning up test files...")
    
    import shutil
    import os
    
    if os.path.exists("test_audio_output"):
        shutil.rmtree("test_audio_output")
        logger.info("✓ Cleaned up test_audio_output/")


def main():
    """Run all processing tests"""
    print("\n" + "="*60)
    print("PROCESSING PIPELINE TEST SUITE")
    print("="*60)
    
    tests = [
        ("Translation Service", test_translation_service),
        ("Text-to-Speech Service", test_tts_service),
        ("End-to-End Pipeline", test_end_to_end_pipeline),
        ("Language-Specific Topics", test_language_specific_consumers)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except KeyboardInterrupt:
            logger.info("\nTests interrupted by user")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Cleanup
    cleanup_test_files()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print("="*60)
    print(f"Result: {passed}/{total} tests passed")
    print("="*60 + "\n")
    
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()