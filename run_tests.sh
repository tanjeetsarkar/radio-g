#!/bin/bash
# Test runner script
# Usage: ./run_tests.sh [options]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "NEWS AGGREGATOR TEST SUITE"
echo "========================================="
echo ""

# Parse arguments
TEST_TYPE="${1:-all}"
COVERAGE="${2:-true}"

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}⚠ Warning: No virtual environment detected${NC}"
    echo "Consider activating your virtual environment first:"
    echo "  source venv/bin/activate"
    echo ""
fi

# Create logs directory
mkdir -p logs

# Function to run tests
run_tests() {
    local marker="$1"
    local description="$2"
    
    echo -e "${GREEN}Running $description...${NC}"
    
    if [ "$COVERAGE" = "true" ]; then
        pytest -m "$marker" -v --cov --cov-report=term-missing
    else
        pytest -m "$marker" -v
    fi
}

# Check Docker services
check_docker_services() {
    echo "Checking Docker services..."
    
    if ! docker ps | grep -q "news_redis"; then
        echo -e "${YELLOW}⚠ Redis is not running${NC}"
        echo "Start with: docker-compose up -d redis"
        echo ""
    else
        echo -e "${GREEN}✓ Redis is running${NC}"
    fi
    
    if ! docker ps | grep -q "news_kafka"; then
        echo -e "${YELLOW}⚠ Kafka is not running${NC}"
        echo "Start with: docker-compose up -d"
        echo ""
    else
        echo -e "${GREEN}✓ Kafka is running${NC}"
    fi
    
    echo ""
}

# Run based on test type
case $TEST_TYPE in
    "unit")
        echo "Running UNIT tests only (no external dependencies)..."
        run_tests "unit" "Unit Tests"
        ;;
    
    "integration")
        echo "Running INTEGRATION tests (requires Docker services)..."
        check_docker_services
        run_tests "integration" "Integration Tests"
        ;;
    
    "kafka")
        echo "Running KAFKA tests..."
        check_docker_services
        run_tests "kafka" "Kafka Tests"
        ;;
    
    "redis")
        echo "Running REDIS tests..."
        check_docker_services
        run_tests "redis" "Redis Tests"
        ;;
    
    "mock")
        echo "Running MOCK service tests..."
        run_tests "mock" "Mock Service Tests"
        ;;
    
    "fast")
        echo "Running FAST tests (unit + mock)..."
        run_tests "unit or mock" "Fast Tests"
        ;;
    
    "slow")
        echo "Running SLOW tests..."
        check_docker_services
        run_tests "slow" "Slow Tests"
        ;;
    
    "all")
        echo "Running ALL tests..."
        check_docker_services
        
        if [ "$COVERAGE" = "true" ]; then
            pytest -v --cov --cov-report=html --cov-report=term-missing --cov-report=xml
        else
            pytest -v
        fi
        ;;
    
    "coverage")
        echo "Running tests with detailed coverage report..."
        pytest -v --cov --cov-report=html --cov-report=term-missing
        echo ""
        echo -e "${GREEN}✓ Coverage report generated at: htmlcov/index.html${NC}"
        ;;
    
    *)
        echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
        echo ""
        echo "Usage: ./run_tests.sh [test_type] [coverage]"
        echo ""
        echo "Test types:"
        echo "  unit        - Unit tests only (fast, no Docker)"
        echo "  integration - Integration tests (requires Docker)"
        echo "  kafka       - Kafka-related tests"
        echo "  redis       - Redis-related tests"
        echo "  mock        - Mock service tests"
        echo "  fast        - Fast tests (unit + mock)"
        echo "  slow        - Slow tests"
        echo "  all         - All tests (default)"
        echo "  coverage    - All tests with HTML coverage report"
        echo ""
        echo "Coverage: true (default) | false"
        echo ""
        echo "Examples:"
        echo "  ./run_tests.sh unit"
        echo "  ./run_tests.sh integration false"
        echo "  ./run_tests.sh coverage"
        exit 1
        ;;
esac

echo ""
echo "========================================="
echo -e "${GREEN}✓ Tests completed!${NC}"
echo "========================================="

# Show coverage summary if generated
if [ -f ".coverage" ] && [ "$COVERAGE" = "true" ]; then
    echo ""
    echo "Coverage Summary:"
    coverage report --skip-empty
fi

echo ""
echo "Log files available in: logs/"
echo ""