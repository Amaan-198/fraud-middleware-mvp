# Test Command

Run the test suite and report results.

## Steps

1. Check if virtual environment exists
2. Run pytest with coverage
3. Run latency tests separately
4. Run demo scenarios
5. Summarize results

## Expected Behavior

```bash
# Run unit tests
pytest tests/ -v --cov=api --cov-report=term-missing

# Run latency tests
python tests/test_latency.py

# Validate scenarios
python demo/run_scenarios.py --validate

# Report
echo "✅ Tests: X/Y passing"
echo "📊 Coverage: Z%"
echo "⚡ P95 Latency: Wms"
echo "🎭 Scenarios: 5/5 working"
```

## Success Criteria

- All tests pass
- Coverage >80%
- P95 latency <60ms
- All scenarios return expected codes
