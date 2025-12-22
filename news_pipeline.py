"""
Complete news ingestion pipeline
Fetches news from RSS feeds and produces to Kafka
"""

import logging
import time
import schedule
from datetime import datetime
from typing import Dict
import sys

from services.news_fetcher import NewsFetcher
from services.kafka_producer import NewsKafkaProducer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('news_pipeline.log')
    ]
)
logger = logging.getLogger(__name__)


class NewsPipeline:
    """
    Complete news ingestion pipeline
    Orchestrates fetching, deduplication, and Kafka production
    """
    
    def __init__(
        self,
        kafka_bootstrap_servers: str = "localhost:9093",
        redis_host: str = "localhost",
        redis_port: int = 6379,
        enable_deduplication: bool = True
    ):
        """
        Initialize pipeline components
        
        Args:
            kafka_bootstrap_servers: Kafka broker addresses
            redis_host: Redis host for deduplication
            redis_port: Redis port
            enable_deduplication: Enable/disable deduplication
        """
        logger.info("="*80)
        logger.info("INITIALIZING NEWS INGESTION PIPELINE")
        logger.info("="*80)
        
        # Initialize news fetcher
        logger.info("Initializing News Fetcher...")
        self.fetcher = NewsFetcher(use_deduplication=enable_deduplication)
        
        # Initialize Kafka producer
        logger.info("Initializing Kafka Producer...")
        self.producer = NewsKafkaProducer(bootstrap_servers=kafka_bootstrap_servers)
        
        # Create Kafka topics if needed
        logger.info("Creating Kafka topics...")
        self.producer.create_topics_if_not_exist()
        
        # Pipeline statistics
        self.total_runs = 0
        self.total_articles_fetched = 0
        self.total_articles_produced = 0
        
        logger.info("✓ Pipeline initialized successfully")
    
    def health_check(self) -> Dict:
        """
        Check health of all pipeline components
        
        Returns:
            Dictionary with health status of each component
        """
        logger.info("Running health checks...")
        
        health = {
            'timestamp': datetime.now().isoformat(),
            'kafka': self.producer.health_check(),
            'redis': None
        }
        
        # Check Redis if deduplication is enabled
        if self.fetcher.deduplicator:
            health['redis'] = self.fetcher.deduplicator.check_health()
        
        # Overall status
        kafka_ok = health['kafka']['connected']
        redis_ok = health['redis']['connected'] if health['redis'] else True
        
        health['overall'] = 'healthy' if (kafka_ok and redis_ok) else 'degraded'
        
        logger.info(f"Health Check: {health['overall'].upper()}")
        return health
    
    def run_once(self) -> Dict:
        """
        Run the pipeline once: fetch news and produce to Kafka
        
        Returns:
            Dictionary with run statistics
        """
        self.total_runs += 1
        run_start = time.time()
        
        logger.info("\n" + "="*80)
        logger.info(f"PIPELINE RUN #{self.total_runs}")
        logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*80)
        
        try:
            # Step 1: Fetch news from all sources
            logger.info("\n[Step 1/2] Fetching news from RSS feeds...")
            news_items = self.fetcher.fetch_all_feeds()
            
            if not news_items:
                logger.warning("No news items fetched!")
                return {
                    'success': False,
                    'articles_fetched': 0,
                    'articles_produced': 0,
                    'duration_seconds': time.time() - run_start
                }
            
            self.total_articles_fetched += len(news_items)
            logger.info(f"✓ Fetched {len(news_items)} unique articles")
            
            # Step 2: Produce to Kafka
            logger.info("\n[Step 2/2] Producing to Kafka...")
            results = self.producer.produce_by_category(news_items)
            
            # Calculate totals
            total_produced = sum(r['delivered'] for r in results.values())
            total_failed = sum(r['failed'] for r in results.values())
            
            self.total_articles_produced += total_produced
            
            # Log results by category
            logger.info("\n📊 Results by Category:")
            for category, stats in results.items():
                logger.info(
                    f"  {category.upper()}: "
                    f"{stats['delivered']}/{stats['total']} delivered "
                    f"({stats['success_rate']:.1f}%)"
                )
            
            run_duration = time.time() - run_start
            
            logger.info("\n" + "="*80)
            logger.info(f"✓ PIPELINE RUN #{self.total_runs} COMPLETE")
            logger.info(f"  Articles Fetched: {len(news_items)}")
            logger.info(f"  Articles Produced: {total_produced}")
            logger.info(f"  Failed: {total_failed}")
            logger.info(f"  Duration: {run_duration:.2f}s")
            logger.info("="*80 + "\n")
            
            return {
                'success': True,
                'run_number': self.total_runs,
                'articles_fetched': len(news_items),
                'articles_produced': total_produced,
                'articles_failed': total_failed,
                'duration_seconds': run_duration,
                'category_breakdown': results
            }
            
        except Exception as e:
            logger.error(f"Pipeline run failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'duration_seconds': time.time() - run_start
            }
    
    def run_continuous(self, interval_minutes: int = 15):
        """
        Run pipeline continuously at specified interval
        
        Args:
            interval_minutes: Minutes between each run
        """
        logger.info("\n" + "="*80)
        logger.info("STARTING CONTINUOUS PIPELINE")
        logger.info(f"Interval: Every {interval_minutes} minutes")
        logger.info("Press Ctrl+C to stop")
        logger.info("="*80 + "\n")
        
        # Schedule the job
        schedule.every(interval_minutes).minutes.do(self.run_once)
        
        # Run immediately on start
        logger.info("Running initial fetch...")
        self.run_once()
        
        # Continuous loop
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\n\nShutting down pipeline...")
            self.shutdown()
    
    def get_stats(self) -> Dict:
        """Get overall pipeline statistics"""
        producer_stats = self.producer.get_stats()
        
        stats = {
            'total_runs': self.total_runs,
            'total_articles_fetched': self.total_articles_fetched,
            'total_articles_produced': self.total_articles_produced,
            'producer_stats': producer_stats
        }
        
        if self.fetcher.deduplicator:
            stats['cached_articles'] = self.fetcher.deduplicator.get_seen_count()
        
        return stats
    
    def shutdown(self):
        """Gracefully shutdown pipeline"""
        logger.info("Closing Kafka producer...")
        self.producer.close()
        
        # Print final stats
        stats = self.get_stats()
        logger.info("\n" + "="*80)
        logger.info("PIPELINE STATISTICS")
        logger.info("="*80)
        logger.info(f"Total Runs: {stats['total_runs']}")
        logger.info(f"Total Articles Fetched: {stats['total_articles_fetched']}")
        logger.info(f"Total Articles Produced: {stats['total_articles_produced']}")
        logger.info("="*80 + "\n")
        
        logger.info("✓ Pipeline shutdown complete")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='News Ingestion Pipeline')
    parser.add_argument(
        '--mode',
        choices=['once', 'continuous'],
        default='once',
        help='Run mode: once or continuous'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=15,
        help='Interval in minutes for continuous mode (default: 15)'
    )
    parser.add_argument(
        '--kafka',
        default='localhost:9093',
        help='Kafka bootstrap servers (default: localhost:9093)'
    )
    parser.add_argument(
        '--redis-host',
        default='localhost',
        help='Redis host (default: localhost)'
    )
    parser.add_argument(
        '--redis-port',
        type=int,
        default=6379,
        help='Redis port (default: 6379)'
    )
    parser.add_argument(
        '--no-dedup',
        action='store_true',
        help='Disable deduplication'
    )
    
    args = parser.parse_args()
    
    # Initialize pipeline
    pipeline = NewsPipeline(
        kafka_bootstrap_servers=args.kafka,
        redis_host=args.redis_host,
        redis_port=args.redis_port,
        enable_deduplication=not args.no_dedup
    )
    
    # Health check
    health = pipeline.health_check()
    if health['overall'] != 'healthy':
        logger.warning("Pipeline health check shows issues - proceeding anyway")
    
    # Run pipeline
    if args.mode == 'once':
        result = pipeline.run_once()
        pipeline.shutdown()
        sys.exit(0 if result['success'] else 1)
    else:
        pipeline.run_continuous(interval_minutes=args.interval)


if __name__ == "__main__":
    main()