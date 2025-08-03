# PromptToVideo.com

A production-ready, monetized Flask application that generates videos from text prompts using Veo 3 AI technology.

## Features

- **AI Video Generation**: Create videos from text prompts using Veo 3
- **Quality Options**: Free (8 seconds, watermarked, no audio) and Premium (60 seconds, no watermark, with audio)
- **Credit System**: Daily free credits + paid credit packs
- **Authentication**: Email/password and passwordless login
- **Payment Integration**: Stripe Checkout for credit purchases
- **Video Storage**: Google Cloud Storage with signed URLs
- **Queue Management**: Celery for background video processing
- **Admin Dashboard**: Analytics and management tools
- **Developer API**: RESTful API for third-party integrations
- **SEO Optimized**: Public video pages with OG tags and sitemap

## Tech Stack

- **Backend**: Flask, SQLAlchemy, Celery
- **Database**: PostgreSQL
- **Cache/Queue**: Redis
- **Storage**: Google Cloud Storage
- **Payments**: Stripe
- **AI**: Veo 3 API
- **Monitoring**: Sentry
- **Testing**: pytest
- **Deployment**: Docker, Docker Compose

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- PostgreSQL
- Redis
- Veo API key
- Stripe account
- Google Cloud Storage bucket

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/prompttovideo.git
   cd prompttovideo
   ```

2. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

3. **Start with Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **Run database migrations**
   ```bash
   docker-compose exec web flask db upgrade
   ```

5. **Access the application**
   - Web: http://localhost:5000
   - API: http://localhost:5000/api/v1

### Development Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up database**
   ```bash
   flask db upgrade
   ```

3. **Run tests**
   ```bash
   pytest
   ```

4. **Start development server**
   ```bash
   flask run
   ```

## API Documentation

### Authentication

All API endpoints require authentication via JWT tokens.

```bash
# Register
POST /auth/register
{
  "email": "user@example.com",
  "password": "password123"
}

# Login
POST /auth/login
{
  "email": "user@example.com",
  "password": "password123"
}
```

### Video Generation

```bash
# Generate video
POST /api/v1/generate
Authorization: Bearer <token>
{
  "prompt": "A beautiful sunset over mountains",
  "quality": "free"  # or "premium"
}

# Check video status
GET /api/v1/videos/{video_id}
Authorization: Bearer <token>

# List user videos
GET /api/v1/videos?page=1&per_page=10
Authorization: Bearer <token>
```

### User Management

```bash
# Get credit balance
GET /api/v1/user/credits
Authorization: Bearer <token>
```

## Environment Variables

See `env.example` for all required environment variables:

- `VEO_API_KEY`: Your Veo API key
- `STRIPE_SECRET_KEY`: Stripe secret key
- `GCS_BUCKET_NAME`: Google Cloud Storage bucket name
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string

## Deployment

### Docker Deployment

```bash
# Build and run
docker-compose -f docker-compose.prod.yml up -d

# Scale workers
docker-compose -f docker-compose.prod.yml up -d --scale celery=3
```

### Cloud Run Deployment

```bash
# Deploy to Google Cloud Run
gcloud run deploy prompttovideo \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Railway Deployment

```bash
# Deploy to Railway
railway login
railway init
railway up
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_app.py
```

## Project Structure

```
prompttovideo/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── models.py            # Database models
│   ├── tasks.py             # Celery tasks
│   ├── mail.py              # Email functionality
│   ├── main/                # Main routes
│   ├── auth/                # Authentication
│   ├── api/                 # API endpoints
│   └── admin/               # Admin dashboard
├── tests/                   # Test suite
├── config.py                # Configuration
├── requirements.txt         # Python dependencies
├── Dockerfile              # Docker configuration
├── docker-compose.yml      # Docker Compose
└── README.md               # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, email support@prompttovideo.com or create an issue on GitHub.

## Roadmap

- [x] Phase 1: Core video generation and user management ✅
- [x] Phase 2: Stripe integration and payment processing ✅
- [x] Phase 3: Watermarking and SEO optimization ✅
- [x] Phase 4: Queue prioritization and rate limiting ✅
- [x] Phase 5: Admin analytics and management ✅
- [x] Phase 6: Queue prioritization, rate limiting, and lightweight admin analytics ✅
- [x] Phase 7: One-click Cloud Run/Railway deploy, Tailwind UI, referral code engine, prompt-pack CMS, and developer API stubs ✅

## Phase 7 Features

### 🚀 **Deployment Configurations**
- **Railway Deployment**: `railway.json` for one-click Railway deployment
- **Google Cloud Run**: `cloudbuild.yaml` for automated Cloud Run deployment
- **Deployment Script**: `deploy.sh` supporting both Cloud Run and Railway

### 👥 **Referral System**
- **Referral Codes**: Unique 8-character codes for each user
- **Referral Landing Pages**: Beautiful landing pages for referral links (`/ref/{code}`)
- **Referral Dashboard**: Complete dashboard showing stats, earnings, and sharing tools
- **Credit Rewards**: 5 credits for both referrer and referred user
- **Social Sharing**: Pre-formatted content for Twitter, Facebook, LinkedIn, and email

### 🔌 **Developer API**
- **RESTful API**: Complete v1 API with authentication and rate limiting
- **Video Generation**: `POST /api/v1/generate` for programmatic video creation
- **Status Checking**: `