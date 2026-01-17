# 🔐 Ideation Vault

> **The Backend Powerhouse of Africa's Startup Engine**

Welcome to **Ideation Vault** — the robust API infrastructure behind [Ideation Axis Group](https://ideationaxis.com), Africa's premier venture studio. This is where data flows securely, where business logic powers innovation, and where we build the scalable foundation that supports tomorrow's game-changing startups.

---

## 🎯 Our Mission

We're not just building an API. We're architecting the secure, scalable backbone that powers Africa's venture ecosystem — managing portfolios, processing analytics, and enabling the digital infrastructure that transforms ideas into thriving businesses.

**Every endpoint here serves Africa's entrepreneurial future.**

---

## ⚡ Quick Start

Get the engine running in seconds:

```bash
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

# Fire up the development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open [http://localhost:8000/docs](http://localhost:8000/docs) and explore the interactive API documentation. Your changes auto-reload — because momentum waits for no one.

---

## 🏗️ Tech Stack

We build with purpose using:

- **FastAPI** - Modern, high-performance Python web framework
- **SQLAlchemy** - Powerful SQL toolkit and ORM
- **Alembic** - Database migration management
- **Pydantic** - Data validation using Python type annotations
- **PostgreSQL** - Robust relational database
- **Redis** - In-memory caching and session management
- **Celery/ARQ** - Distributed task queue for background jobs
- **JWT** - Secure token-based authentication
- **pytest** - Comprehensive testing framework

---

## 📁 Project Structure

```
ideation-vault/
│
├── alembic/                          
│   ├── versions/                     
│   ├── env.py                        
│   └── script.py.mako                
│
├── app/
│   ├── api/                          
│   │   ├── dependencies/             
│   │   │   ├── __init__.py
│   │   │   ├── auth.py               
│   │   │   ├── database.py           
│   │   │   └── permissions.py        
│   │   │
│   │   ├── v1/                       
│   │   │   ├── endpoints/            
│   │   │   │   ├── __init__.py
│   │   │   │   ├── ventures.py       
│   │   │   │   ├── auth.py           
│   │   │   │   ├── users.py          
│   │   │   │   ├── portfolio.py      
│   │   │   │   └── analytics.py     
│   │   │   │
│   │   │   └── router.py             
│   │   │
│   │   └── router.py                 
│   │
│   ├── core/                         
│   │   ├── __init__.py
│   │   ├── config.py                
│   │   ├── security.py               
│   │   ├── logging.py                
│   │   └── exceptions.py            
│   │
│   ├── db/                          
│   │   ├── __init__.py
│   │   ├── base.py                   
│   │   ├── session.py                
│   │   └── init_db.py               
│   │
│   ├── models/                       
│   │   ├── __init__.py
│   │ 
│   │
│   ├── schemas/                      
│   │   ├── __init__.py
│   │
│   │
│   ├── services/                     
│   │   ├── __init__.py
│   │
│   │
│   ├── utils/                       
│   │   ├── __init__.py
│   │
│   ├── middleware/                   
│   │   ├── __init__.py
│   │   ├── cors.py                   # CORS configuration
│   │   ├── rate_limit.py             # Rate limiting
│   │   └── request_logger.py         # Request logging
│   │
│   ├── tasks/                        # Background tasks (Celery/ARQ)
│   │   ├── __init__.py
│   │
│   ├── constants/                    # Application constants
│   │   ├── __init__.py
│   │
│   └── main.py                       # Application entry point
│
├── tests/                            # Test suite
│   ├── __init__.py
│   ├── conftest.py                   
│   ├── unit/                         
│   │   ├── test_services/
│   │   ├── test_repositories/
│   │   └── test_utils/
│   ├── integration/                  # Integration tests
│   │   ├── test_api/
│   │   └── test_database/
│   └── e2e/                          # End-to-end tests
│       └── test_workflows/
│
├── scripts/                         
│   ├── seed_db.py                   
│
├── docs/                             
├── .gitignore                        # Git ignore rules
├── alembic.ini                       # Alembic configuration
├── requirements.txt                  # Python dependencies
└── README.md                         # This file
```

### 🗂️ Key Directories Explained

**`app/api/`** - RESTful API layer with versioning support
- `dependencies/` - Shared FastAPI dependencies for auth, database sessions, and permissions
- `v1/endpoints/` - Domain-organized API endpoints (ventures, users, portfolio, analytics)
- Clean separation enables API versioning without breaking changes

**`app/core/`** - Application core with configuration and security
- `config.py` - Centralized settings using Pydantic BaseSettings
- `security.py` - JWT handling, password hashing, and token management
- `exceptions.py` - Custom exception classes for consistent error handling

**`app/models/`** - SQLAlchemy ORM models representing database tables
- Follow declarative base pattern
- Include relationships, indexes, and constraints
- Base model provides common fields (id, created_at, updated_at)

**`app/schemas/`** - Pydantic schemas for request/response validation
- Separate Create, Update, Response, and InDB schemas
- Automatic validation and serialization
- Type-safe data transfer objects

**`app/services/`** - Business logic layer
- Orchestrates operations between repositories
- Implements complex business rules
- Handles transactions and error scenarios

**`app/repositories/`** - Data access layer using Repository pattern
- Abstracts database operations
- Provides reusable CRUD methods
- Enables easy testing with mock repositories

**`app/tasks/`** - Background job processing
- Asynchronous email sending
- Analytics computation
- Scheduled cleanup operations

---

## 🛠️ Available Scripts

```bash
# Development
uvicorn app.main:app --reload                    # Start dev server with auto-reload
python -m pytest                                  # Run test suite
python -m pytest --cov=app                        # Run tests with coverage
python -m pytest -v -s                            # Run tests with verbose output

# Database
alembic revision --autogenerate -m "message"     # Create new migration
alembic upgrade head                              # Apply migrations
alembic downgrade -1                              # Rollback last migration
python scripts/seed_db.py                         # Seed database with test data

# Production
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker  # Production server
```

---

## 🔧 Environment Variables

Create a `.env` file in the root directory:

```bash
# Application
APP_NAME=Ideation Vault
APP_ENV=development
DEBUG=True
API_V1_PREFIX=/api/v1

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/ideation_vault
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here-generate-with-openssl
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:3000", "https://ideationaxis.com"]

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAILS_FROM_EMAIL=noreply@ideationaxis.com

# Celery/ARQ
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# File Storage
UPLOAD_FOLDER=uploads
MAX_UPLOAD_SIZE=10485760  # 10MB

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

## 🎨 Development Guidelines

### Code with Purpose
Every model, every endpoint, every service matters. We're building the infrastructure that powers Africa's entrepreneurial future.

### Architecture Principles
- **Separation of Concerns**: Clear boundaries between API, business logic, and data access
- **Repository Pattern**: Abstract database operations for flexibility and testability
- **Service Layer**: Centralize business logic and orchestration
- **Schema Validation**: Use Pydantic for automatic request/response validation
- **Async by Default**: Leverage FastAPI's async capabilities for optimal performance

### API Design Standards
```python
# Use proper HTTP methods
GET     /api/v1/ventures              # List ventures
POST    /api/v1/ventures              # Create venture
GET     /api/v1/ventures/{id}         # Get venture
PUT     /api/v1/ventures/{id}         # Update venture
DELETE  /api/v1/ventures/{id}         # Delete venture

# Use proper status codes
200 OK                                 # Successful GET, PUT
201 Created                            # Successful POST
204 No Content                         # Successful DELETE
400 Bad Request                        # Validation error
401 Unauthorized                       # Not authenticated
403 Forbidden                          # Not authorized
404 Not Found                          # Resource doesn't exist
500 Internal Server Error              # Server error
```

### Commit with Clarity
Write meaningful commit messages:
```
✨ Add venture portfolio analytics endpoint
🐛 Fix authentication token refresh logic
♻️ Refactor user repository for better query performance
🔒 Add rate limiting to authentication endpoints
📝 Update API documentation for venture endpoints
```

### Testing Standards
- Write tests for all services and repositories
- Aim for 80%+ code coverage
- Use fixtures for database setup
- Mock external dependencies
- Test edge cases and error scenarios

---

## 🔐 Security Best Practices

- ✅ JWT-based authentication with refresh tokens
- ✅ Password hashing using bcrypt
- ✅ Rate limiting on sensitive endpoints
- ✅ CORS configuration for frontend integration
- ✅ SQL injection prevention via SQLAlchemy ORM
- ✅ Input validation using Pydantic schemas
- ✅ Audit logging for sensitive operations
- ✅ Environment-based configuration (never commit secrets)

---

## 🚀 Deployment

### Docker Deployment
```bash
# Build image
docker build -t ideation-vault .

# Run container
docker run -d -p 8000:8000 --env-file .env ideation-vault

# Using Docker Compose
docker-compose up -d
```

### Production Checklist
- [ ] Set `DEBUG=False` in production
- [ ] Use strong `SECRET_KEY` (generate with `openssl rand -hex 32`)
- [ ] Configure proper CORS origins
- [ ] Set up SSL/TLS certificates
- [ ] Enable database connection pooling
- [ ] Configure logging aggregation
- [ ] Set up monitoring and alerting
- [ ] Implement automated backups
- [ ] Configure rate limiting
- [ ] Set up CI/CD pipeline

---

## 📊 API Documentation

Interactive API documentation is automatically generated and available at:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI JSON**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_services/test_venture_service.py

# Run with output
pytest -v -s

# Run only integration tests
pytest tests/integration/
```

---

## 🌍 The Bigger Picture

This isn't just backend code. This is:
- The secure foundation for Africa's venture ecosystem
- The data engine that powers portfolio analytics
- The reliable infrastructure that founders depend on

**You're not just a developer on this project. You're an architect of Africa's entrepreneurial future.**

---

## 🤝 Contributing

We're building something special, and we're building it together.

1. Create your feature branch: `git checkout -b feature/amazing-feature`
2. Write tests for your changes
3. Ensure all tests pass: `pytest`
4. Format your code: `black . && isort .`
5. Commit your changes: `git commit -m '✨ Add amazing feature'`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request and let's review together

---

## 📚 Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

---

## 🔗 Connect with the Ecosystem

- **Ideation Studio** - Our frontend powerhouse (Next.js)
- **Main Site** - [ideationaxis.com](https://ideationaxis.com)
- **API Documentation** - [api.ideationaxis.com/docs](https://api.ideationaxis.com/docs)

---

## 🐛 Troubleshooting

### Database Connection Issues
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Verify connection string in .env
# Ensure DATABASE_URL format: postgresql://user:password@host:port/dbname
```

### Migration Issues
```bash
# Reset migrations (development only!)
alembic downgrade base
alembic upgrade head

# Check current migration version
alembic current
```

### Import Errors
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

---

## 💡 Remember

Every endpoint is a gateway to opportunity. Every database query supports a founder's dream. Every line of code removes friction from Africa's entrepreneurial journey.

**Let's build Africa's future, one API call at a time.**

---

*Built with ❤️ by the Ideation Axis Group team*

---

## 📄 License

This project is proprietary and confidential. Unauthorized copying, distribution, or use is strictly prohibited.

© 2025 Ideation Axis Group. All rights reserved.
