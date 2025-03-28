# Yearn Risk Score Guidelines

## Development Commands
- **Run Scripts**: `uv run scripts/scan_factories.py` or `uv run protocol/scripts/veda_scan_auth_events.py`
- **Code Formatting**: `uv run -m ruff format .`
- **Update Lock File**: `uv lock` (after changing dependencies in pyproject.toml)

## Dependencies
- **Core Dependencies**:
  - web3: For blockchain interaction
  - python-dotenv: For environment variable management
  - requests: For API calls
- **Dev Dependencies**:
  - ruff: For code formatting and linting

## Style Guidelines
- **Imports**: Group standard library imports first, followed by third-party imports, then local imports
- **Code Organization**: Use functions and classes with clear responsibilities
- **Type Hints**: Use Python typing module for function parameters and return values
- **Error Handling**: Use specific exception catching and provide informative error messages
- **Documentation**: Include docstrings for functions/classes with descriptions and parameter details
- **Naming**: Use snake_case for variables/functions, PascalCase for classes
- **Environment Variables**: Store sensitive data (API keys, RPC URLs) in .env file (never commit)

## Coding Practices
- Cache results to minimize blockchain RPC calls
- Use LRU cache for frequently accessed data
- Prefer batch requests when interacting with blockchain
- Log important information with appropriate log levels
- Organize data output in markdown tables for readability