$ErrorActionPreference = "Stop"
uv run python scripts/train_model.py
uv run python scripts/evaluate_model.py
uv run python scripts/audit_calibration.py
