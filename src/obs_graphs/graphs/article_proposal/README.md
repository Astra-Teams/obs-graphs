# Article Proposal Graph

This directory contains the LangGraph workflow implementation for article proposal generation and execution.

## Directory Structure

```
article_proposal/
├── graph.py           # Main workflow orchestration and state graph definition
├── nodes/             # Individual workflow nodes/agents
│   ├── article_proposal.py          # Analyzes vault and proposes new articles
│   ├── article_content_generation.py # Generates full article content from proposals
│   ├── deep_research.py             # Conducts deep research using external API
│   ├── commit_changes.py            # Commits accumulated changes to branch
│   └── github_pr_creation.py        # Creates GitHub pull requests
├── prompts/           # LLM prompt templates
│   ├── new_article_content.md       # Template for generating article content
│   ├── new_article_creation.md      # Template for proposing new articles
│   └── research_topic_proposal.md   # Template for research topic proposals
├── schemas.py         # Pydantic models for workflow state validation
└── state.py           # Workflow state definitions and dataclasses
```

## Workflow Overview

The article proposal graph supports two main strategies:

### 1. New Article Creation Strategy
- **Trigger**: No user prompt provided
- **Flow**: `article_proposal` → `article_content_generation` → `commit_changes` → `github_pr_creation`
- **Purpose**: Analyzes vault structure and generates new articles to fill gaps

### 2. Research Proposal Strategy
- **Trigger**: User provides a research prompt
- **Flow**: `article_proposal` → `deep_research` → `commit_changes` → `github_pr_creation`
- **Purpose**: Creates research articles based on user-specified topics

## Node Responsibilities

### ArticleProposalAgent (`article_proposal`)
- Analyzes vault structure and content
- For new articles: Identifies gaps and proposes content
- For research: Generates topic proposals from user prompts
- Outputs article proposals or research topics

### ArticleContentGenerationAgent (`article_content_generation`)
- Takes article proposals and generates full markdown content
- Uses LLM to create comprehensive articles with frontmatter
- Creates file changes for new articles

### DeepResearchAgent (`deep_research`)
- Calls external research API for in-depth analysis
- Persists research results as markdown articles
- Handles API errors gracefully

### CommitChangesAgent (`commit_changes`)
- Commits all accumulated file changes atomically
- Generates meaningful commit messages
- Uses GitHub API for bulk operations

### GithubPRCreationAgent (`github_pr_creation`)
- Creates pull requests for committed changes
- Generates PR titles and descriptions
- Links PRs to workflow execution results

## State Management

The workflow uses a typed state graph with the following key components:

- **GraphState**: Main state object with vault summary, strategy, prompt, and execution results
- **AgentResult**: Standardized result format from all nodes
- **FileChange**: Represents file operations (create/update/delete)
- **Pydantic Models**: Validation schemas in `schemas.py`

## Configuration

Nodes are configured through dependency injection via the container system. Each node declares its `name` class attribute for registration and can specify required dependencies (LLM, GitHub client, etc.).

## Testing

Unit tests for individual nodes are located in `tests/unit/nodes/`. Integration tests for the full workflow are in `tests/intg/workflows/`.
