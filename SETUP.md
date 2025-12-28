# 🛠️ Complete Setup Guide

> Step-by-step guide to set up Multilingual News Radio locally using uv

**Target**: Local Development Environment  
**Last Updated**: December 28, 2024

---

## 📋 Table of Contents

1. [Prerequisites](#-prerequisites)
2. [Quick Start (5 Minutes)](#-quick-start-5-minutes)
3. [Detailed Setup](#-detailed-setup)
4. [Environment Configuration](#-environment-configuration)
5. [Running the Application](#-running-the-application)
6. [Development Workflow](#-development-workflow)
7. [Troubleshooting](#-troubleshooting)

---

## 📦 Prerequisites

### Required Software

Install these before starting:

#### 1. Python 3.13+

```bash
# macOS (using Homebrew)
brew install python@3.13

# Ubuntu/Debian
sudo apt update
sudo apt install python3.13 python3.13-venv

# Windows
# Download from: https://www.python.org/downloads/
# ✅ Check "Add Python to PATH" during installation

# Verify installation
python3.13 --version  # Should show: Python 3.13.x
```

#### 2. uv (Fast Python Package Manager)

```bash
# macOS/Linux (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Alternative: Using pip
pip install uv

# Alternative: Using Homebrew (macOS)
brew install uv

# Verify installation
uv --version  # Should show: uv x.x.x
```

**💡 Why uv?**
- 10-100x faster than pip
- Better dependency resolution
- Built-in virtual environment management
- Zero configuration needed

#### 3. Docker Desktop

```bash
# macOS/Windows: Download from
https://www.docker.com/products/docker-desktop

# Ubuntu/Debian
sudo apt install docker.io docker-compose

# Start Docker
sudo systemctl start docker  # Linux
# Or open Docker Desktop app (macOS/Windows)

# Verify
docker --version
docker-compose --version
```

#### 4. Node.js 20+ (for frontend)

```bash
# macOS (using Homebrew)
brew install node@20

# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Windows: Download from
https://nodejs.org/

# Verify
node --version  # Should be v20.x.x or higher
npm --version
```

### API Keys

Get these keys (free tier available):

1. **Google Gemini API**: [makersuite.google.com](https://makersuite.google.com/app/apikey)
2. **ElevenLabs API**: [elevenlabs.io](https://elevenlabs.io/) → Account → API Keys

---

## ⚡ Quick Start (5 Minutes)

For the impatient developer:

```bash
# 1. Clone repository
git clone <repository-url>
cd multilingual-news-radio

# 2. Setup Python environment
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
uv sync

# 4. Start infrastructure
docker-compose up -d

# 5. Configure environment
cp .env.example .env
# Edit .env with your API keys (nano/vim/code .env)

# 6. Seed language configuration
uv run python scripts/seed_languages.py

# 7. Run backend (3 terminals)
# Terminal 1:
uv run python news_pipeline.py --mode once

# Terminal 2:
uv run python processing_consumer.py --mode batch --max 5

# Terminal 3:
uv run python main.py

# 8. Run frontend (new terminal)
cd frontend
npm install
npm run dev

# 9. Open browser
# Frontend: http://localhost:3000
# API: http://localhost:8000/docs
```

---

## 🔧 Detailed Setup

### Step 1: Clone Repository

```bash
# Using HTTPS
git clone https://github.com/yourusername/multilingual-news-radio.git

# Or using SSH
git clone git@github.com:yourusername/multilingual-news-radio.git

# Navigate to project
cd multilingual-news-radio

# Verify you're in the right directory
ls -la
# Should see: config/, services/, frontend/, docker-compose.yml, etc.
```

### Step 2: Python Environment Setup with uv

#### Create Virtual Environment

```bash
# Create virtual environment (in .venv/)
uv venv

# The command creates:
# - .venv/ directory
# - Python 3.13 interpreter
# - pip, setuptools included
```

#### Activate Virtual Environment

```bash
# macOS/Linux
source .venv/bin/activate

# Windows (Command Prompt)
.venv\Scripts\activate.bat

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Verify activation (prompt should show (.venv))
which python  # Should point to .venv/bin/python
python --version  # Should be 3.13.x
```

**💡 Tip**: Add this to your shell profile for auto-activation:

```bash
# Add to ~/.bashrc or ~/.zshrc
alias venv='source .venv/bin/activate'

# Now just type: venv
```

#### Install Dependencies

uv offers multiple ways to install dependencies:

```bash
# Method 1: Using pyproject.toml (recommended)
uv sync

# This installs:
# - All production dependencies
# - All dev dependencies (pytest, etc.)
# - In editable mode

# Method 2: Production only
uv sync --no-dev

# Method 3: Using requirements.txt
uv pip install -r requirements.txt

# Method 4: Install individual packages
uv pip install fastapi uvicorn confluent-kafka redis
```

**What `uv sync` does:**
1. Reads `pyproject.toml`
2. Resolves dependencies
3. Installs everything in `.venv`
4. Creates/updates `uv.lock` file

#### Verify Installation

```bash
# List installed packages
uv pip list

# Should see packages like:
# fastapi, uvicorn, confluent-kafka, redis, etc.

# Check specific packages
uv pip show fastapi
uv pip show confluent-kafka

# Run a quick test
uv run python -c "import fastapi; print(fastapi.__version__)"
```

### Step 3: Docker Infrastructure

#### Start Services

```bash
# Start all services in background
docker-compose up -d

# Services started:
# - Redis (port 6379)
# - Kafka (port 9093)
# - Zookeeper (port 2181)
# - Kafka UI (port 8080)

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f kafka
docker-compose logs -f redis
```

#### Verify Services

```bash
# Check all services are running
docker-compose ps

# Expected output:
# NAME              IMAGE                   STATUS
# news_redis        redis:7-alpine         Up
# news_kafka        cp-kafka:7.5.0         Up
# news_zookeeper    cp-zookeeper:7.5.0     Up
# news_kafka_ui     kafka-ui:latest        Up

# Test Redis
docker exec -it news_redis redis-cli ping
# Expected: PONG

# Wait for Kafka to be ready (~30 seconds)
docker-compose logs kafka | grep "started"
# Should see: [KafkaServer id=1] started

# Open Kafka UI (optional)
open http://localhost:8080  # macOS
# or visit: http://localhost:8080 in browser
```

#### Troubleshooting Docker

```bash
# If services fail to start:

# 1. Check Docker is running
docker info

# 2. Check port conflicts
lsof -i :6379  # Redis
lsof -i :9093  # Kafka
lsof -i :8080  # Kafka UI

# 3. Restart services
docker-compose restart

# 4. Reset everything (nuclear option)
docker-compose down -v
docker-compose up -d
```

### Step 4: Environment Configuration

#### Create `.env` File

```bash
# Copy example file
cp .env.example .env

# Open in editor
nano .env        # Terminal editor
vim .env         # Vim
code .env        # VS Code
subl .env        # Sublime Text
```

#### Configure API Keys

Edit `.env` and add your keys:

```env
# ============================================
# API KEYS (REQUIRED)
# ============================================
GEMINI_API_KEY=your_actual_gemini_api_key_here
ELEVENLABS_API_KEY=your_actual_elevenlabs_api_key_here

# ============================================
# SERVICE PROVIDERS
# ============================================
# For development, you can use 'mock' to avoid using API credits
# For production, use 'gemini' and 'elevenlabs'
TRANSLATION_PROVIDER=gemini
TTS_PROVIDER=elevenlabs

# ============================================
# INFRASTRUCTURE (defaults work for local)
# ============================================
KAFKA_BOOTSTRAP_SERVERS=localhost:9093
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_TTL_HOURS=24

# ============================================
# APPLICATION
# ============================================
ENVIRONMENT=development
LOG_LEVEL=INFO
AUDIO_OUTPUT_DIR=audio_output
MAX_WORKERS=4
FETCH_INTERVAL_MINUTES=15
ENABLE_DEDUPLICATION=true

# ============================================
# BACKEND API
# ============================================
PORT=8000
ALLOWED_ORIGINS=http://localhost:3000

# ============================================
# FRONTEND
# ============================================
NEXT_PUBLIC_API_URL=http://localhost:8000
```

#### Verify Environment Variables

```bash
# Test that environment is loaded
uv run python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print(f'Gemini Key: {os.getenv(\"GEMINI_API_KEY\", \"NOT SET\")[:10]}...')
print(f'ElevenLabs Key: {os.getenv(\"ELEVENLABS_API_KEY\", \"NOT SET\")[:10]}...')
print(f'Translation Provider: {os.getenv(\"TRANSLATION_PROVIDER\")}')
print(f'TTS Provider: {os.getenv(\"TTS_PROVIDER\")}')
"

# Should show:
# Gemini Key: AIzaSyXXXX...
# ElevenLabs Key: sk_XXXXXX...
# Translation Provider: gemini
# TTS Provider: elevenlabs
```

### Step 5: Initialize System

#### Create Required Directories

```bash
# Create directories for logs and audio
mkdir -p logs
mkdir -p audio_output
mkdir -p test_audio_output

# Verify
ls -la
# Should see: logs/, audio_output/, test_audio_output/
```

#### Seed Language Configuration

```bash
# Initialize language configuration in Redis
uv run python scripts/seed_languages.py

# Expected output:
# ✓ Language configuration seeded to Redis

# Verify in Redis
docker exec -it news_redis redis-cli GET config:languages
```

This creates the default configuration:
- **English** (en): George voice
- **Hindi** (hi): Fin voice  
- **Bengali** (bn): Fin voice

#### Test API Integration

```bash
# Test Gemini translation
uv run python test_translation.py

# Expected output:
# ✓ Found API Key: AIza...
# Initializing Gemini Service...
# Processing Article (English -> Hindi)...
# ✅ SUCCESS!
# ---
# English Summary: ...
# Hindi Translation: ...

# Test ElevenLabs TTS
uv run python test_voice.py

# Expected output:
# ✓ Found API Key: sk_...
# Initializing ElevenLabs Service...
# Generating EN audio...
# ✅ Success! Saved to: test_audio_output/test_voice_en.mp3
#    File size: 45.32 KB
```

### Step 6: Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# This installs:
# - Next.js 15
# - React 19
# - Tailwind CSS v4
# - All required packages

# Configure API URL
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Verify
cat .env.local

# Return to root directory
cd ..
```

---

## 🚀 Running the Application

### Development Mode (Mock Services)

Great for testing without using API credits:

```bash
# Edit .env
TRANSLATION_PROVIDER=mock
TTS_PROVIDER=mock

# Terminal 1: Fetch news (once)
uv run python news_pipeline.py --mode once

# Terminal 2: Process (mock translation/TTS)
uv run python processing_consumer.py --mode batch --max 10

# Terminal 3: API server
uv run python main.py

# Terminal 4: Frontend
cd frontend && npm run dev
```

### Production Mode (Real APIs)

Uses actual Gemini and ElevenLabs:

```bash
# Edit .env
TRANSLATION_PROVIDER=gemini
TTS_PROVIDER=elevenlabs

# Terminal 1: Fetch news continuously (every 15 min)
uv run python news_pipeline.py --mode continuous --interval 15

# Terminal 2: Process continuously
uv run python processing_consumer.py --mode continuous

# Terminal 3: API server
uv run python main.py

# Terminal 4: Frontend
cd frontend && npm run dev
```

### Command Options

#### News Pipeline

```bash
# Run once (good for testing)
uv run python news_pipeline.py --mode once

# Run continuously (production)
uv run python news_pipeline.py --mode continuous --interval 15

# With custom Kafka
uv run python news_pipeline.py --kafka localhost:9093

# Disable deduplication
uv run python news_pipeline.py --no-dedup

# Get help
uv run python news_pipeline.py --help
```

#### Processing Consumer

```bash
# Process 5 messages then exit
uv run python processing_consumer.py --mode batch --max 5

# Process continuously
uv run python processing_consumer.py --mode continuous

# With custom providers
uv run python processing_consumer.py \
  --translation-provider gemini \
  --tts-provider elevenlabs

# With custom Kafka
uv run python processing_consumer.py --kafka localhost:9093

# Get help
uv run python processing_consumer.py --help
```

#### API Server

```bash
# Default (port 8000)
uv run python main.py

# Custom port
PORT=9000 uv run python main.py

# With auto-reload (development)
uv run uvicorn main:app --reload --port 8000

# Production mode
ENVIRONMENT=production uv run python main.py
```

### Access Points

Once running:

- 🎨 **Frontend**: http://localhost:3000
- 🔌 **API**: http://localhost:8000
- 📚 **API Docs** (Swagger): http://localhost:8000/docs
- 📖 **API Docs** (ReDoc): http://localhost:8000/redoc
- 📊 **Kafka UI**: http://localhost:8080

---

## 💻 Development Workflow

### Working with uv

#### Adding New Packages

```bash
# Add production dependency
uv add fastapi

# Add with version constraint
uv add "fastapi>=0.100.0"

# Add dev dependency
uv add --dev pytest

# Add multiple packages
uv add requests beautifulsoup4 lxml

# Add from specific index
uv add --index-url https://pypi.org/simple package-name
```

#### Removing Packages

```bash
# Remove package
uv remove package-name

# Remove dev dependency
uv remove --dev pytest-mock
```

#### Updating Dependencies

```bash
# Update specific package
uv pip install --upgrade package-name

# Update all packages (regenerate lock)
uv sync --upgrade

# Check for outdated packages
uv pip list --outdated

# Show what would be updated
uv pip list --outdated --format json
```

#### Lock File Management

```bash
# Generate/update lock file
uv lock

# Install from lock file (reproducible)
uv sync --frozen

# Verify lock file is up to date
uv lock --check
```

### Running Scripts with uv

```bash
# Run any Python script
uv run python script.py

# Run with arguments
uv run python news_pipeline.py --mode once

# Run module
uv run python -m pytest

# Run with specific Python version
uv run --python 3.13 python script.py

# Run without activation
# (uv handles virtual environment automatically)
uv run pytest tests/
```

### Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=services --cov=models

# Run specific test file
uv run pytest tests/test_models.py

# Run specific test
uv run pytest tests/test_models.py::TestNewsItem::test_create_news_item

# Run with verbose output
uv run pytest -v

# Run fast tests only
uv run pytest -m unit

# Using test script
chmod +x run_tests.sh
./run_tests.sh unit
./run_tests.sh integration
./run_tests.sh coverage
```

### Code Quality

```bash
# Format code
uv run black .
uv run isort .

# Lint code
uv run flake8
uv run pylint services/

# Type checking (if mypy is installed)
uv run mypy services/

# Run all checks
uv run black . && uv run isort . && uv run flake8
```

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/add-new-language

# Make changes...

# Run tests before commit
./run_tests.sh unit

# Format code
uv run black . && uv run isort .

# Commit
git add .
git commit -m "feat: add Spanish language support"

# Push
git push origin feature/add-new-language
```

---

## 🔧 Troubleshooting

### uv Issues

#### Installation Problems

```bash
# Verify uv is in PATH
which uv
echo $PATH

# Add to PATH manually (Linux/macOS)
export PATH="$HOME/.cargo/bin:$PATH"
# Add to ~/.bashrc or ~/.zshrc permanently

# Reinstall uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Update uv
uv self update
```

#### Virtual Environment Issues

```bash
# Remove and recreate virtual environment
rm -rf .venv
uv venv

# Activate
source .venv/bin/activate  # or .venv\Scripts\activate

# Verify
which python  # Should point to .venv

# Reinstall dependencies
uv sync
```

#### Package Installation Failures

```bash
# Clear uv cache
uv cache clean

# Try installing with verbose output
uv pip install -v package-name

# Install with no cache
uv pip install --no-cache package-name

# Check for conflicts
uv pip check

# Reinstall all dependencies
rm -rf .venv
uv venv
uv sync --reinstall
```

### Docker Issues

```bash
# Docker not running
sudo systemctl start docker  # Linux
# Or start Docker Desktop (macOS/Windows)

# Ports already in use
lsof -i :6379  # Check Redis
lsof -i :9093  # Check Kafka
kill -9 <PID>  # Kill conflicting process

# Services not starting
docker-compose down -v  # Remove volumes
docker-compose up -d

# View detailed logs
docker-compose logs --tail=100 -f kafka

# Container keeps restarting
docker-compose ps
docker-compose logs <service-name>

# Out of disk space
docker system prune -a  # Clean up
```

### API Connection Issues

```bash
# Test Gemini API
curl -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Hello"}]}]}' \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=YOUR_KEY"

# Test ElevenLabs API
curl -H "xi-api-key: YOUR_KEY" \
  "https://api.elevenlabs.io/v1/voices"

# If 401 Unauthorized:
# - Check API key is correct
# - Verify key is active in dashboard
# - Check for trailing spaces in .env
```

### Import Errors

```bash
# Module not found
uv pip list | grep module-name  # Check if installed
uv pip install module-name

# Wrong Python version
python --version  # Should be 3.13.x
which python  # Should be in .venv

# Reinstall from scratch
rm -rf .venv
uv venv
uv sync

# Clear Python cache
find . -type d -name "__pycache__" -exec rm -r {} +
find . -type f -name "*.pyc" -delete
```

### Redis Connection Errors

```bash
# Check Redis is running
docker ps | grep redis

# Test connection
docker exec -it news_redis redis-cli ping
# Should return: PONG

# Check Redis logs
docker-compose logs redis

# Restart Redis
docker-compose restart redis

# Connect manually
docker exec -it news_redis redis-cli
# Then: PING, GET config:languages, etc.
```

### Kafka Issues

```bash
# Kafka not ready (wait 30 seconds)
docker-compose logs kafka | grep "started"

# Check Kafka UI
open http://localhost:8080

# List topics
docker exec -it news_kafka kafka-topics \
  --bootstrap-server localhost:9092 --list

# Describe topic
docker exec -it news_kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --describe --topic raw-news-feed

# Reset Kafka
docker-compose down -v
docker-compose up -d
# Wait 30 seconds for startup
```

---

## 🧹 Cleanup

### Quick Cleanup

```bash
# Stop services
docker-compose down

# Deactivate virtual environment
deactivate

# Clear logs
rm -rf logs/*

# Clear audio files
rm -rf audio_output/*
```

### Full Reset

```bash
# Stop and remove Docker containers
docker-compose down -v

# Remove Docker images (optional)
docker system prune -a

# Remove virtual environment
rm -rf .venv

# Remove generated files
rm -rf logs/* audio_output/* test_audio_output/*
rm -rf .pytest_cache/ htmlcov/ .coverage
rm -rf **/__pycache__ **/*.pyc

# Recreate environment
uv venv
source .venv/bin/activate
uv sync

# Restart Docker
docker-compose up -d
```

---

## 📚 Next Steps

After successful setup:

1. ✅ **Run Tests**: `./run_tests.sh unit`
2. 📝 **Read Documentation**: Check `docs/` folder
3. 🎨 **Customize**: Edit `config/sources.yaml` for RSS feeds
4. 🌐 **Add Languages**: Run `scripts/add_language.py`
5. 🚀 **Deploy**: Follow `docs/DEPLOYMENT.md`

---

## 🆘 Getting Help

1. **Check Documentation**
   - README.md for overview
   - TESTING.md for testing guide
   - DEPLOYMENT.md for production

2. **Search Issues**
   - GitHub Issues
   - Stack Overflow

3. **Enable Debug Logging**
   ```bash
   LOG_LEVEL=DEBUG uv run python main.py
   ```

4. **Check Logs**
   ```bash
   tail -f logs/*.log
   ```

---

**Setup complete! 🎉 Now start building amazing features!**

*If you encounter any issues, please open a GitHub issue with:*
- *Your OS and Python version*
- *Error messages*
- *Steps to reproduce*