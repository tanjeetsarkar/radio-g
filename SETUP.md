# Complete Setup Guide

## 📦 Prerequisites

- Python 3.13+
- Docker & Docker Compose
- Git

## 🚀 Installation Steps

### 1. Clone Repository

```bash
git clone <repository-url>
cd news-aggregator
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate  # Windows
```

### 3. Install Dependencies

```bash
# Install all dependencies (including testing)
pip install -r requirements.txt

# Verify installation
pip list
```

### 4. Setup Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
nano .env  # or use your preferred editor
```

### 5. Start Docker Services

```bash
# Start all services (Redis, Kafka, Zookeeper)
docker-compose up -d

# Verify services are running
docker-compose ps

# Expected output:
# news_redis      redis:7-alpine    running    0.0.0.0:6379->6379/tcp
# news_kafka      cp-kafka:7.5.0    running    0.0.0.0:9092-9093->9092-9093/tcp
# news_zookeeper  cp-zookeeper:7.5.0 running   0.0.0.0:2181->2181/tcp
# news_kafka_ui   kafka-ui:latest   running    0.0.0.0:8080->8080/tcp
```

### 6. Create Required Directories

```bash
# Create logs directory for file-based logging
mkdir -p logs

# Create audio output directory
mkdir -p audio_output

# Create test directories
mkdir -p test_audio_output
mkdir -p htmlcov  # For coverage reports
```

## ✅ Verify Setup

### 1. Test Docker Services

```bash
# Test Redis connection
docker exec -it news_redis redis-cli ping
# Should return: PONG

# Test Kafka
docker exec -it news_kafka kafka-broker-api-versions --bootstrap-server localhost:9092
# Should list broker API versions

# Open Kafka UI (optional)
open http://localhost:8080  # macOS
# OR
xdg-open http://localhost:8080  # Linux
```

### 2. Run Health Checks

```bash
# Quick Python health check
python -c "
import redis
import yaml
from confluent_kafka.admin import AdminClient

# Test Redis
r = redis.Redis(host='localhost', port=6379)
print(f'Redis: {r.ping()}')

# Test Kafka
admin = AdminClient({'bootstrap.servers': 'localhost:9093'})
topics = admin.list_topics(timeout=5)
print(f'Kafka: Connected ({len(topics.topics)} topics)')
"
```

### 3. Run Unit Tests

```bash
# Run fast unit tests (no Docker required)
./run_tests.sh unit

# Or with pytest directly
pytest -m unit -v
```

### 4. Run Integration Tests

```bash
# Run integration tests (requires Docker)
./run_tests.sh integration
```

## 🔧 Configuration

### RSS Feed Sources

Edit `config/sources.yaml` to customize news sources:

```yaml
feeds:
  technology:
    - url: "https://techcrunch.com/feed/"
      name: "TechCrunch"
      priority: 1
      enabled: true
```

### Logging Configuration

Logging is automatically configured using the centralized `LoggerConfig`:

```python
from utils.logging_config import LoggerConfig

# Get a logger for your module
logger = LoggerConfig.get_logger(__name__)

# Logs are automatically saved to logs/{module_name}.log
logger.info("Your log message")
```

Log files are located in `logs/` directory:
- `news_fetcher.log` - News fetching logs
- `kafka_producer.log` - Kafka production logs
- `kafka_consumer.log` - Kafka consumption logs
- `deduplicator.log` - Deduplication logs
- `translation.log` - Translation service logs
- `tts.log` - Text-to-speech logs
- `pipeline.log` - Pipeline execution logs

### Service Configuration

Configure services via environment variables in `.env`:

```env
# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_TTL_HOURS=24

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9093

# Fetcher
FETCH_INTERVAL_MINUTES=15
MAX_ARTICLES_PER_FEED=10
```

## 📋 Development Workflow

### 1. Start Services

```bash
# Start Docker services
docker-compose up -d

# Verify services
docker-compose ps
```

### 2. Run Tests

```bash
# Run all tests
./run_tests.sh all

# Run specific test category
./run_tests.sh unit
./run_tests.sh integration
./run_tests.sh kafka

# Run with coverage
./run_tests.sh coverage
```

### 3. Run Pipeline

```bash
# Run pipeline once
python news_pipeline.py --mode once

# Run continuously (every 15 minutes)
python news_pipeline.py --mode continuous --interval 15

# Run with custom settings
python news_pipeline.py \
  --mode once \
  --kafka localhost:9093 \
  --redis-host localhost \
  --redis-port 6379
```

### 4. Process News

```bash
# Process news with mock services (development)
python processing_consumer.py \
  --mode batch \
  --max 5 \
  --translation-provider mock \
  --tts-provider mock

