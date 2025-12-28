# 🌍 Dynamic Multilingual News Radio

> AI-powered real-time news aggregation with dynamic language support, translation, and text-to-speech broadcasting

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 15](https://img.shields.io/badge/Next.js-15-black)](https://nextjs.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Status**: Production-ready with Dynamic Language Management ✅

## 🎯 What is This?

A scalable, event-driven news aggregation system that:

1. **Fetches** news from 12+ RSS feeds across 4 categories (General, Technology, Business, Sports)
2. **Deduplicates** articles intelligently using Redis cache
3. **Streams** through Kafka for horizontal scalability
4. **Translates & Summarizes** using Google Gemini AI
5. **Converts to Speech** using ElevenLabs TTS with custom voices per language
6. **Serves** via REST API with a beautiful Next.js frontend

### 🆕 What's New in v2.0

- **🌐 Dynamic Language Management**: Add/remove languages without code changes via Redis configuration
- **🎙️ Custom Voice Selection**: Configure different ElevenLabs voices per language
- **🔄 Real-time Updates**: Language changes reflect immediately across the system
- **📊 Admin Controls**: Manage language configuration through Redis
- **🚀 Fan-Out Architecture**: Multiple API instances build independent caches from Kafka
- **⚡ Production-Ready Logging**: Structured JSON logging for GCP Cloud Logging
- **🏥 Health Checks**: Comprehensive health, readiness, and liveness probes
- **🔐 Environment-Based Configuration**: Separate dev/staging/production configs

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         RSS Feeds (12+)                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  News Fetcher   │ ◄─── Schedules (15min)
                    │  + Scraper      │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Deduplicator   │ ◄─── Redis Cache (24h TTL)
                    │   (Redis)       │
                    └────────┬────────┘
                             │
                             ▼
                ┌────────────────────────┐
                │  Kafka: raw-news-feed  │
                └───────────┬────────────┘
                            │
            ┌───────────────┴───────────────┐
            │  Processing Consumer (N×)     │
            │  ┌──────────────────────────┐ │
            │  │  Gemini Translation      │ │
            │  │  + Summarization         │ │
            │  └──────────────────────────┘ │
            │  ┌──────────────────────────┐ │
            │  │  ElevenLabs TTS          │ │
            │  │  (Custom Voices)         │ │
            │  └──────────────────────────┘ │
            └───────────────┬───────────────┘
                            │
            ┌───────────────┴───────────────┐
            │  Kafka: news-{language}*      │
            │  (Dynamic Topics)             │
            └───────────────┬───────────────┘
                            │
            ┌───────────────┴───────────────┐
            │  FastAPI Backend (N×)         │
            │  - Fan-Out Consumers          │
            │  - In-Memory Cache            │
            │  - Health Checks              │
            └───────────────┬───────────────┘
                            │
            ┌───────────────┴───────────────┐
            │  Next.js Frontend             │
            │  - Real-time Updates          │
            │  - Audio Streaming            │
            │  - Dynamic Language Selector  │
            └───────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│              Configuration Layer (Redis)                         │                                                                 │  ┌──────────────────────────────────────────────────────────┐   │
│  │  config:languages                                          │  │
│  │  {                                                         │  │
│  │    "en": { "name": "English", "voice_id": "...", ... }   │  │
│  │    "hi": { "name": "Hindi", "voice_id": "...", ... }     │  │
│  │    "es": { "name": "Spanish", "voice_id": "...", ... }   │  │
│  │  }                                                         │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 📦 Tech Stack

### Backend
- **Python 3.13** with `uv` package manager (ultra-fast Rust-based)
- **Apache Kafka** for event streaming and fan-out
- **Redis** for deduplication and dynamic configuration
- **FastAPI** for REST API with async support
- **Google Gemini 2.5 Flash** for translation & summarization
- **ElevenLabs Multilingual v2** for text-to-speech

### Frontend
- **Next.js 15** with App Router (React Server Components)
- **React 19** with TypeScript
- **Tailwind CSS v4** (just-in-time engine)
- **Lucide React** for icons
- **Axios** for API calls

### Infrastructure
- **Docker Compose** for local development
- **Confluent Kafka** (Cloud or self-hosted)
- **GCP Memorystore** for Redis (production)
- **GCP Cloud Run** for serverless deployment
- **GCP Cloud Logging** for structured logs

## 🚀 Quick Start

### Prerequisites

Install these tools:
- **Python 3.13+** - [Download](https://www.python.org/downloads/)
- **uv** package manager - [Install Guide](https://docs.astral.sh/uv/)
- **Docker Desktop** - [Download](https://www.docker.com/products/docker-desktop)
- **Node.js 20+** - [Download](https://nodejs.org/)

Get API keys:
- **Google Gemini API** - [Get Key](https://makersuite.google.com/app/apikey)
- **ElevenLabs API** - [Get Key](https://elevenlabs.io/)

### 1️⃣ Clone Repository

```bash
git clone <repository-url>
cd multilingual-news-radio
```

### 2️⃣ Backend Setup

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install all dependencies (uses pyproject.toml)
uv sync

# Or install from requirements.txt
uv pip install -r requirements.txt
```

### 3️⃣ Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit with your favorite editor
nano .env  # or vim, code, etc.
```

**Minimum required configuration:**

```env
# API Keys (REQUIRED)
GEMINI_API_KEY=your_gemini_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# Service Providers
TRANSLATION_PROVIDER=gemini
TTS_PROVIDER=elevenlabs

# Infrastructure (defaults work for local development)
KAFKA_BOOTSTRAP_SERVERS=localhost:9093
REDIS_HOST=localhost
REDIS_PORT=6379
```

### 4️⃣ Start Infrastructure

```bash
# Start Redis, Kafka, Zookeeper
docker-compose up -d

# Verify services are running
docker-compose ps

# Expected output:
# NAME              STATUS
# news_redis        Up
# news_kafka        Up
# news_zookeeper    Up
# news_kafka_ui     Up

# Check Kafka is ready (~30 seconds to start)
docker-compose logs kafka | grep "started"
```

### 5️⃣ Seed Language Configuration

```bash
# Initialize language configuration in Redis
uv run python scripts/seed_languages.py

# Output:
# ✓ Language configuration seeded to Redis
```

This creates the default configuration:
- **English** (voice: George)
- **Hindi** (voice: Fin)
- **Bengali** (voice: Fin)

### 6️⃣ Run Backend Services

Open 3 terminal windows:

```bash
# Terminal 1: News Fetching Pipeline (runs every 15 min)
uv run python news_pipeline.py --mode continuous --interval 15

# Terminal 2: Processing Consumer (translates + TTS)
uv run python processing_consumer.py --mode continuous

# Terminal 3: API Server
uv run python main.py
```

### 7️⃣ Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure API URL
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Run development server
npm run dev
```

### 8️⃣ Access the Application

- 🎨 **Frontend**: http://localhost:3000
- 🔌 **API**: http://localhost:8000
- 📚 **API Docs**: http://localhost:8000/docs
- 📊 **Kafka UI**: http://localhost:8080

## 🎛️ Dynamic Language Management

### View Current Configuration

```bash
# Connect to Redis
docker exec -it news_redis redis-cli

# View configuration
GET config:languages
```

### Add a New Language

```python
# scripts/add_language.py
import redis
import json

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Get current config
config = json.loads(r.get('config:languages') or '{}')

# Add Spanish
config['es'] = {
    'name': 'Spanish',
    'flag': '🇪🇸',
    'voice_id': 'your_elevenlabs_voice_id',
    'enabled': True
}

# Save
r.set('config:languages', json.dumps(config))
print("✓ Spanish added")
```

```bash
# Run the script
uv run python scripts/add_language.py
```

**No restart needed!** The system will:
1. Processing consumer picks up the new language on next message
2. API creates the new topic: `news-spanish`
3. Frontend shows Spanish in the language selector
4. Users can immediately start consuming Spanish news

### Disable a Language

```python
config['es']['enabled'] = False
r.set('config:languages', json.dumps(config))
```

### Change Voice for a Language

```python
# Use a different ElevenLabs voice for Hindi
config['hi']['voice_id'] = 'new_voice_id_here'
r.set('config:languages', json.dumps(config))
```

## 🧪 Testing

### Quick Test

```bash
# Make test script executable (first time)
chmod +x run_tests.sh

# Run fast unit tests (no Docker needed)
./run_tests.sh unit
```

### Full Test Suite

```bash
# Run all tests with coverage
./run_tests.sh coverage

# Run specific categories
./run_tests.sh integration  # Requires Docker
./run_tests.sh kafka        # Kafka-specific
./run_tests.sh redis        # Redis-specific
```

### Using uv Directly

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_models.py

# Run with coverage
uv run pytest --cov=services --cov=models --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Test API Integration

```bash
# Test Gemini translation
uv run python test_translation.py

# Test ElevenLabs TTS
uv run python test_voice.py
```

## 📝 Development Workflow

### Adding Dependencies

```bash
# Add production dependency
uv add package-name

# Add dev dependency
uv add --dev pytest-mock

# Add with version constraint
uv add "fastapi>=0.100.0"

# Sync all dependencies from pyproject.toml
uv sync
```

### Updating Dependencies

```bash
# Check for outdated packages
uv pip list --outdated

# Update specific package
uv pip install --upgrade package-name

# Update all (regenerate lock)
uv sync --upgrade
```

### Running Scripts

```bash
# Run any Python script with uv
uv run python script.py

# Run with arguments
uv run python news_pipeline.py --mode once --kafka localhost:9093

# Run with specific Python version
uv run --python 3.13 python script.py
```

### Code Quality

```bash
# Format code
uv run black .
uv run isort .

# Lint code
uv run flake8
uv run pylint services/

# Type checking (if mypy is added)
uv add --dev mypy
uv run mypy services/
```

## 🔧 Configuration

### RSS Feed Sources

Edit `config/sources.yaml`:

```yaml
feeds:
  technology:
    - url: "https://techcrunch.com/feed/"
      name: "TechCrunch"
      priority: 1
      enabled: true
    
    - url: "https://www.theverge.com/rss/index.xml"
      name: "The Verge"
      priority: 2
      enabled: true

  business:
    - url: "https://feeds.bloomberg.com/markets/news.rss"
      name: "Bloomberg"
      priority: 1
      enabled: true

settings:
  fetch_interval_minutes: 15
  retry_attempts: 2
  request_timeout_seconds: 30
  max_articles_per_feed: 10
```

### Environment Variables

Full `.env` configuration:

```env
# ============================================
# ENVIRONMENT
# ============================================
ENVIRONMENT=development  # development, staging, production
LOG_LEVEL=INFO

# ============================================
# API KEYS
# ============================================
GEMINI_API_KEY=your_key_here
ELEVENLABS_API_KEY=your_key_here

# ============================================
# SERVICE PROVIDERS
# ============================================
# Options: mock, gemini
TRANSLATION_PROVIDER=gemini

# Options: mock, elevenlabs
TTS_PROVIDER=elevenlabs

# ============================================
# KAFKA (Local Development)
# ============================================
KAFKA_BOOTSTRAP_SERVERS=localhost:9093

# Production (Confluent Cloud example)
# KAFKA_BOOTSTRAP_SERVERS=pkc-xxx.aws.confluent.cloud:9092
# KAFKA_CREDENTIALS=API_KEY:API_SECRET

# ============================================
# REDIS
# ============================================
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_TTL_HOURS=24

# Production (managed Redis)
# REDIS_PASSWORD=your_password
# REDIS_SSL=true

# ============================================
# APPLICATION
# ============================================
AUDIO_OUTPUT_DIR=audio_output
MAX_WORKERS=4
FETCH_INTERVAL_MINUTES=15
ENABLE_DEDUPLICATION=true

# ============================================
# BACKEND API
# ============================================
PORT=8000
ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com

# ============================================
# FRONTEND
# ============================================
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 📊 Monitoring

### Application Logs

```bash
# Watch all logs
tail -f logs/*.log

# Watch specific service
tail -f logs/pipeline.log
tail -f logs/kafka_producer.log
tail -f logs/translation.log
tail -f logs/tts.log

# Search for errors
grep ERROR logs/*.log

# Follow logs during test
tail -f logs/*.log & uv run pytest
```

### Kafka Monitoring

Open **Kafka UI**: http://localhost:8080

Features:
- Topic messages and throughput
- Consumer groups and lag
- Broker health
- Message inspection

### API Health Checks

```bash
# Comprehensive health check
curl http://localhost:8000/health

# Readiness probe (for K8s/Cloud Run)
curl http://localhost:8000/ready

# Liveness probe
curl http://localhost:8000/live

# Get available languages
curl http://localhost:8000/languages

# Get English playlist
curl http://localhost:8000/playlist/en?limit=10
```

### Redis Monitoring

```bash
# Connect to Redis CLI
docker exec -it news_redis redis-cli

# View stats
INFO

# Count cached articles
DBSIZE

# View sample dedupe keys
KEYS news:seen:* | head -20

# View language config
GET config:languages

# Clear cache (use with caution!)
FLUSHDB
```

## 🚨 Troubleshooting

### uv Issues

```bash
# Check uv version
uv --version

# Reinstall uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clear cache
uv cache clean

# Recreate virtual environment
rm -rf .venv
uv venv
uv sync
```

### Docker Service Issues

```bash
# Check Docker is running
docker info

# Check service status
docker-compose ps

# View logs
docker-compose logs kafka
docker-compose logs redis

# Restart specific service
docker-compose restart kafka

# Reset everything
docker-compose down -v
docker-compose up -d
```

### Port Conflicts

```bash
# Check what's using a port
lsof -i :6379  # Redis
lsof -i :9093  # Kafka
lsof -i :8000  # API
lsof -i :3000  # Frontend

# Kill process
kill -9 <PID>

# Or change ports in docker-compose.yml
```

### API Key Issues

```bash
# Verify environment variables loaded
uv run python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print(f'Gemini: {os.getenv(\"GEMINI_API_KEY\", \"NOT SET\")[:10]}...')
print(f'ElevenLabs: {os.getenv(\"ELEVENLABS_API_KEY\", \"NOT SET\")[:10]}...')
"

# Test APIs directly
uv run python test_translation.py
uv run python test_voice.py
```

### Kafka Not Ready

```bash
# Kafka takes ~30 seconds to start
# Check if fully started:
docker-compose logs kafka | grep "started"

# If stuck, restart with fresh state
docker-compose down -v
docker-compose up -d

# Wait 30 seconds, then verify
docker-compose logs -f kafka
```

### Import Errors

```bash
# Reinstall dependencies
uv sync --reinstall

# Check Python path
uv run python -c "import sys; print('\n'.join(sys.path))"

# Verify package installation
uv pip list | grep kafka

# Clear Python cache
find . -type d -name "__pycache__" -exec rm -r {} +
find . -type f -name "*.pyc" -delete
```

## 🧹 Cleanup

### Quick Cleanup

```bash
# Stop Docker services
docker-compose down

# Clear logs
rm -rf logs/*

# Clear audio files
rm -rf audio_output/*
rm -rf test_audio_output/*
```

### Full Reset

```bash
# Stop and remove all Docker containers
docker-compose down -v

# Remove Docker images
docker system prune -a

# Clear Python environment
rm -rf .venv

# Clear all generated files
rm -rf logs/* audio_output/* test_audio_output/*
rm -rf .pytest_cache/ htmlcov/ .coverage

# Recreate environment
uv venv
uv sync
```

## 📚 Documentation

- [SETUP.md](docs/SETUP.md) - Detailed setup guide
- [TESTING.md](docs/TESTING.md) - Testing documentation
- [DEPLOYMENT.md](docs/DEPLOYMENT.md) - Production deployment guide
- [ROADMAP.md](docs/ROADMAP.md) - Feature roadmap
- [API Docs](http://localhost:8000/docs) - Interactive API documentation

## 🗺️ Project Structure

```
multilingual-news-radio/
├── config/
│   ├── config.py              # Environment-based configuration
│   ├── logging_config.py      # Structured logging setup
│   └── sources.yaml           # RSS feed sources
├── services/
│   ├── content_scraper.py     # Article content extraction
│   ├── deduplicator.py        # Redis-based deduplication
│   ├── kafka_producer.py      # Kafka message producer
│   ├── kafka_consumer.py      # Kafka message consumer
│   ├── language_manager.py    # Dynamic language configuration
│   ├── news_fetcher.py        # RSS feed fetcher
│   ├── translation_service.py # Gemini translation
│   └── tts_service.py         # ElevenLabs TTS
├── models/
│   └── news_item.py           # Data models
├── utils/
│   └── health.py              # Health check utilities
├── tests/                     # Test suite
├── scripts/
│   └── seed_languages.py      # Language config seeding
├── frontend/                  # Next.js application
├── news_pipeline.py           # News fetching pipeline
├── processing_consumer.py     # Translation/TTS consumer
├── main.py                    # FastAPI application
├── docker-compose.yml         # Local infrastructure
├── pyproject.toml             # Python project config
├── requirements.txt           # Python dependencies
└── .env.example               # Environment template
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`./run_tests.sh unit`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Confluent** - Kafka streaming platform
- **Google Gemini** - AI-powered translation
- **ElevenLabs** - High-quality text-to-speech
- **Astral (uv)** - Lightning-fast Python package manager
- **Next.js Team** - React framework
- **Vercel** - Deployment platform

## 📞 Support

- **Documentation**: Check [docs/](docs/) folder
- **Issues**: Open a GitHub issue
- **Email**: support@example.com

---

**Built with ❤️ for AI Partner Catalyst Hackathon 2024**

*Powered by Confluent, Google Gemini, and ElevenLabs*