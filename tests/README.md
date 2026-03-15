# Discord AI Bot - Test Suite

Comprehensive test suite for the Czech Discord AI bot with API failover and admin interface.

## Test Structure

### Core Test Modules

1. **test_message_detection.py** - Message interest detection and conversation participation
   - Question detection
   - Conversation starters
   - Bot mention handling
   - Context awareness
   - Rate limiting
   - Spam detection

2. **test_czech_responses.py** - Czech language quality and naturalness
   - Czech language verification
   - Grammar checking
   - Idiom usage
   - Formality level matching
   - Cultural context handling
   - Response personality

3. **test_api_failover.py** - API failover mechanism (Claude → Gemini → OpenAI)
   - Primary API usage
   - Failover triggers
   - Timeout handling
   - Rate limit handling
   - Context preservation
   - Health checks

4. **test_admin_interface.py** - FastAPI admin interface
   - Authentication (login/logout)
   - Configuration management
   - Bot control (start/stop/restart)
   - Token management
   - WebSocket connections

5. **test_error_handling.py** - Error handling and edge cases
   - Discord connection errors
   - API errors
   - Edge cases (empty messages, special characters)
   - State management
   - Recovery mechanisms

6. **test_docker_deployment.py** - Docker deployment integration
   - Docker build
   - Container runtime
   - Docker Compose
   - Production readiness
   - Scalability

## Running Tests

### Install Dependencies

```bash
pip install -r tests/requirements.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Module

```bash
pytest tests/test_message_detection.py
pytest tests/test_czech_responses.py
pytest tests/test_api_failover.py
pytest tests/test_admin_interface.py
pytest tests/test_error_handling.py
```

### Run Tests by Marker

```bash
# Run only async tests
pytest -m asyncio

# Skip Docker tests
pytest -m "not docker"

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

### Run with Coverage

```bash
pytest --cov=src --cov-report=html
```

This generates an HTML coverage report in `htmlcov/index.html`.

### Run Verbose

```bash
pytest -v
```

## Test Implementation Status

These tests are designed to be implemented alongside the actual bot code. Currently, most test bodies are scaffolded with `pass` statements and commented-out assertions. As you implement each feature:

1. Uncomment the relevant test code
2. Import the actual implementation
3. Run the tests to verify functionality

## Coverage Goals

- **Overall Coverage**: 70%+ (enforced by pytest.ini)
- **Core Bot Logic**: 80%+
- **API Failover**: 90%+
- **Admin Interface**: 75%+
- **Error Handling**: 85%+

## Test Categories

### Unit Tests
- Individual function testing
- Mock external dependencies
- Fast execution
- No network calls

### Integration Tests
- Component interaction
- Real API calls (with test keys)
- Database interactions
- Marked with `@pytest.mark.integration`

### Docker Tests
- Container building
- Deployment verification
- Requires Docker daemon
- Marked with `@pytest.mark.docker`

## Continuous Integration

Tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run tests
  run: |
    pip install -r tests/requirements.txt
    pytest --cov=src --cov-report=xml
```

## Troubleshooting

### Import Errors
Ensure the `src/` directory is in your Python path:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Async Test Failures
Make sure `pytest-asyncio` is installed and `asyncio_mode = auto` is set in `pytest.ini`.

### Docker Tests Failing
- Ensure Docker daemon is running
- Check you have permissions to access Docker
- Try: `sudo usermod -aG docker $USER`

### Missing Dependencies
Install all test requirements:
```bash
pip install -r tests/requirements.txt
```

## Best Practices

1. **Keep Tests Independent**: Each test should be able to run in isolation
2. **Use Fixtures**: Reuse common setup via pytest fixtures in `conftest.py`
3. **Mock External Services**: Don't make real API calls in unit tests
4. **Clear Test Names**: Test names should describe what they test
5. **Fast Tests**: Keep unit tests fast (<1s each)
6. **Meaningful Assertions**: Test actual behavior, not implementation details

## Adding New Tests

1. Create test file following naming convention: `test_*.py`
2. Use appropriate test class: `class Test*:`
3. Add fixtures to `conftest.py` if reusable
4. Mark tests appropriately (`@pytest.mark.asyncio`, etc.)
5. Update this README with new test categories

## Contact

For questions about testing strategy or implementation, refer to the main project documentation.
