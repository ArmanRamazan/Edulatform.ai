---
name: tdd-backend
description: TDD workflow for Python backend services. Red-Green-Refactor cycle.
---

# TDD Backend Workflow

## Trigger
Use for ANY Python backend code change (new feature, bug fix, refactor).

## Mandatory process -- skipping any step = invalid work

### Step 1: RED -- Write failing test FIRST
```bash
# Read existing tests for patterns:
cat services/py/<name>/tests/conftest.py
cat services/py/<name>/tests/test_<module>.py

# Write test that describes expected behavior
# Use AsyncMock(spec=Repository) for unit tests
# Use real fixtures for integration tests
```

**Test structure:**
```python
import pytest
from unittest.mock import AsyncMock
from app.services.<module> import <Service>
from app.domain.<entity> import <Entity>

@pytest.fixture
def mock_repo():
    return AsyncMock(spec=<Repository>)

@pytest.fixture
def service(mock_repo):
    return <Service>(mock_repo)

async def test_<behavior>(service, mock_repo):
    # Arrange
    mock_repo.<method>.return_value = <expected>
    # Act
    result = await service.<method>(<args>)
    # Assert
    assert result == <expected>
```

### Step 2: Run test -- confirm it FAILS
```bash
cd services/py/<name> && uv run --package <name> pytest tests/test_<module>.py::<test_name> -v
```
Expected: FAIL. If it passes, the test is wrong.

### Step 3: GREEN -- Minimal implementation
Write the minimum code to make the test pass. No extra features. No "while I'm here" changes.

### Step 4: Run test -- confirm it PASSES
```bash
cd services/py/<name> && uv run --package <name> pytest tests/ -v
```
ALL tests must pass. Not just the new one.

### Step 5: REFACTOR
- Remove duplication
- Improve naming
- Extract if needed (but only if used 3+ times)

### Step 6: Run full suite again
```bash
cd services/py/<name> && uv run --package <name> pytest tests/ -v
```

### Step 7: Commit
```bash
git add services/py/<name>/
git commit -m "<type>(<scope>): <description>"
```
