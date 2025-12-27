# Complete Setup Guide

## 📦 Prerequisites

### Required Software

- **Python 3.13+**
- **uv** - Fast Python package manager
- **Docker & Docker Compose**
- **Node.js 20+** and npm
- **Git**

### API Keys

You'll need:
1. **Google Gemini API Key** - Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. **ElevenLabs API Key** - Get from [ElevenLabs](https://elevenlabs.io/)

## 🚀 Installation Steps

### 1. Install uv Package Manager

uv is a fast Python package manager written in Rust. Install it:

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Alternative (using pip):**
```bash
pip install uv
```

Verify installation:
```bash
uv --version
```

### 2. Clone Repository

```bash
git clone <repository-url>
cd news-aggregator
```

### 3. Setup Python Environment with uv

```bash
# Create virtual environment using uv
uv venv

# Activate virtual environment
# macOS/Linux:
source .venv/bin/activate

# Windows:
.venv\Scripts\activate

# Your prompt should now show (.venv)
```

### 4. Install Python Dependencies

**Option A: Using requirements.txt**
```bash
uv pip install -r requirements.txt
```

**Option B: Using pyproject.toml (recommended)**
```bash
# Install all dependencies including dev dependencies
uv sync

# Install only production dependencies
uv sync --no-dev
```

**Option C: Install individual packages**
```bash
# Install core packages
uv add fastapi uvicorn confluent-kafka redis pyyaml

# Install AI packages
uv add google-genai elevenlabs

# Install testing packages
uv add --dev pytest pytest-cov pytest-asyncio
```

Verify installation:
```bash
uv pip list
```

### 5. Setup Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit with your favorite editor
nano .env
# or
vim .env
# or
code .env  # VS Code
```

**Required Configuration:**

```env
# ============================================
# API Keys (REQUIRED for production)
# ============================================
GEMINI_API_KEY=your_gemini_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# ============================================
# Service Providers
# ============================================
# For development, use 'mock'
# For production, use 'gemini' and 'elevenlabs'
TRANSLATION_PROVIDER=gemini
TTS_PROVIDER=elevenlabs

# ============================================
# Kafka Configuration
# ============================================
# Local development (default)
KAFKA_BOOTSTRAP_SERVERS=localhost:9093

# Production (Confluent Cloud example)
# KAFKA_BOOTSTRAP_SERVERS=pkc-xxx.us-east-1.aws.confluent.cloud:9092
# KAFKA_CREDENTIALS=API_KEY:API_SECRET

# ============================================
# Redis Configuration
# ============================================
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_TTL_HOURS=24

# Production (managed Redis)
# REDIS_PASSWORD=your_redis_password
# REDIS_SSL=true

# ============================================
# Application Settings
# ============================================
ENVIRONMENT=development
LOG_LEVEL=INFO
AUDIO_OUTPUT_DIR=audio_output
MAX_WORKERS=4
FETCH_INTERVAL_MINUTES=15
ENABLE_DEDUPLICATION=true

# ============================================
# Frontend Configuration
# ============================================
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 6. Create Required Directories

```bash
# Create directories for logs and audio
mkdir -p logs
mkdir -p audio_output
mkdir -p test_audio_output
```

### 7. Start Docker Services

```bash
# Start Redis, Kafka, Zookeeper
docker-compose up -d

# Verify services are running
docker-compose ps

# Expected output:
# NAME              IMAGE                          STATUS
# news_redis        redis:7-alpine                 Up
# news_kafka        confluentinc/cp-kafka:7.5.0    Up
# news_zookeeper    confluentinc/cp-zookeeper:7.5.0 Up
# news_kafka_ui     provectuslabs/kafka-ui:latest  Up
```

**Verify Docker Services:**

```bash
# Test Redis
docker exec -it news_redis redis-cli ping
# Should return: PONG

# Test Kafka (wait ~30 seconds for startup)
docker-compose logs kafka | grep "started"
# Should show: [KafkaServer id=1] started

# Open Kafka UI (optional)
open http://localhost:8080  # macOS
# or
xdg-open http://localhost:8080  # Linux
```

### 8. Setup Frontend

```bash
# Navigate to frontend directory
cd frontend

# Install Node.js dependencies
npm install

# Create environment file
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Return to root directory
cd ..
```

## ✅ Verify Setup

### 1. Test Python Installation

```bash
# Check Python version
python --version
# Should be 3.13+

# Check installed packages
uv pip list | grep -E "fastapi|confluent-kafka|redis|genai|elevenlabs"
```

### 2. Test Docker Services

```bash
# Test Redis connection
python -c "
import redis
r = redis.Redis(host='localhost', port=6379)
print(f'Redis: {r.ping()}')
"
# Should print: Redis: True

# Test Kafka connection
python -c "
from confluent_kafka.admin import AdminClient
admin = AdminClient({'bootstrap.servers': 'localhost:9093'})
topics = admin.list_topics(timeout=5)
print(f'Kafka: Connected ({len(topics.topics)} topics)')
"
# Should print: Kafka: Connected (X topics)
```

### 3. Test API Keys

**Test Gemini:**
```bash
uv run python test_translation.py
```

Expected output:
```
✓ Found API Key: AIza...
Initializing Gemini Service...
Processing Article (English -> Hindi)...

✅ SUCCESS!
----------------------------------------
📄 English Summary:
SpaceX successfully launched Starship...
----------------------------------------
🕉️ Hindi Translation:
स्पेसएक्स ने सफलतापूर्वक...
----------------------------------------
```

**Test ElevenLabs:**
```bash
uv run python test_voice.py
```

Expected output:
```
✓ Found API Key: sk_...
Initializing ElevenLabs Service...

Generating EN audio...
✅ Success! Saved to: test_audio_output/test_voice_en.mp3
   File size: 45.32 KB

Generating HI audio...
✅ Success! Saved to: test_audio_output/test_voice_hi.mp3
   File size: 52.18 KB
```

### 4. Run Unit Tests

```bash
# Run fast unit tests (no Docker required)
./run_tests.sh unit

# Or with uv directly
uv run pytest -m unit -v
```

Expected output:
```
======================== test session starts =========================
tests/test_models.py::TestNewsItem::test_create_news_item PASSED
tests/test_models.py::TestNewsItem::test_news_item_id_generation PASSED
...
====================== 15 passed in 2.34s =======================
```

### 5. Run Integration Tests

```bash
# Run integration tests (requires Docker)
./run_tests.sh integration

# Or with uv
uv run pytest -m integration -v
```

## 🎯 Running the Application

### Development Mode (Mock Services)

Good for testing without API credits:

```bash
# Edit .env
TRANSLATION_PROVIDER=mock
TTS_PROVIDER=mock

# Terminal 1: Pipeline (fetches news)
uv run python news_pipeline.py --mode once

# Terminal 2: Processing (mock translation/TTS)
uv run python processing_consumer.py --mode batch --max 5

# Terminal 3: API Server
uv run python main.py

# Terminal 4: Frontend
cd frontend && npm run dev
```

### Production Mode (Real Services)

Uses real Gemini and ElevenLabs APIs:

```bash
# Edit .env
TRANSLATION_PROVIDER=gemini
TTS_PROVIDER=elevenlabs

# Terminal 1: Pipeline (runs continuously)
uv run python news_pipeline.py --mode continuous --interval 15

# Terminal 2: Processing (continuous)
uv run python processing_consumer.py --mode continuous

# Terminal 3: API Server
uv run python main.py

# Terminal 4: Frontend
cd frontend && npm run dev
```

### Access Points

- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Kafka UI**: http://localhost:8080
- **Redis**: localhost:6379

## 🔧 Development Workflow with uv

### Adding New Packages

```bash
# Add a production dependency
uv add package-name

# Add a development dependency
uv add --dev package-name

# Add with version constraint
uv add "package-name>=1.0.0,<2.0.0"

# Add from specific source
uv add --index-url https://pypi.org/simple package-name
```

### Updating Dependencies

```bash
# Show outdated packages
uv pip list --outdated

# Update a specific package
uv pip install -U package-name

# Update all packages (be careful!)
uv pip install -U -r requirements.txt

# Regenerate requirements.txt
uv pip compile pyproject.toml -o requirements.txt
```

### Running Scripts with uv

```bash
# Run any Python script
uv run python script_name.py

# Run with arguments
uv run python news_pipeline.py --mode once

# Run tests
uv run pytest

# Run with specific Python version
uv run --python 3.13 python script.py
```

### Virtual Environment Management

```bash
# Create new virtual environment
uv venv

# Create with specific Python version
uv venv --python 3.13

# Remove virtual environment
rm -rf .venv

# Recreate fresh environment
rm -rf .venv && uv venv && uv sync
```

## 🐛 Troubleshooting

### uv Installation Issues

```bash
# Check if uv is in PATH
which uv

# Add to PATH manually (Linux/macOS)
export PATH="$HOME/.cargo/bin:$PATH"

# Reinstall uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Package Installation Failures

```bash
# Clear uv cache
uv cache clean

# Try installing with verbose output
uv pip install -v package-name

# Use different index
uv pip install --index-url https://pypi.org/simple package-name
```

### Docker Service Issues

```bash
# Check if Docker is running
docker info

# Restart Docker services
docker-compose restart

# View logs
docker-compose logs kafka
docker-compose logs redis

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
# Verify environment variables are loaded
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('Gemini:', os.getenv('GEMINI_API_KEY')[:10] + '...')
print('ElevenLabs:', os.getenv('ELEVENLABS_API_KEY')[:10] + '...')
"

# Test APIs directly
uv run python test_translation.py
uv run python test_voice.py
```

### Python Version Issues

```bash
# Check Python version
python --version

# Use specific Python version with uv
uv venv --python 3.13

# Or use system Python
uv venv --python $(which python3.13)
```

## 📊 Monitoring & Logs

### View Application Logs

```bash
# Watch all logs
tail -f logs/*.log

# Watch specific service
tail -f logs/pipeline.log
tail -f logs/kafka_producer.log
tail -f logs/translation.log

# Search for errors
grep ERROR logs/*.log
```

### Monitor Docker Services

```bash
# View container status
docker-compose ps

# View resource usage
docker stats

# View logs
docker-compose logs -f kafka
docker-compose logs -f redis
```

### Monitor Kafka

Open http://localhost:8080 for:
- Topic messages and throughput
- Consumer groups and lag
- Broker health

### Monitor Redis

```bash
# Connect to Redis CLI
docker exec -it news_redis redis-cli

# Get stats
INFO

# Count cached articles
DBSIZE

# View sample keys
KEYS news:seen:* | head -20
```

## 🧹 Cleanup

### Reset Development Environment

```bash
# Stop and remove Docker containers
docker-compose down -v

# Clear Python cache
find . -type d -name "__pycache__" -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# Clear logs
rm -rf logs/*

# Clear audio files
rm -rf audio_output/*
rm -rf test_audio_output/*

# Clear test artifacts
rm -rf .coverage htmlcov/ .pytest_cache/

# Recreate virtual environment
rm -rf .venv
uv venv
uv sync
```

### Complete Reset

```bash
# Run cleanup script
./cleanup.sh

# Or manually:
docker-compose down -v
docker system prune -a
rm -rf .venv logs/* audio_output/* test_audio_output/*
uv venv && uv sync
```

## 🚀 Next Steps

1. ✅ Complete setup and verify all tests pass
2. 📝 Review configuration in `config/sources.yaml`
3. 🔑 Add your API keys to `.env`
4. 🧪 Test with mock services first
5. 🎯 Run with real services
6. 🎨 Customize frontend in `frontend/`
7. 📦 Prepare for deployment

## 📚 Additional Resources

- [uv Documentation](https://docs.astral.sh/uv/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Kafka Documentation](https://kafka.apache.org/documentation/)
- [Next.js Documentation](https://nextjs.org/docs)

## 🆘 Getting Help

1. Check logs: `tail -f logs/*.log`
2. Run health check: `curl http://localhost:8000/health`
3. Check Docker: `docker-compose ps`
4. Run tests: `./run_tests.sh unit`
5. Review [TESTING.md](TESTING.md)

---

**Setup complete! 🎉 Now run the application and start broadcasting multilingual news!**