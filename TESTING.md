# Testing Guide

## 🧪 Test Suite Overview

The project uses **pytest** for comprehensive testing with file-based logging.

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── test_models.py           # Model unit tests
├── test_deduplicator.py     # Deduplication service tests
├── test_kafka_services.py   # Kafka producer/consumer tests
├── test_translation_tts.py  # Translation & TTS service tests
└── test_pipelines.py        # End-to-end pipeline tests (future)
```

### Test Categories

Tests are organized with **markers**:

- `@pytest.mark.unit` - Fast unit tests, no external dependencies
- `@pytest.mark.integration` - Integration tests requiring Docker services
- `@pytest.mark.kafka` - Tests requiring Kafka
- `@pytest.mark.redis` - Tests requiring Redis
- `@pytest.mark.mock` - Tests using mock services only
- `@pytest.mark.slow` - Slow-running tests

## 🚀 Quick Start

### 1. Install Test Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Docker Services (for integration tests)

```bash
# Start Redis and Kafka
docker-compose up -d

# Verify services
docker-compose ps
```

### 3. Run Tests

```bash
# Run all tests
./run_tests.sh all

# Run only unit tests (no Docker needed)
./run_tests.sh unit

# Run only integration tests
./run_tests.sh integration

# Run with detailed coverage report
./run_tests.sh coverage
```

## 📝 Detailed Test Commands

### By Test Type

```bash
# Unit tests only (fastest)
pytest -m unit -v

# Integration tests (requires Docker)
pytest -m integration -v

# Mock service tests
pytest -m mock -v

# Kafka-specific tests
pytest -m kafka -v

# Redis-specific tests
pytest -m redis -v
```

### By Module

```bash
# Test specific module
pytest tests/test_models.py -v

# Test specific class
pytest tests/test_deduplicator.py::TestNewsDeduplicator -v

# Test specific function
pytest tests/test_models.py::TestNewsItem::test_create_news_item -v
```

### With Coverage

```bash
# Run with coverage
pytest --cov=services --cov=models --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Parallel Execution (faster)

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel
pytest -n auto
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
pytest --cov --cov-report=html

# Terminal report
pytest --cov --cov-report=term-missing

# XML report (for CI/CD)
pytest --cov --cov-report=xml
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
# Watch logs in real-time
tail -f logs/*.log

# View specific service logs
tail -f logs/kafka_producer.log
```

## 🐛 Debugging Failed Tests

### 1. Run Single Test with Verbose Output

```bash
pytest tests/test_kafka_services.py::TestKafkaProducer::test_produce_single_message -vv -s
```

### 2. Show Print Statements

```bash
# Show print() output
pytest -s

# Show captured logs
pytest --log-cli-level=DEBUG
```

### 3. Stop on First Failure

```bash
pytest -x  # Stop on first failure
pytest --maxfail=3  # Stop after 3 failures
```

### 4. Run Last Failed Tests

```bash
pytest --lf  # Run last failed
pytest --ff  # Run failed first, then others
```

### 5. Check Logs

```bash
# Check test run logs
cat logs/kafka_producer.log

# Search for errors
grep ERROR logs/*.log
```

## 🔧 Writing New Tests

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
```

### Using Fixtures

```python
@pytest.mark.integration
@pytest.mark.redis
def test_with_redis(redis_deduplicator, sample_news_item):
    """Test using Redis fixture"""
    result = redis_deduplicator.mark_as_seen(sample_news_item)
    assert result is True
```

### Mock External APIs

```python
@pytest.mark.unit
def test_with_mock(mocker):
    """Test with mocked dependency"""
    mock_api = mocker.patch('services.external_api.call')
    mock_api.return_value = {'status': 'ok'}
    
    # Your test code
```

## 🎯 Best Practices

### 1. Test Naming

```python
# ✅ Good: Descriptive names
def test_producer_delivers_message_to_kafka():
    pass

# ❌ Bad: Vague names
def test_kafka():
    pass
```

### 2. Test Independence

```python
# ✅ Good: Each test is independent
def test_create_user():
    user = create_user("test")
    assert user.name == "test"

# ❌ Bad: Tests depend on each other
def test_step_1():
    global user
    user = create_user()

def test_step_2():
    assert user.name == "test"  # Depends on test_step_1
```

### 3. Use Fixtures for Setup

```python
# ✅ Good: Use fixtures
@pytest.fixture
def sample_data():
    return {"key": "value"}

def test_with_fixture(sample_data):
    assert sample_data["key"] == "value"

# ❌ Bad: Setup in every test
def test_without_fixture():
    data = {"key": "value"}  # Repeated setup
    assert data["key"] == "value"
```

### 4. Test Edge Cases

```python
def test_with_empty_input():
    result = process([])
    assert result == []

def test_with_none_input():
    with pytest.raises(ValueError):
        process(None)

def test_with_large_input():
    large_data = ["item"] * 10000
    result = process(large_data)
    assert len(result) == 10000
```

## 🚨 Troubleshooting

### Redis Connection Failed

```bash
# Check if Redis is running
docker-compose ps redis

# Start Redis
docker-compose up -d redis

# Check logs
docker-compose logs redis
```

### Kafka Connection Failed

```bash
# Check if Kafka is running
docker-compose ps kafka

# Kafka takes ~30 seconds to start
docker-compose logs -f kafka | grep "started"

# Restart Kafka
docker-compose restart kafka zookeeper
```

### Tests Hanging

```bash
# Set timeout for tests
pytest --timeout=30

# Kill hanging processes
pkill -f pytest
```

### Port Already in Use

```bash
# Find process using port
lsof -i :6379  # Redis
lsof -i :9093  # Kafka

# Kill process
kill -9 <PID>
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
      
      kafka:
        image: confluentinc/cp-kafka:7.5.0
        ports:
          - 9093:9093
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Run tests
        run: |
          pytest --cov --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## 📚 Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest Fixtures](https://docs.pytest.org/en/latest/fixture.html)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Testing Best Practices](https://docs.pytest.org/en/latest/goodpractices.html)

## 🆘 Need Help?

1. Check the logs: `tail -f logs/*.log`
2. Run with verbose output: `pytest -vv -s`
3. Check Docker services: `docker-compose ps`
4. View test coverage: `open htmlcov/index.html`