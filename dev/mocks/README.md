# Development Mocks

This directory contains mock data for development and testing.

## Structure

```
dev/mocks/
├── github_responses.json  # Mock GitHub API responses
├── llm_responses.json     # Mock LLM responses
├── vault/                 # Sample Obsidian vault for development
│   ├── .obsidian/
│   ├── Technology/
│   ├── Programming/
│   └── Science/
└── README.md
```

## Usage

### Enable Mock Mode in Development

Set these environment variables in your `.env` file:

```bash
DEBUG=true
USE_MOCK_GITHUB=true   # Use mock GitHub responses
USE_MOCK_LLM=true      # Use mock LLM responses
MOCK_DATA_DIR=dev/mocks
```

### Mock Files

- **github_responses.json**: Contains mock responses for GitHub API calls
- **llm_responses.json**: Contains mock responses for LLM API calls

### Sample Vault

The `vault/` directory contains a sample Obsidian vault for development:
- Use it to test workflow operations
- Add more sample articles as needed
- Mimics the structure of a real Obsidian vault

## Notes

- Mocks are only active when `DEBUG=true`
- Test environment always uses mocks regardless of DEBUG setting
- Production environment ignores mock settings
