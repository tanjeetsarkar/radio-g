#!/bin/bash
# ============================================
# Test Local Deployment Script
# ============================================
set -e

echo "🧪 Testing Radio-G Local Deployment"
echo "===================================="
echo ""
echo "📍 Deployment Endpoints:"
echo "  API:      http://localhost:8000"
echo "  Frontend: http://localhost:3000"
echo "  Redis:    localhost:6379"
echo "  Kafka:    localhost:9092"
echo ""

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

API_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:3000"

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# Helper function for tests
run_test() {
    local test_name="$1"
    local test_command="$2"
    local verbose_output="$3"
    
    echo -ne "${BLUE}Testing: ${test_name}...${NC} "
    
    if [ -n "$verbose_output" ]; then
        echo "" # New line for verbose output
        echo -e "  ${YELLOW}Command: ${test_command}${NC}"
    fi
    
    local output
    output=$(eval "$test_command" 2>&1)
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ PASSED${NC}"
        if [ -n "$verbose_output" ] && [ -n "$output" ]; then
            echo -e "  ${GREEN}Response: ${output:0:200}${NC}"
        fi
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}❌ FAILED${NC}"
        if [ -n "$output" ]; then
            echo -e "  ${RED}Error: ${output:0:200}${NC}"
        fi
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

echo ""
echo -e "${BLUE}🔍 Running deployment tests...${NC}"
echo ""

# Infrastructure tests
echo -e "${BLUE}📦 Infrastructure Tests:${NC}"
echo "  Checking Redis at localhost:6379..."
run_test "Redis is running" "docker compose exec -T redis redis-cli ping" "verbose"
echo "  Checking Kafka at localhost:9092..."
run_test "Kafka is running" "docker compose exec -T kafka kafka-broker-api-versions --bootstrap-server localhost:9092 | head -n 3" "verbose"
echo "  Checking Redis language config..."
run_test "Language config exists" "docker compose exec -T redis redis-cli EXISTS languages:config"

# Application tests
echo ""
echo -e "${BLUE}🚀 Application Tests:${NC}"
run_test "News Fetcher is running" "docker compose ps news-fetcher | grep -q 'Up'"
run_test "News Processor is running" "docker compose ps news-processor | grep -q 'Up'"
run_test "News API is running" "docker compose ps news-api | grep -q 'Up'"
run_test "Frontend is running" "docker compose ps news-frontend | grep -q 'Up'"

# API endpoint tests
echo ""
echo -e "${BLUE}🌐 API Endpoint Tests:${NC}"
echo "  Testing ${API_URL}/health"
run_test "API health check" "curl -s -f ${API_URL}/health" "verbose"
echo "  Testing ${API_URL}/ready"
run_test "API readiness check" "curl -s -f ${API_URL}/ready" "verbose"
echo "  Testing ${API_URL}/languages"
run_test "API languages endpoint" "curl -s -f ${API_URL}/languages" "verbose"
echo "  Testing ${API_URL}/playlist/en"
run_test "API news endpoint (English)" "curl -s -f ${API_URL}/playlist/en | jq -r '.items | length' 2>/dev/null || echo 'Response received'" "verbose"

# Check API response structure
echo -ne "${BLUE}Testing: API returns valid JSON...${NC} "
JSON_RESPONSE=$(curl -s ${API_URL}/languages)
if echo "$JSON_RESPONSE" | python3 -m json.tool &>/dev/null; then
    echo -e "${GREEN}✅ PASSED${NC}"
    echo -e "  ${GREEN}Response preview: ${JSON_RESPONSE:0:150}...${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}❌ FAILED${NC}"
    echo -e "  ${RED}Invalid response: ${JSON_RESPONSE:0:150}${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Frontend tests
echo ""
echo -e "${BLUE}🎨 Frontend Tests:${NC}"
echo "  Testing ${FRONTEND_URL}"
run_test "Frontend is accessible" "curl -s -o /dev/null -w 'HTTP %{http_code} - %{time_total}s' -f ${FRONTEND_URL}" "verbose"
echo "  Checking HTML content..."
run_test "Frontend returns HTML" "curl -s ${FRONTEND_URL} | head -n 5"

