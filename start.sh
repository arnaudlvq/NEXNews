#!/bin/bash

# NEXNews - Quick Start Script

echo "=================================="
echo "              NEXNews"
echo "=================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "No .env file found !"
    read -p "Press Enter after you've configured .env (or press Ctrl+C to exit and configure later)..."
fi

echo ""
echo "Starting NEXNews services..."
docker compose up --build -d

echo "..."
sleep 5

echo ""
echo "=================================="
echo "      ✅ NEXNews is running!"
echo "=================================="
echo ""
echo "REST API:"
echo "  Server: http://localhost:8000"
echo "  Docs:   http://localhost:8000/docs"
echo ""
echo "Endpoints:"
echo "  GET  /              - API info & categories"
echo "  POST /news/search   - Search articles"
echo "  GET  /news/{id}     - Get specific article"
echo "  GET  /health        - Health check"
echo "  GET  /stats         - Article statistics"
echo "  GET  /embeddings/stats - Embedding stats"
echo ""
echo "Test commands:"
echo "  curl http://localhost:8000/health"
echo "  curl http://localhost:8000/stats"
echo "  curl -X POST http://localhost:8000/news/search -H 'Content-Type: application/json' -d '{\"prompt\": \"security\"}'"
echo ""
echo "Docker commands:"
echo "  View logs:     docker compose logs -f"
echo "  Stop services: docker compose down"
echo "  Run tests:     docker compose exec api pytest tests/ -v"
echo ""
