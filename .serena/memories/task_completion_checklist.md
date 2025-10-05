# Task Completion Checklist

## Before Committing Code
1. **Format**: Run `just format` to format code with black and ruff
2. **Lint**: Run `just lint` to check code quality
3. **Test**: Run `just test` to execute full test suite
4. **Verify**: Ensure all tests pass before committing

## After Code Changes
- Local tests (unit + SQLite) should pass
- Docker tests (PostgreSQL + e2e) should pass for production-ready code
- Code should be formatted and linted

## For Database Changes
1. Create models in `src/db/models/`
2. Generate migration: `alembic revision --autogenerate -m "description"`
3. Apply migration: `alembic upgrade head`
4. Test migrations in both SQLite and PostgreSQL

## CI/CD Considerations
- Database migrations run automatically in Docker containers
- Separate environments use different Docker Compose project names
- Volumes are environment-specific and prefixed with PROJECT_NAME
