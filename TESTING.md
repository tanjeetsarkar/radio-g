# Testing Guide

## 🧪 Test Suite Overview

The project uses **pytest** for comprehensive testing with **uv** as the package manager.

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── test_models.py           # Model unit tests
├── test_deduplicator.py     # Deduplication service tests  
├── test_kafka_services.py   # Kafka producer/consumer tests
├── test_fetcher.py          # News fetcher tests
├── test_translation_tts.py  # Translation & TTS service tests
├── test_processing.py       # Processing consumer tests
└── test_kafka_pipeline.py   # End-to-end pipeline tests
```

### Test Categories

Tests are organized with **markers**:

- `@pytest.mark.unit` - Fast unit tests, no external dependencies
- `@pytest.mark.integration` - Integration tests requiring Docker services
- `@pytest.mark.slow` - Slow tests
- `@pytest.mark.kafka` - Tests requiring Kafka
- `@pytest.mark.redis` - Tests requiring Redis
- `@pytest.mark.mock` - Tests using mock services only

## 🚀 Quick Start

### 1. Install Test Dependencies

```bash
# Activate virtual environment
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install all dependencies including test packages
uv sync

# Or install test dependencies specifically
uv pip install -r requirements.txt

# Or install individually
uv add --dev pytest pytest-cov pytest-asyncio pytest-mock pytest-timeout
```

### 2. Start Docker Services (for integration tests)

```bash
# Start Redis and Kafka
docker compose up -d

# Verify services
docker compose ps

# Wait for Kafka to be ready (~30 seconds)
docker compose logs kafka | grep "started"
```

### 3. Run Tests

**Using the test script:**
```bash
# Make executable (first time only)
chmod +x run_tests.sh

# Run all tests
./run_tests.sh all

# Run only unit tests (no Docker needed)
./run_tests.sh unit

# Run only integration tests
./run_tests.sh integration

# Run with coverage report
./run_tests.sh coverage
```

**Using uv directly:**
```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=services --cov=models

# Run specific test file
uv run pytest tests/test_models.py -v
```

## 📝 Detailed Test Commands

### By Test Type

```bash
# Unit tests only (fastest, no Docker)
uv run pytest -m unit -v

# Integration tests (requires Docker)
uv run pytest -m integration -v

# Mock service tests
uv run pytest -m mock -v

# Kafka-specific tests
uv run pytest -m kafka -v

# Redis-specific tests
uv run pytest -m redis -v

# Slow tests only
uv run pytest -m slow -v
```

### By Module

```bash
# Test specific module
uv run pytest tests/test_models.py -v

# Test specific class
uv run pytest tests/test_deduplicator.py::TestNewsDeduplicator -v

# Test specific function
uv run pytest tests/test_models.py::TestNewsItem::test_create_news_item -v

# Test multiple files
uv run pytest tests/test_models.py tests/test_fetcher.py -v
```

### With Coverage

```bash
# Run with coverage
uv run pytest --cov=services --cov=models --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows

# Coverage with missing lines
uv run pytest --cov=services --cov=models --cov-report=term-missing

# Coverage with XML output (for CI/CD)
uv run pytest --cov=services --cov=models --cov-report=xml
```

### Parallel Execution (faster)

```bash
# Install pytest-xdist
uv add --dev pytest-xdist

# Run tests in parallel (auto-detect CPU cores)
uv run pytest -n auto

# Run with specific number of workers
uv run pytest -n 4
```

### Test with Different Python Versions

```bash
# Test with specific Python version
uv run --python 3.13 pytest

# Test with multiple Python versions (if installed)
uv run --python 3.12 pytest
uv run --python 3.13 pytest
```

## 🔍 Test Coverage

### Current Coverage Targets

- **Models**: >90% coverage
- **Services**: >80% coverage  
- **Integration**: >70% coverage
- **Overall**: >75% coverage

### Generate Coverage Report

```bash
# HTML report
uv run pytest --cov --cov-report=html

# Terminal report with missing lines
uv run pytest --cov --cov-report=term-missing

# XML report (for CI/CD integration)
uv run pytest --cov --cov-report=xml

# JSON report
uv run pytest --cov --cov-report=json

# Multiple formats at once
uv run pytest --cov --cov-report=html --cov-report=term-missing --cov-report=xml
```

### View Coverage

```bash
# View HTML report
open htmlcov/index.html

# View coverage summary in terminal
uv run coverage report

# View detailed report
uv run coverage report -m

