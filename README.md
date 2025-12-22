# Dynamic Multilingual News Desk - Setup Guide

## 🎯 Project Overview

A real-time news aggregation system that fetches global headlines, translates them, and broadcasts in multiple languages.

**Current Phase**: Data Ingestion, Deduplication & Kafka Streaming ✅

## 📁 Project Structure

```
news-aggregator/
├── config/
│   └── sources.yaml          # RSS feed configurations
├── models/
│   └── news_item.py          # News data model
├── services/
│   ├── news_fetcher.py       # Main fetcher with retry logic
│   ├── content_scraper.py    # Article content scraper
│   ├── deduplicator.py       # Redis-based deduplication
│   ├── kafka_producer.py     # Kafka producer service
│   └── kafka_consumer.py     # Kafka consumer service
├── news_pipeline.py          # Complete ingestion pipeline
├── docker-compose.yml        # Docker services
├── requirements.txt          # Python dependencies
├── test_fetcher.py          # Test news fetching
├── test_kafka_pipeline.py   # Test Kafka integration
└── README.md                 # This file
```

## 🚀 Quick Start

### 1. Start Docker Services

```bash
# Start Redis and Kafka
docker-compose up -d

# Verify services are running
docker-compose ps
```

You should see:
- ✅ Redis on port 6379
- ✅ Kafka on port 9092/9093
- ✅ Zookeeper on port 2181
- ✅ Kafka UI on port 8080 (optional, for monitoring)

### 2. Install Python Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Test the Complete Pipeline

```bash
# Test Kafka integration
python test_kafka_pipeline.py

# Run pipeline once
python news_pipeline.py --mode once

# Run continuously (every 15 minutes)
python news_pipeline.py --mode continuous --interval 15
```

Expected output:
```
[Test 1] Kafka Connection...
✓ Kafka connection successful

[Test 2] Topic Creation...
✓ Topic exists: raw-news-feed
✓ Topic exists: news-english
✓ Topic exists: news-hindi
✓ Topic exists: news-bengali

[Test 3] Produce & Consume...
✓ Produce & consume test successful

[Test 4] Full Pipeline...
✓ Full pipeline test successful

Result: 4/4 tests passed
```

## 🔧 Configuration

### RSS Feed Sources (`config/sources.yaml`)

Configure news sources with priorities:

```yaml
feeds:
  technology:
    - url: "https://techcrunch.com/feed/"
      name: "TechCrunch"
      priority: 1        # 1 = highest priority
      enabled: true
```

### Settings

- **fetch_interval_minutes**: 15 (how often to fetch news)
- **retry_attempts**: 2 (retry failed feeds)
- **rate_limit_delay_seconds**: 2 (delay between feeds)
- **max_articles_per_feed**: 10

## 🎯 Features Implemented

### ✅ Phase 1: Data Ingestion (COMPLETE)

1. **Multi-Source RSS Fetching**
   - 4 categories: General, Tech, Business, Sports
   - 12+ reliable news sources
   - Priority-based fetching

2. **Intelligent Content Scraping**
   - Full article extraction (not just RSS summaries)
   - Rotating user agents to avoid blocking
   - Automatic fallback for paywalled sites (Bloomberg, WSJ, etc.)
   - Image extraction

3. **Deduplication**
   - Redis-based caching (24-hour TTL)
   - SHA-256 hashing of URL + title
   - Prevents processing same article twice

4. **Robust Error Handling**
   - 2 retry attempts with exponential backoff
   - Graceful degradation (RSS description if scraping fails)
   - Rate limiting to respect sources

### ✅ Phase 2: Kafka Streaming (COMPLETE)

5. **Kafka Producer**
   - Produces to 4 topics: raw-news-feed, news-english, news-hindi, news-bengali
   - Batching and compression (gzip)
   - Delivery confirmations and statistics
   - Automatic topic creation

6. **Kafka Consumer**
   - Subscribes to multiple topics
   - Batch and continuous consumption modes
   - Offset management and error handling

7. **Integrated Pipeline**
   - Fetch → Deduplicate → Produce to Kafka
   - Scheduled execution (every 15 minutes)
   - Health checks and monitoring
   - Graceful shutdown handling

## 📊 Testing Individual Components

### Test News Fetcher Only

```bash
python test_fetcher.py
```

### Test Kafka Producer/Consumer

```python
# Terminal 1: Start consumer
python -m services.kafka_consumer --topic raw-news-feed --continuous

# Terminal 2: Run pipeline
python news_pipeline.py --mode once
```

### Monitor Kafka Topics (Kafka UI)

Open browser: http://localhost:8080

You'll see:
- Topics: raw-news-feed, news-english, news-hindi, news-bengali
- Message counts and throughput
- Consumer groups and lag

### Consume Specific Number of Messages

```bash
# Consume last 10 messages
python -m services.kafka_consumer --topic raw-news-feed --max 10

# Consume continuously
python -m services.kafka_consumer --topic raw-news-feed --continuous
```

## 🐛 Troubleshooting

### Redis Connection Error

```bash
# Check if Redis is running
docker-compose ps redis

# Restart Redis
docker-compose restart redis

# Check logs
docker-compose logs redis
```

### "403 Forbidden" Errors

This is **expected** for paywalled sites (Bloomberg, WSJ, NYT). The system automatically uses RSS descriptions for these sources.

### No Articles Fetched

1. Check internet connection
2. Verify RSS feeds are accessible: `curl -I https://techcrunch.com/feed/`
3. Check rate limiting delays in config

### Kafka Connection Error

```bash
# Check if Kafka is running
docker-compose ps kafka

# Kafka takes ~30 seconds to start
docker-compose logs -f kafka | grep "started"

# Restart Kafka
docker-compose restart kafka zookeeper
```

### No Messages in Kafka Topics

```bash
# Check Kafka UI
open http://localhost:8080

# Manually test producer
python -c "from services.kafka_producer import NewsKafkaProducer; p = NewsKafkaProducer(); print(p.health_check())"

# Check topic exists
docker exec -it news_kafka kafka-topics --list --bootstrap-server localhost:9092
```

## 🎛️ Monitoring

### View Kafka Topics (Kafka UI)

Open browser: http://localhost:8080

### Check Redis Cache

```bash
# Connect to Redis CLI
docker exec -it news_redis redis-cli

# Count cached articles
KEYS news:seen:*
```

## 📝 Next Steps

- [x] **Phase 1**: Data Ingestion & Deduplication ✅
- [x] **Phase 2**: Kafka Producer & Streaming ✅
- [ ] **Phase 3**: Gemini Integration (translation + summarization)
- [ ] **Phase 4**: ElevenLabs Integration (text-to-speech)
- [ ] **Phase 5**: Frontend Interface (playlist player)

## 🔗 Useful Links

- **Kafka UI**: http://localhost:8080
- **Redis**: localhost:6379
- **Hackathon**: https://ai-partner-catalyst.devpost.com/

## 📄 License

Built for AI Partner Catalyst Hackathon 2024