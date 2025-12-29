# 🌍 Radio-G: Dynamic Multilingual News Desk

> AI-powered real-time news aggregation with dynamic language support, translation, and text-to-speech broadcasting

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 15](https://img.shields.io/badge/Next.js-15-black)](https://nextjs.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Status**: Production-ready with Dynamic Language Management ✅

---

## 🚀 Quick Start (3 Steps)

### Prerequisites
- **Docker** (v20.10+) and **Docker Compose** (v2.0+)
- **Python 3.13+** with **uv** package manager ([install guide](https://docs.astral.sh/uv/))
- **Node.js 20+**
- **gcloud CLI** (for GCP deployment only)
- **API Keys**: [Google Gemini](https://aistudio.google.com/apikey) | [ElevenLabs](https://elevenlabs.io/app/settings/api-keys)

### 1. Create Environment File

```bash
# Interactive setup
./scripts/create_env.sh
# Select option 1 (Local development)
```

Or manually:
```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY and ELEVENLABS_API_KEY
```

### 2. Deploy

```bash
# Deploy locally with automatic testing
./scripts/deploy.sh .env
```

That's it! The unified deployment script handles everything:
- ✅ Builds all Docker images
- ✅ Starts infrastructure (Redis, Kafka)
- ✅ Deploys all services
- ✅ Runs comprehensive tests
- ✅ Shows service URLs

### 3. Access Your Application

- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000/docs
- **Kafka UI**: http://localhost:8080

---

## 🎯 What is Radio-G?

A scalable, event-driven news aggregation system that:

1. **Fetches** news from 12+ RSS feeds across 4 categories
2. **Deduplicates** articles intelligently using Redis
3. **Streams** through Kafka for horizontal scalability
4. **Translates & Summarizes** using Google Gemini AI
5. **Converts to Speech** using ElevenLabs TTS with custom voices
6. **Serves** via REST API with a beautiful Next.js frontend

### ✨ Key Features

- **🌐 Dynamic Language Management**: Add/remove languages via Redis without code changes
- **🎙️ Custom Voice Selection**: Configure different ElevenLabs voices per language
- **🔄 Real-time Updates**: Language changes reflect immediately
- **🚀 Fan-Out Architecture**: Multiple API instances with independent caches
- **⚡ Production-Ready**: Structured JSON logging for GCP Cloud Logging
- **🏥 Health Checks**: Comprehensive health, readiness, and liveness probes

---

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
                    └────────┬────────┘
                             │
                             ▼
                ┌────────────────────────┐
                │  Kafka: raw-news-feed  │
                └───────────┬────────────┘
                            │
            ┌───────────────┴───────────────┐
            │  Processing Consumer (N×)     │
            │  • Gemini Translation         │
            │  • Summarization              │
            │  • ElevenLabs TTS             │
            └───────────────┬───────────────┘
                            │
            ┌───────────────┴───────────────┐
            │  Kafka: news-{language}*      │
            │  (Dynamic Topics)             │
            └───────────────┬───────────────┘
                            │
            ┌───────────────┴───────────────┐
            │  FastAPI Backend (N×)         │
            │  • Fan-Out Consumers          │
            │  • In-Memory Cache            │
            └───────────────┬───────────────┘
                            │
            ┌───────────────┴───────────────┐
            │  Next.js Frontend             │
            │  • Real-time Updates          │
            │  • Audio Streaming            │
            └───────────────────────────────┘
```

---

## 📦 Tech Stack

### Backend
- **Python 3.13** with `uv` package manager (ultra-fast Rust-based)
- **Apache Kafka** for event streaming
- **Redis** for deduplication and configuration
- **FastAPI** for REST API
- **Google Gemini 2.5 Flash** for translation & summarization
- **ElevenLabs Multilingual v2** for text-to-speech

### Frontend
- **Next.js 15** (App Router)
- **React 19** with TypeScript
- **Tailwind CSS v4**

### Infrastructure
- **Docker Compose** (local)
- **GCP Cloud Run** (production)
- **GCP Memorystore** (Redis)
- **Confluent Kafka** (Cloud or self-hosted)

---

## 🚢 Production Deployment

### Quick Deploy to GCP

```bash
# 1. Create production environment file
./scripts/create_env.sh  # Select option 2 (Production/GCP)

# 2. Deploy to GCP
./scripts/deploy.sh .env.prod
```

The script automatically:
- ✅ Authenticates with GCP
- ✅ Builds and pushes Docker images to GCR
- ✅ Deploys to Cloud Run
- ✅ Configures networking and IAM
- ✅ Displays service URLs

For detailed deployment instructions, see [DEPLOYMENT_COMPARISON.md](DEPLOYMENT_COMPARISON.md).

---

## 🎛️ Dynamic Language Management

### View Current Languages

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
config = json.loads(r.get('config:languages') or '{}')

# Add Spanish
config['es'] = {
    'name': 'Spanish',
    'flag': '🇪🇸',
    'voice_id': 'your_elevenlabs_voice_id',
    'enabled': True
}

r.set('config:languages', json.dumps(config))
print("✓ Spanish added")
```

**No restart needed!** Changes take effect immediately.

---

## 🧪 Testing

```bash
# Run all tests with coverage
./run_tests.sh coverage

# Run specific test categories
./run_tests.sh unit         # Fast unit tests (no Docker)
./run_tests.sh integration  # Integration tests (requires Docker)
./run_tests.sh kafka        # Kafka-specific tests
./run_tests.sh redis        # Redis-specific tests

# Using uv directly
uv run pytest                                    # All tests
uv run pytest -v                                 # Verbose
uv run pytest tests/test_models.py              # Specific file
uv run pytest --cov=services --cov-report=html  # With coverage
```

See [TESTING.md](TESTING.md) for comprehensive testing guide.

---

## 🔧 Development

### Using uv Package Manager

```bash
# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv sync

# Add dependencies
uv add package-name              # Production
uv add --dev pytest-mock         # Development

# Run scripts
uv run python news_pipeline.py
uv run pytest
```

### Manual Service Startup (for development)

```bash
# Terminal 1: Start infrastructure
docker compose up -d

# Terminal 2: Seed language configuration
uv run python scripts/seed_languages.py

# Terminal 3: News Fetching Pipeline
uv run python news_pipeline.py --mode continuous --interval 15

# Terminal 4: Processing Consumer (translation + TTS)
uv run python processing_consumer.py --mode continuous

# Terminal 5: API Server
uv run python main.py

# Terminal 6: Frontend
cd frontend && npm install && npm run dev
```

### RSS Feed Configuration

Edit [config/sources.yaml](config/sources.yaml):

```yaml
feeds:
  technology:
    - url: "https://techcrunch.com/feed/"
      name: "TechCrunch"
      priority: 1
      enabled: true

settings:
  fetch_interval_minutes: 15
  max_articles_per_feed: 10
```

---

## 📊 Monitoring

### Health Checks

```bash
# Comprehensive health check
curl http://localhost:8000/health

# Readiness probe (K8s/Cloud Run)
curl http://localhost:8000/ready

# Available languages
curl http://localhost:8000/languages

# Get playlist
curl http://localhost:8000/playlist/en?limit=10
```

### View Logs

```bash
# Watch all logs
tail -f logs/*.log

# Watch specific service
tail -f logs/pipeline.log

# Search for errors
grep ERROR logs/*.log
```

### Kafka UI

Open http://localhost:8080 to monitor:
- Topic messages and throughput
- Consumer groups and lag
- Message inspection

---

## 🚨 Troubleshooting

### Deployment Script Issues

```bash
# Check environment file exists
ls -la .env

# Verify Docker is running
docker compose ps

# View deployment logs
./scripts/deploy.sh .env 2>&1 | tee deploy.log
```

### Port Conflicts

```bash
# Check what's using a port
lsof -i :6379  # Redis
lsof -i :9093  # Kafka
lsof -i :8000  # API
lsof -i :3000  # Frontend

# Or change ports in docker-compose.yml
```

### Kafka Not Ready

```bash
# Kafka takes ~30 seconds to start
docker compose logs kafka | grep "started"

# If stuck, restart with fresh state
docker compose down -v
docker compose up -d
```

### Full Reset

```bash
# Stop and remove all Docker containers
docker compose down -v

# Remove Docker images
docker system prune -a

# Clear Python environment
rm -rf .venv
uv venv && uv sync

# Clear generated files
rm -rf logs/* audio_output/* .pytest_cache/ htmlcov/
```

---

## 📚 Documentation

- **[DEPLOYMENT_COMPARISON.md](DEPLOYMENT_COMPARISON.md)** - Deployment workflow guide
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Detailed system architecture
- **[API.md](API.md)** - Complete API reference
- **[TESTING.md](TESTING.md)** - Testing documentation
- **[ROADMAP.md](ROADMAP.md)** - Feature roadmap
- **[PLAN.md](PLAN.md)** - Internal development guide

---

## 🗺️ Project Structure

```
radio-g/
├── config/                    # Configuration files
│   ├── config.py              # Environment-based config
│   ├── logging_config.py      # Logging setup
│   └── sources.yaml           # RSS feed sources
├── services/                  # Core services
│   ├── kafka_producer.py      # Kafka producer
│   ├── kafka_consumer.py      # Kafka consumer
│   ├── language_manager.py    # Dynamic languages
│   ├── translation_service.py # Gemini translation
│   ├── tts_service.py         # ElevenLabs TTS
│   ├── deduplicator.py        # Redis deduplication
│   └── news_fetcher.py        # RSS fetcher
├── models/                    # Data models
├── utils/                     # Utilities
├── tests/                     # Test suite
├── scripts/                   # Deployment scripts
│   ├── deploy.sh              # 🚀 Unified deployment
│   ├── create_env.sh          # Environment config creator
│   └── seed_languages.py      # Language config seeder
├── frontend/                  # Next.js application
├── news_pipeline.py           # News fetching pipeline
├── processing_consumer.py     # Translation/TTS consumer
├── main.py                    # FastAPI application
├── docker-compose.yml         # Local infrastructure
├── pyproject.toml             # Python project config
└── .env.example               # Environment template
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`./run_tests.sh unit`)
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push and open a Pull Request

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Confluent** - Kafka streaming platform
- **Google Gemini** - AI-powered translation
- **ElevenLabs** - High-quality text-to-speech
- **Astral (uv)** - Lightning-fast Python package manager

---

**Built with ❤️ using Confluent, Google Gemini, and ElevenLabs**