# Show only files with <100% coverage
uv run coverage report --skip-covered
```

## 📊 Logging During Tests

All services use **file-based logging** during tests:

```
logs/
├── news_fetcher.log        # News fetcher logs
├── content_scraper.log     # Content scraper logs
├── deduplicator.log        # Deduplication logs
├── kafka_producer.log      # Kafka producer logs
├── kafka_consumer.log      # Kafka consumer logs
├── translation.log         # Translation service logs
├── tts.log                 # TTS service logs
├── pipeline.log            # Pipeline logs
└── processing.log          # Processing consumer logs
```

### View Logs During Testing

```bash
# Watch all logs in real-time
tail -f logs/*.log

# Watch specific service logs
tail -f logs/kafka_producer.log

# Search for errors
grep ERROR logs/*.log

# Search for specific test
grep "test_produce_single_message" logs/*.log
```

## 🐛 Debugging Failed Tests

### 1. Run Single Test with Verbose Output

```bash
# Run with maximum verbosity
uv run pytest tests/test_kafka_services.py::TestKafkaProducer::test_produce_single_message -vv -s

# Show print() output
uv run pytest -s

# Show captured logs
uv run pytest --log-cli-level=DEBUG
```

### 2. Stop on First Failure

```bash
# Stop on first failure
uv run pytest -x

# Stop after N failures
uv run pytest --maxfail=3

# Run only last failed tests
uv run pytest --lf

# Run failed first, then others
uv run pytest --ff
```

### 3. Debug with pdb

```bash
# Drop into debugger on failure
uv run pytest --pdb

# Drop into debugger on error
uv run pytest --pdb --pdbcls=IPython.terminal.debugger:TerminalPdb
```

### 4. Increase Test Timeout

```bash
# Set timeout for all tests (in seconds)
uv run pytest --timeout=30

# Disable timeout for specific tests
uv run pytest --timeout=0
```

### 5. Check Logs

```bash
# Check test run logs
cat logs/kafka_producer.log

# Search for errors
grep ERROR logs/*.log

# View last 100 lines
tail -100 logs/pipeline.log

# Follow logs during test run
tail -f logs/*.log & uv run pytest
```

## 🔧 Writing New Tests with uv

### Test Template

```python
import pytest
from services.your_service import YourService


@pytest.mark.unit
class TestYourService:
    """Test your service"""
    
    def test_something(self, sample_fixture):
        """Test description"""
        # Arrange
        service = YourService()
        
        # Act
        result = service.do_something()
        
        # Assert
        assert result is not None
        assert result.status == "success"
```

### Using Fixtures

```python
@pytest.mark.integration
@pytest.mark.redis
def test_with_redis(redis_deduplicator, sample_news_item):
    """Test using Redis fixture"""
    result = redis_deduplicator.mark_as_seen(sample_news_item)
    assert result is True
    
    # Verify it's marked as duplicate
    is_dup = redis_deduplicator.is_duplicate(sample_news_item)
    assert is_dup is True
```

### Mock External APIs

```python
@pytest.mark.unit
def test_with_mock(mocker):
    """Test with mocked dependency"""
    # Mock external API call
    mock_api = mocker.patch('services.external_api.call')
    mock_api.return_value = {'status': 'ok', 'data': 'test'}
    
    # Your test code
    service = YourService()
    result = service.fetch_data()
    
    assert result['status'] == 'ok'
    mock_api.assert_called_once()
```

### Parametrized Tests

```python
@pytest.mark.parametrize("language,expected", [
    ("en", "Hello"),
    ("hi", "नमस्ते"),
    ("bn", "হ্যালো"),
])
def test_greetings(language, expected):
    """Test greetings in multiple languages"""
    result = get_greeting(language)
    assert expected in result
```

## 🎯 Best Practices

### 1. Test Naming

```python
# ✅ Good: Descriptive names
def test_producer_delivers_message_to_kafka():
    pass

def test_consumer_handles_invalid_json():
    pass

# ❌ Bad: Vague names
def test_kafka():
    pass

def test_1():
    pass
```

### 2. Test Independence

```python
# ✅ Good: Each test is independent
def test_create_user():
    user = create_user("test")
    assert user.name == "test"

def test_delete_user():
    user = create_user("test")
    result = delete_user(user.id)
    assert result is True

# ❌ Bad: Tests depend on each other
def test_step_1():
    global user
    user = create_user("test")

def test_step_2():
    assert user.name == "test"  # Depends on test_step_1
```

### 3. Use Fixtures for Setup

```python
# ✅ Good: Use fixtures
@pytest.fixture
def sample_data():
    return {"key": "value", "count": 10}

def test_with_fixture(sample_data):
    assert sample_data["key"] == "value"
    assert sample_data["count"] == 10

# ❌ Bad: Setup in every test
def test_without_fixture():
    data = {"key": "value", "count": 10}  # Repeated
    assert data["key"] == "value"
```

### 4. Test Edge Cases

```python
def test_with_empty_input():
    """Test with empty list"""
    result = process([])
    assert result == []

def test_with_none_input():
    """Test with None input"""
    with pytest.raises(ValueError):
        process(None)

def test_with_large_input():
    """Test with large dataset"""
    large_data = ["item"] * 10000
    result = process(large_data)
    assert len(result) == 10000

def test_with_special_characters():
    """Test with special characters"""
    result = process("Hello 世界 🌍")
    assert "Hello" in result
```

### 5. Use Context Managers

```python
def test_file_operations(tmp_path):
    """Test file operations with temporary directory"""
    file_path = tmp_path / "test.txt"
    
    # Write
    with open(file_path, 'w') as f:
        f.write("test data")
    
    # Read
    with open(file_path, 'r') as f:
        content = f.read()
    
    assert content == "test data"
```

## 🚨 Troubleshooting

### uv Test Execution Issues

```bash
# Clear pytest cache
uv run pytest --cache-clear

# Reinstall test dependencies
uv pip install --force-reinstall pytest pytest-cov

# Check pytest is installed
uv pip show pytest
```

### Redis Connection Failed

```bash
# Check if Redis is running
docker compose ps redis

# Start Redis
docker compose up -d redis

# Check logs
docker compose logs redis

# Test connection manually
docker exec -it news_redis redis-cli ping
```

### Kafka Connection Failed

```bash
# Check if Kafka is running
docker compose ps kafka

# Kafka takes ~30 seconds to start
docker compose logs -f kafka | grep "started"

# Restart Kafka
docker compose restart kafka zookeeper

# Clear Kafka data (if corrupted)
docker compose down -v
docker compose up -d
```

### Tests Hanging

```bash
# Run with timeout
uv run pytest --timeout=30

# Run specific test with timeout
uv run pytest tests/test_file.py --timeout=10

# Kill hanging processes
pkill -f pytest

# Or use process ID
ps aux | grep pytest
kill -9 <PID>
```

### Port Already in Use

```bash
# Find process using port
lsof -i :6379  # Redis
lsof -i :9093  # Kafka

# Kill process
kill -9 <PID>

# Or stop Docker services
docker compose down
```

### Import Errors

```bash
# Reinstall dependencies
uv sync --reinstall

# Check Python path
uv run python -c "import sys; print('\n'.join(sys.path))"

# Verify package installation
uv pip list | grep pytest

# Clear Python cache
find . -type d -name "__pycache__" -exec rm -r {} +
find . -type f -name "*.pyc" -delete
```

### Permission Errors

```bash
# Fix test script permissions
chmod +x run_tests.sh

# Fix log directory permissions
chmod -R 755 logs/

# Fix audio directory permissions
chmod -R 755 audio_output/
```

## 📈 CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      kafka:
        image: confluentinc/cp-kafka:7.5.0
        ports:
          - 9093:9093
        env:
          KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
          KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9093
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      
      - name: Set up Python
        run: uv venv && source .venv/bin/activate
      
      - name: Install dependencies
        run: uv sync
      
      - name: Run unit tests
        run: uv run pytest -m unit --cov --cov-report=xml
      
      - name: Run integration tests
        run: uv run pytest -m integration --cov --cov-report=xml --cov-append
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

### GitLab CI Example

```yaml
test:
  image: python:3.13
  
  services:
    - redis:7-alpine
    - confluentinc/cp-kafka:7.5.0
  
  before_script:
    - curl -LsSf https://astral.sh/uv/install.sh | sh
    - export PATH="$HOME/.cargo/bin:$PATH"
    - uv venv
    - source .venv/bin/activate
    - uv sync
  
  script:
    - uv run pytest --cov --cov-report=xml
  
  coverage: '/TOTAL.*\s+(\d+%)$/'
  
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
```

## 📚 Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest Fixtures](https://docs.pytest.org/en/latest/fixture.html)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [uv Documentation](https://docs.astral.sh/uv/)
- [Testing Best Practices](https://docs.pytest.org/en/latest/goodpractices.html)

## 🆘 Need Help?

1. Check the logs: `tail -f logs/*.log`
2. Run with verbose output: `uv run pytest -vv -s`
3. Check Docker services: `docker compose ps`
4. View coverage report: `open htmlcov/index.html`
5. Review test fixtures: `uv run pytest --fixtures`
6. Debug with pdb: `uv run pytest --pdb`

---

**Happy Testing! 🧪 Ensure all tests pass before deploying to production.**