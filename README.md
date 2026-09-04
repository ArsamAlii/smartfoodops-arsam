## SmartFoodOps AI Layer
Documentation Link:
https://docs.google.com/document/d/1aBRBtsvaJvidWhXUdb5j3lFWZW4G8Ojg/edit

The Week 5 AI layer provides:

- Grounded customer food recommendations
- Order-status explanations
- Restaurant description generation
- Restaurant promotion generation
- Structured restaurant highlights
- SSE streaming
- Redis AI rate limiting and caching
- AI interaction persistence
- AI analytics
- Prometheus AI metrics

### Requirements

- Docker Desktop
- Docker Compose
- Git
- Valid `LLM_API_KEY`
- Valid `EMBEDDING_API_KEY`

### Environment

Create a `.env` file in the project root.

Example:

```env
LLM_API_KEY=<your-key>
LLM_MODEL=openai/gpt-oss-20b
LLM_TIMEOUT_SECONDS=60

EMBEDDING_API_KEY=<your-key>
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

AI_RATE_LIMIT_PER_MINUTE=20
AI_CACHE_TTL_SECONDS=300