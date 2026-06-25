"""InsightFace adapter (real backend; runs on the household Mac).

Uses InsightFace's ``buffalo_l`` pretrained pack (a non-commercial license, fine for
this personal/home-use project). ``insightface``, ``onnxruntime`` and ``numpy`` are
imported lazily inside the methods so this module stays import-safe in CI, where the
``perception`` extra is not installed. Install on the Mac with
``uv sync --extra perception`` and select with ``PB_RECOGNITION_BACKEND=insightface``.
"""

from __future__ import annotations

import io

from projectbuddy.models.recognition.base import FaceRecognizer


class InsightFaceRecognizer(FaceRecognizer):
    def __init__(self, *, model: str = "buffalo_l", device: str = "cpu") -> None:
        # Lazy import: keeps CI/import safe without the perception extra installed.
        from insightface.app import FaceAnalysis

        providers = ["CUDAExecutionProvider"] if device == "cuda" else ["CPUExecutionProvider"]
        self._app = FaceAnalysis(name=model, providers=providers)
        self._app.prepare(ctx_id=0 if device == "cuda" else -1, det_size=(640, 640))

    async def embed(self, image: bytes) -> list[float] | None:
        if not image:
            return None
        import numpy as np
        from PIL import Image

        try:
            pil = Image.open(io.BytesIO(image)).convert("RGB")
        except Exception:
            return None
        # InsightFace is built on OpenCV and expects BGR; feeding RGB swaps the red/blue
        # channels, which leaves the recognizer off-distribution and its embeddings
        # unstable (near-orthogonal for the same face). Convert RGB→BGR first.
        bgr = np.ascontiguousarray(np.asarray(pil)[:, :, ::-1])
        faces = self._app.get(bgr)
        if not faces:
            return None
        # The most prominent face wins (largest bounding box).
        face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        # Use the raw embedding and L2-normalize ourselves so cosine matching is robust
        # regardless of whether this insightface version pre-normalizes.
        emb = np.asarray(face.embedding, dtype="float32")
        norm = float(np.linalg.norm(emb))
        if norm == 0.0:
            return None
        return [float(x) for x in (emb / norm)]
