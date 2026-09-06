# Operations & Health Verification

## Verification Commands
```bash
# Run full unit test suite:
PYTHONPATH=src python3 -m unittest discover -s tests

# Check CLI entry points:
weather --version
cli-weather --version

# Check live query:
weather "Tokyo" -o
weather "Tokyo" --json
```