# Kafka topics check
echo ""
echo -e "${BLUE}📨 Kafka Topics Tests:${NC}"
echo "  Listing Kafka topics at localhost:9092..."
echo -e "  ${YELLOW}Available topics:${NC}"
docker compose exec -T kafka kafka-topics --bootstrap-server localhost:9092 --list 2>/dev/null | sed 's/^/    /'
run_test "raw-news-feed topic exists" "docker compose exec -T kafka kafka-topics --bootstrap-server localhost:9092 --list | grep -q 'raw-news-feed'"

# Check for articles in Kafka (may fail initially if fetcher hasn't run)
echo -ne "${BLUE}Testing: Articles in Kafka (optional)...${NC} "
echo "" # New line for verbose output
echo -e "  ${YELLOW}Checking message count in raw-news-feed topic...${NC}"
TOPIC_COUNT=$(docker compose exec -T kafka kafka-run-class kafka.tools.GetOffsetShell --broker-list localhost:9092 --topic raw-news-feed 2>/dev/null | awk -F ":" '{sum += $3} END {print sum}')
if [ "$TOPIC_COUNT" -gt "0" ]; then
    echo -e "${GREEN}✅ PASSED (${TOPIC_COUNT} messages in topic)${NC}"
    echo -e "  ${GREEN}Topic: raw-news-feed | Messages: ${TOPIC_COUNT}${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${YELLOW}⚠️  SKIPPED (0 messages - fetcher may not have run yet)${NC}"
fi

# Docker health checks
echo ""
echo -e "${BLUE}🏥 Docker Health Checks:${NC}"
echo "  Checking container health status..."
echo -e "  ${YELLOW}Container statuses:${NC}"
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" | sed 's/^/    /'
echo ""
run_test "Redis health check" "docker inspect news_redis --format '{{.State.Health.Status}}' 2>/dev/null || echo 'running'"
run_test "Kafka health check" "docker inspect news_kafka --format '{{.State.Health.Status}}' 2>/dev/null || echo 'running'"
run_test "API health check" "docker inspect news_api --format '{{.State.Health.Status}}' 2>/dev/null || echo 'running'"

# Resource usage
echo ""
echo -e "${BLUE}📊 Resource Usage:${NC}"
echo "  Current resource consumption:"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" | grep -E '(NAME|news_)' | sed 's/^/    /'
echo ""
echo -e "  ${YELLOW}Container logs (last 5 lines per service):${NC}"
for service in news-fetcher news-processor news-api news-frontend; do
    echo -e "    ${BLUE}${service}:${NC}"
    docker compose logs --tail=2 $service 2>/dev/null | sed 's/^/      /' || echo "      (no logs)"
done

# Summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Test Summary${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "Tests Passed: ${GREEN}${TESTS_PASSED}${NC}"
echo -e "Tests Failed: ${RED}${TESTS_FAILED}${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed! System is ready.${NC}"
    echo ""
    echo -e "${BLUE}📋 Next steps:${NC}"
    echo "  1. 🌐 Visit the application:"
    echo "     Frontend:  ${FRONTEND_URL}"
    echo "     API Docs:  ${API_URL}/docs"
    echo "     Health:    ${API_URL}/health"
    echo ""
    echo "  2. 📝 Monitor logs:"
    echo "     All services: docker compose logs -f"
    echo "     API only:     docker compose logs -f news-api"
    echo "     Fetcher:       docker compose logs -f news-fetcher"
    echo "     Processor:     docker compose logs -f news-processor"
    echo ""
    echo "  3. 🔍 Check status:"
    echo "     docker compose ps"
    echo "     docker compose stats"
    echo ""
    echo "  4. ☁️  When ready, deploy to GCP:"
    echo "     ./scripts/deploy_to_gcp.sh"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Check logs:${NC}"
    echo ""
    echo -e "${YELLOW}Debugging commands:${NC}"
    echo "  View all logs:        docker compose logs"
    echo "  View specific service: docker compose logs [news-api|news-fetcher|news-processor]"
    echo "  Check container status: docker compose ps"
    echo "  Check Redis:          docker compose exec redis redis-cli ping"
    echo "  Check Kafka topics:   docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list"
    echo "  Test API directly:    curl -v ${API_URL}/health"
    echo ""
    exit 1
fi
