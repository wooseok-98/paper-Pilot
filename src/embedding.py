"""임베딩 모델 래퍼 — 글을 의미 벡터로 바꾸는 공용 모듈"""

from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_model = SentenceTransformer(MODEL_NAME)     # 모듈 로드 시 딱 한 번만 로딩

def embed(texts: list[str]):
    return _model.encode(texts, normalize_embeddings=True)
