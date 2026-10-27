"""Download embedding and reranking models into the Hugging Face cache (~/.cache/huggingface)."""

from sentence_transformers import CrossEncoder, SentenceTransformer

BI_ENCODERS = [
    "sentence-transformers/all-MiniLM-L6-v2",  # ~90 MB, fast baseline
    "BAAI/bge-small-en-v1.5",                  # ~130 MB, stronger for retrieval
]
CROSS_ENCODERS = [
    "cross-encoder/ms-marco-MiniLM-L-6-v2",    # ~90 MB, fast reranker
    "BAAI/bge-reranker-base",                  # ~1.1 GB, stronger reranker
]

for name in BI_ENCODERS:
    model = SentenceTransformer(name)
    print(f"{name}: embedding dim {model.encode(['test']).shape[1]}, device {model.device}")

for name in CROSS_ENCODERS:
    model = CrossEncoder(name)
    score = model.predict([("Is there a top up limit?", "Top-up limits depend on your plan.")])
    print(f"{name}: test score {float(score[0]):.3f}")