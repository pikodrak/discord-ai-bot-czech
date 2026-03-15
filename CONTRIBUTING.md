# Contributing Guide

Thank you for considering contributing to the Discord AI Bot project!

## How to Contribute

### Reporting Bugs

1. Check existing issues to avoid duplicates
2. Use the bug report template
3. Include:
   - Bot version
   - Environment (Docker/local, OS)
   - Configuration (sanitized, no secrets)
   - Complete error logs
   - Steps to reproduce

### Suggesting Features

1. Open an issue with "Feature Request" label
2. Describe:
   - Use case
   - Expected behavior
   - Why it would be useful
   - Possible implementation approach

### Code Contributions

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Add tests if applicable
5. Update documentation
6. Commit with clear messages
7. Push and create a pull request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/your-username/discord-ai-bot-czech.git
cd discord-ai-bot-czech

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies

# Create test configuration
cp .env.example .env.test
# Edit .env.test with test credentials

# Run tests
pytest
```

## Code Style

- Follow PEP 8
- Use type hints
- Maximum line length: 100 characters
- Use meaningful variable names
- Add docstrings to functions/classes

Example:
```python
def calculate_interest_score(message: str, history: List[str]) -> float:
    """
    Calculate how interesting a message is based on content and context.
    
    Args:
        message: The message to evaluate
        history: Recent message history for context
    
    Returns:
        Interest score between 0.0 and 1.0
    """
    # Implementation
    pass
```

## Testing

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_bot.py

# With coverage
pytest --cov=src --cov-report=html
```

### Writing Tests

```python
import pytest
from src.bot import calculate_interest_score

def test_interest_score_high():
    """Test that interesting messages score high."""
    message = "Právě jsem objevil něco neuvěřitelného!"
    score = calculate_interest_score(message, [])
    assert score > 0.7

def test_interest_score_low():
    """Test that boring messages score low."""
    message = "ok"
    score = calculate_interest_score(message, [])
    assert score < 0.3
```

## Commit Messages

Format:
```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding/updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(bot): add support for multiple channels

- Bot can now monitor multiple channels
- Configuration updated to accept channel list
- Admin interface updated for channel management

Closes #42
```

```
fix(api): handle rate limit errors gracefully

Previously, rate limit errors would crash the bot.
Now they are caught and the bot waits before retrying.

Fixes #56
```

## Pull Request Process

1. Update README.md if needed
2. Update CHANGELOG.md
3. Ensure all tests pass
4. Request review from maintainers
5. Address review comments
6. Squash commits if requested
7. Maintainer will merge

## Documentation

Update documentation for:
- New features
- Configuration changes
- API endpoints
- Breaking changes

Documentation files:
- `README.md`: Main documentation
- `QUICKSTART.md`: Quick setup guide
- `docs/API.md`: API reference
- `docs/DEPLOYMENT.md`: Deployment guide
- `docs/CONFIGURATION.md`: Configuration reference

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
