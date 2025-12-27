# Dynamic Multilingual News Desk

A real-time news aggregation system that fetches global headlines, translates them into multiple languages, and converts them to audio broadcasts.

**Status**: Production-ready MVP ✅

## 🎯 Project Overview

This system:
1. **Fetches** news from 12+ RSS feeds across 4 categories
2. **Deduplicates** articles using Redis cache
3. **Streams** via Kafka for scalability
4. **Translates** using Google Gemini API (English, Hindi, Bengali)
5. **Converts** to audio using ElevenLabs text-to-speech
6. **Serves** via REST API with Next.js frontend

## 🏗️ Architecture

```
RSS Feeds → News Fetcher → Deduplicator (Redis) → Kafka (raw-news-feed)
                                                         ↓
                                                   Processing Consumer
                                                    ├─ Gemini (translate)
                                                    └─ ElevenLabs (TTS)
                                                         ↓
                                              Kafka (news-en/hi/bn)
                                                         ↓
                                                   FastAPI Backend
                                                         ↓
                                                  Next.js Frontend
```

## 📦 Tech Stack

### Backend
- **Python 3.13** with `uv` package manager
- **Kafka** for event streaming
- **Redis** for deduplication
- **FastAPI** for REST API
- **Google Gemini** for translation
- **ElevenLabs** for text-to-speech

### Frontend
- **Next.js 15** with App Router
- **React 19** with TypeScript
- **Tailwind CSS v4**
- **Lucide React** for icons

## 🚀 Quick Start

### Prerequisites

