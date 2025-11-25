# NEXNews

**AI-powered news aggregation and search API for IT professionals.**

Collects news from RSS feeds → Classifies with GPT-4.1 → Serves via REST API with semantic search.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              NEXNews System                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐      ┌──────────────────────────────────────────────┐     │
│   │ RSS Sources │      │            INGESTOR SERVICE                  │     │
│   │             │      │  ┌───────────┐  ┌────────────┐  ┌─────────┐  │     │
│   │ • R/sysadmin│─────▶│  │ Collector │─▶│ Classifier │─▶│ Embedder│  │     │
│   │ • Ars Tech  │      │  │ (RSS)     │  │ (GPT-4.1)  │  │ (OpenAI)│  │     │
│   │ • Tom's HW  │      │  └───────────┘  └────────────┘  └─────────┘  │     │
│   │             │      │                       │              │       │     │
│   └─────────────┘      └───────────────────────┼──────────────┼───────┘     │
│                                                │              │             │
│                                                ▼              ▼             │
│                                         ┌──────────┐   ┌──────────┐         │
│                                         │  SQLite  │   │ ChromaDB │         │
│                                         │(articles)│   │(vectors) │         │
│                                         └────┬─────┘   └────┬─────┘         │
│                                              │              │               │
│   ┌─────────────┐      ┌─────────────────────┴──────────────┴─────────┐     │
│   │ AI Clients  │      │              API SERVICE                     │     │
│   │             │◀────▶│  POST /news/search  - Semantic search        │     │
│   │ • Chatbots  │      │  GET  /news/{id}    - Get article            │     │
│   │ • Agents    │      │  GET  /health       - Health check           │     │
│   │ • Apps      │      │  GET  /stats        - Statistics             │     │
│   └─────────────┘      └──────────────────────────────────────────────┘     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Prerequisites
- Docker & Docker Compose
- OpenAI API key ([get one here](https://platform.openai.com/))

### 2. Setup
```bash
# Clone and enter directory
git clone git@github.com:arnaudlvq/NEXNews.git
cd NEXNews

# Copy example environment file and add your API key
cp .env.example .env
# Edit .env and replace 'your_openai_api_key_here' with your actual key

# Start everything
./start.sh
```

### 3. Use the API
```bash
# Search for articles about security
curl -X POST http://localhost:8000/news/search \
  -H "Content-Type: application/json" \
  -d '{"prompt": "cybersecurity threats"}'

# Get all AI-related articles
curl -X POST http://localhost:8000/news/search \
  -H "Content-Type: application/json" \
  -d '{"category": "Artificial Intelligence & Emerging Tech"}'

# Get a specific article
curl http://localhost:8000/news/1
```

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/news/search` | POST | Search articles by prompt and/or category |
| `/news/{id}` | GET | Get specific article by ID |
| `/health` | GET | Health check |
| `/stats` | GET | Database & embedding statistics |

### Search Request Body
```json
{
  "prompt": "natural language query",  // optional
  "category": "Cybersecurity",         // optional
  "limit": 20                          // optional, default 20
}
```

### Categories
- `Cybersecurity`
- `Artificial Intelligence & Emerging Tech`
- `Software & Development`
- `Hardware & Devices`
- `Tech Industry & Business`
- `Other`

---

## Project Structure

```
NEXNews/
├── app/
│   ├── __init__.py     # Package init
│   ├── api.py          # REST API endpoints (FastAPI)
│   ├── classifier.py   # GPT-4.1 classification
│   ├── collector.py    # RSS feed collection
│   ├── config.py       # Settings management
│   ├── database.py     # SQLite models (SQLAlchemy)
│   ├── embeddings.py   # Semantic search (ChromaDB + OpenAI)
│   └── logger.py       # Structured logging
├── tests/
│   ├── __init__.py     # Package init
│   └── test_api.py     # API tests (pytest)
├── data/               # Database files (SQLite + ChromaDB)
├── .env.example        # Example environment variables
├── .gitignore          # Git ignore rules
├── docker-compose.yml  # Container orchestration
├── Dockerfile          # Container definition
├── ingestor_start.py   # Background service entry point
├── pytest.ini          # Pytest configuration
├── requirements.txt    # Python dependencies
├── run_tests.sh        # Test runner
└── start.sh            # Quick start script
```

---

## How It Works

### 1. Collection (every 10 minutes)
The **Ingestor** fetches articles from RSS feeds:
- Reddit r/sysadmin
- Ars Technica
- Hacker News
- Tom's Hardware

### 2. Classification
Each article is sent to **GPT-4.1** with a structured prompt. The model returns:
- Category (from predefined list)
- Confidence level

### 3. Embedding
Article text is converted to a **1536-dimension vector** using OpenAI's embedding model, stored in ChromaDB for semantic search.

### 4. Search
When you search:
- **With prompt**: Semantic search using vector similarity
- **With category**: Direct database filter
- **Both**: Semantic search filtered by category

---

## Testing

```bash
# Run all tests
./run_tests.sh

# Expected output
======================== 13 passed in 2.37s ========================
```

Tests cover:
- Health endpoint
- Statistics endpoint
- Article retrieval
- Search functionality (prompt, category, validation)
- Error handling (404, invalid input)

---

## Configuration

Environment variables (`.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | - | Required for AI features |
| `INGESTOR_INTERVAL_MINUTES` | 10 | Collection frequency |
| `DATABASE_URL` | `sqlite:///./data/nexnews.db` | Database location |

---

## Assumptions & Decisions

1. **RSS-only sources**: No API keys needed for news collection
2. **SQLite + ChromaDB**: Simple, file-based storage suitable for demo
3. **OpenAI embeddings**: Better quality than local models, low cost (~$0.00002/article)
4. **Semantic search**: AI applications benefit from natural language queries
5. **Docker-first**: Ensures consistent environment across machines

---

## Future Improvements

- [ ] Add more news sources (BBC Tech, The Verge, etc.)
- [ ] Switch to PostgreSQL for production scale
- [ ] Add Redis caching for frequent queries
- [ ] Implement rate limiting
- [ ] Add authentication for production use
- [ ] Create web dashboard

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| API | FastAPI |
| Database | SQLite + SQLAlchemy |
| Vector DB | ChromaDB |
| AI | OpenAI GPT-4.1 + Embeddings |
| Container | Docker Compose |
| Testing | pytest |

--- 