# Process continuously
python processing_consumer.py \
  --mode continuous \
  --translation-provider mock \
  --tts-provider mock
```

### 5. Monitor Services

```bash
# View logs in real-time
tail -f logs/*.log

# View specific service logs
tail -f logs/pipeline.log

# Kafka UI
open http://localhost:8080

# Check Redis keys
docker exec -it news_redis redis-cli
> KEYS news:seen:*
> DBSIZE
```

## 🔍 Debugging

### Check Logs

```bash
# View all logs
ls -lh logs/

# View last 50 lines of a log
tail -50 logs/kafka_producer.log

# Search for errors
grep ERROR logs/*.log

# Watch logs in real-time
tail -f logs/*.log
```

### Check Docker Services

```bash
# Check running containers
docker-compose ps

# View container logs
docker-compose logs redis
docker-compose logs kafka

# Restart services
docker-compose restart redis
docker-compose restart kafka

# Rebuild services
docker-compose down
docker-compose up -d --build
```

### Reset Everything

```bash
# Stop all services
docker-compose down

# Remove volumes (clears all data)
docker-compose down -v

# Clear Redis cache
docker exec -it news_redis redis-cli FLUSHALL

# Delete Kafka topics
docker exec -it news_kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --delete --topic raw-news-feed

# Clean Python cache
find . -type d -name "__pycache__" -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# Remove logs
rm -rf logs/*

# Remove coverage data
rm -rf .coverage htmlcov/

# Start fresh
docker-compose up -d
```

## 📊 Monitoring & Metrics

### Kafka UI

Access Kafka UI at http://localhost:8080 to monitor:
- Topics and partitions
- Messages and throughput
- Consumer groups and lag
- Broker health

### Redis Stats

```bash
# Connect to Redis CLI
docker exec -it news_redis redis-cli

# Get Redis info
INFO

# Get memory usage
INFO memory

# Count cached articles
DBSIZE

# View sample keys
KEYS news:seen:* | head -10
```

### Pipeline Stats

```python
from news_pipeline import NewsPipeline

pipeline = NewsPipeline()
stats = pipeline.get_stats()
print(stats)
```

## 🐛 Common Issues

### Port Already in Use

```bash
# Find process using port
lsof -i :6379  # Redis
lsof -i :9093  # Kafka

# Kill process
kill -9 <PID>

# Or change ports in docker-compose.yml
```

### Docker Services Not Starting

```bash
# Check Docker daemon
docker info

# Restart Docker
sudo systemctl restart docker  # Linux
# OR restart Docker Desktop

# Check disk space
df -h

# Prune Docker
docker system prune -a
```

### Import Errors

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check Python path
python -c "import sys; print('\n'.join(sys.path))"
```

### Redis Connection Failed

```bash
# Check if Redis is running
docker-compose ps redis

# Check Redis logs
docker-compose logs redis

# Test connection
docker exec -it news_redis redis-cli ping

# Restart Redis
docker-compose restart redis
```

### Kafka Connection Failed

```bash
# Kafka takes ~30 seconds to start
docker-compose logs -f kafka | grep "started"

# Check Kafka health
docker exec -it news_kafka kafka-broker-api-versions \
  --bootstrap-server localhost:9092

# Restart Kafka
docker-compose restart kafka zookeeper
```

## 🚀 Next Steps

1. ✅ Complete setup and verify all services
2. ✅ Run all tests to ensure everything works
3. 📝 Review configuration in `config/sources.yaml`
4. 🔄 Run the pipeline once to fetch news
5. 🧪 Process news with mock services
6. 🎯 Add real API keys for Gemini & ElevenLabs (Phase 3 & 4)
7. 🎨 Build frontend interface (Phase 5)

## 📚 Documentation

- [README.md](README.md) - Project overview and quick start
- [TESTING.md](TESTING.md) - Comprehensive testing guide
- [SETUP.md](SETUP.md) - This file
- API documentation: Run `python -m pydoc -b` and navigate to modules

## 🆘 Getting Help

1. Check logs: `tail -f logs/*.log`
2. Run health checks: `./run_tests.sh unit`
3. Review Docker services: `docker-compose ps`
4. Check documentation: `README.md` and `TESTING.md`

## ✨ Tips for Success

1. **Always activate virtual environment** before working
2. **Start Docker services** before running integration tests
3. **Check logs** when something fails
4. **Run tests frequently** during development
5. **Monitor Kafka UI** to see message flow
6. **Clean up resources** when done (ports, containers, volumes)

Happy coding! 🎉