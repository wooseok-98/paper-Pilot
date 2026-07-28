"""pytest가 자동으로 먼저 읽는 파일 — src를 import 경로에 추가

소스가 `from search import ...`, `from agents.qa import ...` 처럼
src를 루트로 가정하고 import하므로, 테스트에서도 src를 sys.path에 넣어준다.
이 파일 덕분에 프로젝트 루트에서 그냥 `pytest`만 쳐도 됨.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))     # 소스 모듈 (search, agents.*, graph ...)
sys.path.insert(0, str(ROOT / "eval"))    # 평가 지표 (metrics)
