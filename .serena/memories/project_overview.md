# Obsidian Graphs - Project Overview

## Purpose
AI-powered workflow automation for Obsidian vaults using LangGraph and modular nodes. The project provides intelligent agents that can analyze, organize, and enhance Obsidian knowledge bases through automated workflows.

## Tech Stack
- **Framework**: FastAPI for REST API
- **Workflow Engine**: LangGraph for state-based workflow orchestration
- **LLM Integration**: Langchain + Ollama
- **Database**: PostgreSQL (production) / SQLite (testing)
- **Task Queue**: Celery with Redis
- **VCS**: GitPython for repository operations
- **GitHub API**: PyGithub for PR creation and repo management
- **Containerization**: Docker with multi-stage builds optimized for uv
- **Package Manager**: uv (ultra-fast dependency management)
- **Python Version**: 3.12+

## Architecture
- **Dependency Injection**: Protocol-based DI container in `src/container.py`
- **Modular Nodes**: Extensible agent system for vault operations
- **Database Switching**: Environment-based (USE_SQLITE flag) database selection
- **External Services**: GitHub, Ollama, Redis

## Key Features
- Article improvement, categorization, cross-referencing
- File organization and quality audits
- Automated PR creation for vault changes
- LangGraph-based workflow orchestration
- Comprehensive testing (unit, db, e2e)