- **Python 3.13+**
- **uv** package manager ([install guide](https://docs.astral.sh/uv/getting-started/installation/))
- **Docker & Docker Compose**
- **Node.js 20+** (for frontend)
- **API Keys**:
  - Google Gemini API key
  - ElevenLabs API key

### 1. Clone Repository

```bash
git clone <repository-url>
cd news-aggregator
```

### 2. Backend Setup

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install all dependencies
uv pip install -r requirements.txt

# Or use uv sync (if you have a pyproject.toml)
uv sync
```

### 3. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your API keys
nano .env
```

Required variables:
```env
# Gemini API
GEMINI_API_KEY=your_gemini_api_key_here

# ElevenLabs API
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# Kafka (use defaults for local)
KAFKA_BOOTSTRAP_SERVERS=localhost:9093

# Redis (use defaults for local)
REDIS_HOST=localhost
REDIS_PORT=6379

# Service Configuration
TRANSLATION_PROVIDER=gemini
TTS_PROVIDER=elevenlabs
```

### 4. Start Infrastructure

```bash
# Start Redis and Kafka
docker-compose up -d

# Verify services are running
docker-compose ps

# Check logs if needed
docker-compose logs -f kafka redis
```

### 5. Run Backend Services

```bash
# Terminal 1: Run news fetching pipeline (fetches every 15 min)
python news_pipeline.py --mode continuous --interval 15

# Terminal 2: Run processing consumer (translates + TTS)
python processing_consumer.py --mode continuous

# Terminal 3: Run API server
python main.py
```

### 6. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure API URL
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Run development server
npm run dev
```

### 7. Access the Application

- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Kafka UI**: http://localhost:8080

## 🧪 Testing

```bash
# Make test script executable (first time only)
chmod +x run_tests.sh

# Run all tests
./run_tests.sh all

# Run fast tests only (no Docker required)
./run_tests.sh unit

# Run integration tests (requires Docker)
./run_tests.sh integration

# Run with coverage report
./run_tests.sh coverage
```

Or use pytest directly with uv:

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_models.py

# Run with coverage
uv run pytest --cov=services --cov=models
```

## 📝 Development with uv

### Install New Package

```bash
# Add a new package
uv add package-name

# Add a dev dependency
uv add --dev package-name

# Add with specific version
uv add "package-name>=1.0.0"
```

### Update Dependencies

```bash
# Update all packages
uv pip list --outdated
uv pip install -U package-name

# Or regenerate requirements
uv pip compile pyproject.toml -o requirements.txt
```

### Run Python Scripts with uv

```bash
# Run script with uv
uv run python news_pipeline.py

# Run with specific Python version
uv run --python 3.13 python script.py
```

## 🎛️ Configuration

### RSS Feed Sources

Edit `config/sources.yaml`:

```yaml
feeds:
  technology:
    - url: "https://techcrunch.com/feed/"
      name: "TechCrunch"
      priority: 1
      enabled: true
```

### Service Providers

Edit `.env`:

```env
# Use mock services for development
TRANSLATION_PROVIDER=mock
TTS_PROVIDER=mock

# Use real services for production
TRANSLATION_PROVIDER=gemini
TTS_PROVIDER=elevenlabs
```

## 📊 Monitoring

### View Logs

```bash
# All logs
tail -f logs/*.log

# Specific service
tail -f logs/pipeline.log
tail -f logs/kafka_producer.log
tail -f logs/translation.log
```

### Kafka UI

Open http://localhost:8080 to monitor:
- Topics and messages
- Consumer groups
- Broker health

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Readiness probe
curl http://localhost:8000/ready

# Liveness probe
curl http://localhost:8000/live
```

## 🐳 Production Deployment

### Environment Variables for Production

```env
# Required
ENVIRONMENT=production
GEMINI_API_KEY=xxx
ELEVENLABS_API_KEY=xxx

# Confluent Cloud Kafka (example)
KAFKA_BOOTSTRAP_SERVERS=pkc-xxx.us-east-1.aws.confluent.cloud:9092
KAFKA_CREDENTIALS=API_KEY:API_SECRET

# Redis (managed)
REDIS_HOST=your-redis-host
REDIS_PORT=6379
REDIS_PASSWORD=xxx
REDIS_SSL=true

# Application
LOG_LEVEL=INFO
AUDIO_OUTPUT_DIR=/app/audio_output
MAX_WORKERS=4
```

### Docker Build

```bash
# Build backend image
docker build -t news-radio-backend .

# Build frontend image
cd frontend
docker build -t news-radio-frontend .
```

### Scaling Considerations

- **News Fetcher**: Single instance (scheduled)
- **Processing Consumer**: Scale horizontally (3-5 instances)
- **API Server**: Scale horizontally (auto-scaling)
- **Frontend**: Static hosting or edge deployment

## 🔧 Troubleshooting

### uv Issues

```bash
# Reinstall uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clear uv cache
uv cache clean

# Recreate virtual environment
rm -rf .venv
uv venv
```

### Port Conflicts

```bash
# Check what's using a port
lsof -i :6379  # Redis
lsof -i :9093  # Kafka
lsof -i :8000  # API

# Kill process
kill -9 <PID>
```

### Docker Issues

```bash
# Restart services
docker-compose restart

# Reset everything
docker-compose down -v
docker-compose up -d
```

### API Key Issues

```bash
# Test Gemini API
python test_translation.py

# Test ElevenLabs API
python test_voice.py
```

## 📚 Documentation

- [SETUP.md](SETUP.md) - Detailed setup instructions
- [TESTING.md](TESTING.md) - Testing guide
- [API Documentation](http://localhost:8000/docs) - Interactive API docs

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is built for the AI Partner Catalyst Hackathon 2024.

## 🙏 Acknowledgments

- **Confluent** - Kafka streaming platform
- **Google Gemini** - Translation and summarization
- **ElevenLabs** - Text-to-speech synthesis
- **Astral (uv)** - Fast Python package manager

## 📞 Support

For issues or questions:
1. Check the [documentation](SETUP.md)
2. Review [troubleshooting guide](#-troubleshooting)
3. Open an issue on GitHub

---

**Built with ❤️ for AI Partner Catalyst Hackathon 2024**