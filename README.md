# fal.ai Proxy Application

A proxy service that forwards image editing requests to fal.ai's kontext endpoints with image download/upload, caching, and retry logic.

The App APIs are deployed on the url: https://fal-proxy-app.onrender.com/docs#

## Features

- 3 endpoints: `/kontext`, `/kontext/max`, `/kontext/dev`
- Automatic image download from user URLs
- Cloud storage for public accessibility
- Redis caching for duplicate requests
- Retry logic with exponential backoff
- Error handling with specific status codes

## Quick Start

### Prerequisites

- Docker Desktop
- fal.ai API key
- Supabase account

### Setup

1. **Clone & Configure**

```bash
git clone https://github.com/Ashay041/fal-proxy-app.git
```

2. **Create `.env` file**

```env
FAL_KEY=your_fal_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

3. **Run with Docker**

```bash
docker-compose up --build
```

4. **Access**

- API Docs: http://localhost:8000/docs#
- To use the deployed version of the app: https://fal-proxy-app.onrender.com/docs#

## Technologies Used

**Backend**

- FastAPI (async Python framework)
- fal-client (fal.ai SDK)
- httpx (async HTTP client)
- tenacity (retry logic)

**Storage & Database**

- Supabase (cloud file storage + PostgreSQL)
- Neon (PostgreSQL database)
- Upstash (Redis cache)

**Deployment & CI/CD**

- Render (backend hosting)
- GitHub Actions (automated deployment pipeline)
- Docker (containerization)

## API Endpoints

### `POST /kontext`

```json
{
  "image_url": "https://example.com/image.jpg",
  "prompt": "make it blue",
  "seed": 12345,
  "num_images": 1
}
```

### `POST /kontext/max`

Same parameters as `/kontext`

### `POST /kontext/dev`

```json
{
  "image_url": "https://example.com/image.jpg",
  "prompt": "change to daytime",
  "num_inference_steps": 35,
  "acceleration": "regular"
}
```

## Testing

```bash
pytest tests/ -v
```

## Architecture flow

```
Request → Cache Check → Download Image → Upload to Storage 
→ Call fal.ai → Download Results → Upload Results → Cache → Return
```

## Project Structure

```
├── services/
│   ├── image_service.py    # Image download/upload
│   ├── fal_service.py      # fal.ai API calls
│   ├── cache_service.py    # Redis caching
│   └── database.py         # PostgreSQL setup
├── tests/                  # Unit tests
├── main.py                 # FastAPI app
└── docker-compose.yml
```
