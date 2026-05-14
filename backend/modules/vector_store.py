import os
import pickle
import numpy as np
from pathlib import Path
from loguru import logger
from backend.config import get_settings

settings = get_settings()

try:
    import faiss
    from sentence_transformers import SentenceTransformer
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("[VectorStore] faiss-cpu or sentence-transformers not installed. Semantic search disabled.")


class VectorStore:
    MODEL_NAME = "all-MiniLM-L6-v2"
    DIM = 384

    def __init__(self, index_path: str | None = None):
        self.index_path = Path(index_path or settings.faiss_index_path)
        self.index_path.mkdir(parents=True, exist_ok=True)
        self._model = None
        self._index = None
        self._metadata: list[dict] = []

        if FAISS_AVAILABLE:
            self._load_or_create()

    def _load_or_create(self):
        idx_file = self.index_path / "index.faiss"
        meta_file = self.index_path / "metadata.pkl"

        if idx_file.exists() and meta_file.exists():
            self._index = faiss.read_index(str(idx_file))
            with open(meta_file, "rb") as f:
                self._metadata = pickle.load(f)
            logger.info(f"[VectorStore] Loaded index with {self._index.ntotal} vectors")
        else:
            self._index = faiss.IndexFlatL2(self.DIM)
            self._metadata = []
            logger.info("[VectorStore] Created new FAISS index")

    @property
    def model(self):
        if self._model is None and FAISS_AVAILABLE:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.MODEL_NAME)
        return self._model

    def _embed(self, texts: list[str]) -> np.ndarray:
        return self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)

    def add(self, texts: list[str], metadata: list[dict]):
        if not FAISS_AVAILABLE:
            return
        vectors = self._embed(texts)
        self._index.add(vectors.astype("float32"))
        self._metadata.extend(metadata)
        self._save()
        logger.info(f"[VectorStore] Added {len(texts)} vectors (total: {self._index.ntotal})")

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        if not FAISS_AVAILABLE or self._index.ntotal == 0:
            return []
        vec = self._embed([query]).astype("float32")
        distances, indices = self._index.search(vec, min(top_k, self._index.ntotal))
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self._metadata):
                results.append({**self._metadata[idx], "distance": float(dist)})
        return results

    def _save(self):
        faiss.write_index(self._index, str(self.index_path / "index.faiss"))
        with open(self.index_path / "metadata.pkl", "wb") as f:
            pickle.dump(self._metadata, f)

    def add_job(self, job: dict):
        text = f"{job.get('title', '')} {job.get('company', '')} {job.get('description', '')}"
        self.add([text], [{"type": "job", "job_id": job.get("id"), "title": job.get("title")}])

    def add_profile_chunk(self, chunk: str, label: str):
        self.add([chunk], [{"type": "profile", "label": label}])

    def find_similar_jobs(self, profile_text: str, top_k: int = 10) -> list[dict]:
        return [r for r in self.search(profile_text, top_k=top_k) if r.get("type") == "job"]
