# Code Style and Conventions

## Code Formatting
- **Black**: Python code formatter (target Python 3.12)
- **Ruff**: Fast Python linter with rules E, F, I
- **Ignored Rules**: E501 (line too long)

## Type Hints
- Type hints are used throughout the codebase
- Protocol-based interfaces for dependency injection
- Optional types from typing module

## Docstrings
- Google-style docstrings
- Classes and public methods are documented
- Args, Returns, and Raises sections are included

## Naming Conventions
- **Classes**: PascalCase (e.g., `GithubClient`, `DependencyContainer`)
- **Functions/Methods**: snake_case (e.g., `get_github_client`, `clone_repository`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `POSTGRES_HOST`, `OLLAMA_MODEL`)
- **Private attributes**: Leading underscore (e.g., `_github_client`, `_llm`)

## Project Structure
- Protocol definitions in `src/protocols/`
- Implementations in corresponding module directories
- DI container manages all dependencies
- Settings loaded via pydantic-settings from environment

## Design Patterns
- **Dependency Injection**: Protocol-based DI container
- **Lazy Instantiation**: Dependencies created on first access
- **Settings Pattern**: Pydantic BaseSettings for configuration
- **Repository Pattern**: Vault service for file operations
