"""MiniFASNet anti-spoof adapter (real backend; runs on the household Mac).

Loads a Silent-Face MiniFASNet ONNX model (Apache-2.0) from ``PB_LIVENESS_MODEL`` and
runs it via onnxruntime — no extra pip dependency beyond the ``perception`` extra
(onnxruntime / numpy / pillow). The Silent-Face models are 3-class with index 1 = "real";
we softmax the output and accept when P(real) >= ``liveness_threshold``.

Design choice: this **fails open** (returns True) on a missing model / decode / inference
error and logs once, so a misconfigured liveness backend degrades to "no anti-spoof"
rather than bricking all enrollment. Set it up and verify on the Mac before relying on it.
"""

from __future__ import annotations

import io
import logging

_log = logging.getLogger("uvicorn.error")


class MiniFasnetLivenessDetector:
    def __init__(self, *, model: str, device: str = "cpu", threshold: float = 0.5) -> None:
        import onnxruntime as ort  # lazy: keeps CI import-safe without the extra

        if not model:
            raise ValueError("PB_LIVENESS_MODEL must point to a MiniFASNet .onnx file")
        providers = ["CUDAExecutionProvider"] if device == "cuda" else ["CPUExecutionProvider"]
        self._sess = ort.InferenceSession(model, providers=providers)
        self._input = self._sess.get_inputs()[0]
        self._threshold = threshold
        _log.info("MiniFasnetLivenessDetector ready model=%s thr=%.2f", model, threshold)

    async def check(self, image: bytes) -> bool:
        if not image:
            return False
        try:
            import numpy as np
            from PIL import Image

            # Input is NCHW (1, 3, H, W); resize the decoded crop to the model's size.
            _, _, h, w = self._input.shape
            pil = Image.open(io.BytesIO(image)).convert("RGB").resize((int(w), int(h)))
            arr = np.asarray(pil, dtype="float32") / 255.0  # HWC, [0,1]
            blob = np.transpose(arr, (2, 0, 1))[np.newaxis, :, :, :]  # NCHW
            out = self._sess.run(None, {self._input.name: blob})[0].reshape(-1)
            exp = np.exp(out - out.max())
            probs = exp / exp.sum()
            # Silent-Face MiniFASNet: class index 1 is the "real / live" class.
            live = float(probs[1]) if probs.shape[0] > 1 else float(probs[0])
            return live >= self._threshold
        except Exception as exc:  # fail open: log once, don't block enrollment
            _log.warning("liveness check failed, allowing frame: %r", exc)
            return True
