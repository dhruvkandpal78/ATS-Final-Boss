# Status: B01 - Reproducible environment and artifact startup

- **Status**: Completed B01
- **Source commit**: c469fff...
- **Changed paths**: pyproject.toml, .env.example, scripts/doctor.py, scripts/generate_dummy_fixtures.py, tests/fixtures/dummy_*
- **Tests**: Ran scripts/doctor.py.
- **Exit codes**: 0
- **Limitations**: We are using standard pip and pyproject.toml without poetry/uv since standard venv is in use.
- **Next package**: B02 - Shared inference and preprocessing
