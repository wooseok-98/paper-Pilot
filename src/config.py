import os
from pathlib import Path

# src/ -> 레포 루트
ROOT = Path(__file__).resolve().parent.parent

# 환경변수로 덮어쓸 수 있게 (Docker 볼륨 경로용)
DATA_DIR = Path(os.getenv("PAPERPILOT_DATA_DIR", ROOT / "data"))