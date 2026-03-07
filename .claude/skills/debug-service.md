---
name: debug-service
description: Systematic debugging workflow for Python services
---

# Debug Service Workflow

## Trigger
Use when investigating any bug, test failure, or unexpected behavior in a Python service.

## Process (follow in order, do NOT skip steps)

### 1. Reproduce
```bash
# Run the failing test or trigger the bug
cd services/py/<name> && uv run --package <name> pytest tests/<test_file>.py -v -s
```
If you can't reproduce, the bug report is incomplete. Ask for more details.

### 2. Isolate
- Which layer? routes -> services -> domain -> repositories
- Run test with `-s` flag to see print output
- Add strategic print/logging if needed
- Check: is it a data issue, logic issue, or infrastructure issue?

### 3. Understand root cause
- Read the code path end-to-end
- Check edge cases: None, empty list, missing key, concurrent access
- Check: does the same pattern exist elsewhere? (potential systemic issue)

### 4. Write failing test (TDD)
```python
async def test_bug_<description>(service, mock_repo):
    """Regression test for: <bug description>"""
    # Setup that triggers the bug
    mock_repo.<method>.return_value = <buggy_state>
    # Assert correct behavior
    result = await service.<method>(...)
    assert result == <expected>
```

### 5. Fix
- Fix root cause, not symptom
- Minimal change -- don't refactor unrelated code
- Keep the fix in the correct layer

### 6. Verify
```bash
cd services/py/<name> && uv run --package <name> pytest tests/ -v
```
ALL tests pass = done. Any failure = investigate further.

### 7. Check for similar bugs
- Search codebase for same pattern
- If found in 2+ places, fix all occurrences
