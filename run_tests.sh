#!/bin/bash

# NEXNews - Run Tests

echo "=================================="
echo "      Running NEXNews Tests"
echo "=================================="
echo ""

# Check if services are running
if ! docker ps | grep -q nexnews-api; then
    echo "❌ Error: NEXNews services are not running!"
    echo "   Start them first with: ./start.sh"
    exit 1
fi

echo "Running API tests..."
echo ""

# Run pytest inside the API container
docker compose exec api pytest tests/ -v 2>&1

exit_code=$?

echo ""
if [ $exit_code -eq 0 ]; then
    echo "=================================="
    echo "   ✅ All tests passed!"
    echo "=================================="
else
    echo "=================================="
    echo "   ❌ Some tests failed"
    echo "=================================="
fi

exit $exit_code
