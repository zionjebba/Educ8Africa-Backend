🔐 Educ8Africa Backend

Empowering Africa's Learners, One API at a Time

Welcome to Educ8Africa — the backend engine behind Educ8Africa
, Africa's premier education and skills platform. This is where data flows securely, learning journeys are tracked, and scalable infrastructure supports every learner’s success story.

🎯 Our Mission

We’re not just building APIs — we’re building the backbone of Africa’s digital learning ecosystem. From course management to performance tracking, every endpoint supports accessible, flexible, and quality education for every learner.

Every request here contributes to Africa’s educational future.

⚡ Quick Start

Get the backend running locally:

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Initialize the database
python -m app.db.init_db

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000


Open http://localhost:8000/docs
 to explore the interactive API documentation. Auto-reload ensures your updates are live instantly.

🏗️ Tech Stack

We build with purpose using:

FastAPI – Modern, high-performance Python web framework

SQLAlchemy – ORM and SQL toolkit for database management

Alembic – Database migration management

Pydantic – Type-safe validation for requests/responses

PostgreSQL – Reliable relational database

Redis – Caching and session management

Celery/ARQ – Background tasks and asynchronous jobs

JWT – Secure authentication tokens

pytest – Testing framework

📁 Project Structure
educ8africa-backend/
│
├── alembic/                        
├── app/
│   ├── api/                         # RESTful API endpoints
│   │   ├── dependencies/            
│   │   ├── v1/
│   │   │   └── endpoints/           # Courses, Users, Performance, Analytics
│   │   └── router.py
│   │
│   ├── core/                        # Configuration, security, logging
│   ├── db/                          # Database session and init
│   ├── models/                      # ORM models
│   ├── schemas/                     # Pydantic schemas
│   ├── services/                    # Business logic layer
│   ├── repositories/                # Data access layer
│   ├── tasks/                       # Async background jobs
│   ├── middleware/                  # CORS, rate limiting, logging
│   └── main.py                      # Entry point
│
├── tests/                           # Unit, integration, and e2e tests
├── scripts/                         # Seed and utility scripts
├── docs/                            # Documentation
├── requirements.txt                 
└── README.md                        

🛠️ Available Scripts
# Development
uvicorn app.main:app --reload                    
pytest                                          
pytest --cov=app                                
pytest -v -s                                    

# Database
alembic revision --autogenerate -m "message"
alembic upgrade head
alembic downgrade -1
python scripts/seed_db.py                        

# Production
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker

🔧 Environment Variables
# Application
APP_NAME=Educ8Africa
APP_ENV=development
DEBUG=True
API_V1_PREFIX=/api/v1

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/educ8africa
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:3000", "https://educ8africa.com"]

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAILS_FROM_EMAIL=noreply@educ8africa.com

# Celery/ARQ
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

🎨 Development Guidelines

Separation of Concerns – API, business logic, and data access layers are isolated

Repository Pattern – Clean database abstraction

Service Layer – Orchestrates business logic

Schema Validation – Type-safe request/response handling with Pydantic

Async by Default – Leverage FastAPI's async capabilities

🔐 Security Best Practices

JWT authentication with refresh tokens

Password hashing with bcrypt

Rate limiting on sensitive endpoints

SQL injection prevention with ORM

CORS configuration

Audit logging

Never commit secrets

🚀 Deployment
# Docker
docker build -t educ8africa-backend .
docker run -d -p 8000:8000 --env-file .env educ8africa-backend

# Docker Compose
docker-compose up -d


Checklist for production:

 Set DEBUG=False

 Strong SECRET_KEY

 Proper CORS

 SSL/TLS certificates

 Connection pooling

 Logging aggregation

 Monitoring & alerts

 Automated backups

 CI/CD pipeline

📊 API Documentation

Swagger UI: http://localhost:8000/docs

ReDoc: http://localhost:8000/redoc

OpenAPI JSON: http://localhost:8000/openapi.json

🤝 Contributing

Create feature branch: git checkout -b feature/amazing-feature

Write tests

Run tests: pytest

Format code: black . && isort .

Commit: git commit -m '✨ Add amazing feature'

Push: git push origin feature/amazing-feature

Open a Pull Request

📚 Resources

FastAPI Documentation

SQLAlchemy Documentation

Pydantic Documentation

Alembic Documentation

PostgreSQL Documentation

🌍 The Bigger Picture

This backend is more than code — it’s the engine behind Africa’s learners, ensuring access, scalability, and security for everyone.

Every endpoint supports a learner’s growth. Every database query powers opportunity.

📄 License

This project is proprietary and confidential. Unauthorized use or distribution is prohibited.

© 2026 Educ8Africa. All rights reserved.