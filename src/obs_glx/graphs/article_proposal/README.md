# Article Proposal Graph

This directory contains the LangGraph workflow implementation for article proposal generation and execution.

## Directory Structure

```
article_proposal/
├── graph.py           # Main workflow orchestration and state graph definition
├── nodes/             # Individual workflow nodes/agents
│   ├── node1_article_proposal.py    # Analyzes vault and proposes new articles
│   ├── node2_deep_research.py       # Conducts deep research using external API
│   └── node3_submit_draft_branch.py # Submits markdown drafts to GitHub
├── prompts/           # LLM prompt templates
│   ├── new_article_creation.md      # Template for proposing new articles
│   └── research_topic_proposal.md   # Template for research topic proposals
├── schemas.py         # Pydantic models for workflow state validation
└── state.py           # Workflow state definitions and dataclasses
```

## Workflow Overview

The article proposal graph supports two main strategies:

### 1. New Article Creation Strategy
- **Trigger**: No user prompt provided
- **Flow**: `article_proposal` → `submit_draft_branch`
- **Purpose**: Analyzes vault structure and generates new articles to fill gaps

### 2. Research Proposal Strategy
- **Trigger**: User provides one or more research prompts
- **Flow**: `article_proposal` → `deep_research` → `submit_draft_branch`
- **Purpose**: Creates research articles based on user-specified topics

## Node Responsibilities

### ArticleProposalAgent (`article_proposal`)
- Analyzes vault structure and content
- For new articles: Identifies gaps and proposes content
- For research: Uses the first prompt from the ordered list to generate topic proposals while preserving the remaining prompts for downstream agents
- Outputs article proposals or research topics

### DeepResearchAgent (`deep_research`)
- Calls external research API for in-depth analysis
- Persists research results as markdown articles
- Handles API errors gracefully

### SubmitDraftBranchNode (`submit_draft_branch`)
- Generates commit messages and branch content from accumulated results
- Creates workflow branches via GitHub and records metadata for operators
- Stores branch metadata (name, files) for downstream consumers

## State Management

The workflow uses a typed state graph with the following key components:

- **GraphState**: Main state object with vault summary, strategy, prompts list, and execution results
- **AgentResult**: Standardized result format from all nodes
- **FileChange**: Represents file operations (create/update/delete)
- **Pydantic Models**: Validation schemas in `schemas.py`

## Configuration

Nodes are configured through dependency injection via the container system. Each node declares its `name` class attribute for registration and can specify required dependencies (LLM, GitHub client, etc.).

## Testing

Unit tests for individual nodes are located in `tests/unit/nodes/`. Integration tests for the full workflow are in `tests/intg/workflows/`.
