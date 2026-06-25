"""InsightFace adapter (real backend; runs on the household Mac).

Uses InsightFace's ``buffalo_l`` pretrained pack (a non-commercial license, fine for
this personal/home-use project). ``insightface``, ``onnxruntime`` and ``numpy`` are
imported lazily inside the methods so this module stays import-safe in CI, where the
``perception`` extra is not installed. Install on the Mac with
``uv sync --extra perception`` and select with ``PB_RECOGNITION_BACKEND=insightface``.

We run recognition explicitly: detect → align the face by its 5 keypoints
(``norm_crop``) → embed with the recognition model. This is the canonical path and
avoids relying on ``FaceAnalysis.get`` populating ``face.embedding`` (which behaved
as a non-identity vector in some builds).
"""

from __future__ import annotations

import io
import logging

from projectbuddy.models.recognition.base import FaceRecognizer

# Logs to uvicorn's configured logger so diagnostics show in the run-mac terminal.
_log = logging.getLogger("uvicorn.error")


class InsightFaceRecognizer(FaceRecognizer):
    def __init__(self, *, model: str = "buffalo_l", device: str = "cpu") -> None:
        # Lazy import: keeps CI/import safe without the perception extra installed.
        from insightface.app import FaceAnalysis

        providers = ["CUDAExecutionProvider"] if device == "cuda" else ["CPUExecutionProvider"]
        self._app = FaceAnalysis(name=model, providers=providers)
        self._app.prepare(ctx_id=0 if device == "cuda" else -1, det_size=(640, 640))
        self._rec = self._app.models.get("recognition")
        rec_name = type(self._rec).__name__ if self._rec is not None else "MISSING"
        # Startup marker so we can confirm exactly which adapter build is live.
        _log.info("InsightFaceRecognizer ready [aligned-v3] model=%s rec=%s", model, rec_name)

    async def embed(self, image: bytes) -> list[float] | None:
        if not image:
            return None
        import numpy as np
        from PIL import Image

        try:
            pil = Image.open(io.BytesIO(image)).convert("RGB")
        except Exception:
            return None
        # InsightFace/OpenCV expect BGR; our PIL decode is RGB, so swap channels.
        bgr = np.ascontiguousarray(np.asarray(pil)[:, :, ::-1])
        faces = self._app.get(bgr)
        if not faces:
            return None
        face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))

        emb = None
        kps = getattr(face, "kps", None)
        # Canonical recognition: align by keypoints, then run the recognition model.
        try:
            from insightface.utils import face_align

            if self._rec is not None and kps is not None:
                aimg = face_align.norm_crop(bgr, landmark=kps, image_size=112)
                emb = np.asarray(self._rec.get_feat(aimg), dtype="float32").flatten()
        except Exception as exc:  # log and fall back to face.embedding
            _log.info("explicit align/get_feat failed: %r", exc)

        if emb is None or emb.size == 0:
            emb = np.asarray(face.embedding, dtype="float32")

        det = float(getattr(face, "det_score", 0.0))
        _log.info(
            "embed: faces=%d det=%.2f kps=%s emb_norm=%.2f",
            len(faces),
            det,
            kps is not None,
            float(np.linalg.norm(emb)),
        )

        norm = float(np.linalg.norm(emb))
        if norm == 0.0:
            return None
        return [float(x) for x in (emb / norm)]
