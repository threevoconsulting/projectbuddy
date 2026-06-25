"""Diagnose the InsightFace recognition adapter on real photos (Mac only).

Why: live recognition returned near-zero cosine for the SAME face, which should be
impossible for a working ArcFace model. This isolates whether the problem is our
adapter, the model load, or non-deterministic embeddings.

Usage (save a few JP/PNG photos first; two of the same person + one of another helps):

    uv run python scripts/diag_face.py face1.jpg face2.jpg other.jpg

It prints: the insightface version/path, which sub-models loaded, the embedding norm,
a DETERMINISM check (same file embedded twice → cosine should be ~1.0), and pairwise
cosines between the photos.
"""

from __future__ import annotations

import sys

import numpy as np
from PIL import Image


def main() -> None:
    import insightface
    from insightface.app import FaceAnalysis

    print(f"insightface {getattr(insightface, '__version__', '?')} @ {insightface.__file__}")

    app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
    app.prepare(ctx_id=-1, det_size=(640, 640))
    print("loaded sub-models:", list(getattr(app, "models", {}).keys()))

    def embed(path: str) -> np.ndarray | None:
        pil = Image.open(path).convert("RGB")
        bgr = np.ascontiguousarray(np.asarray(pil)[:, :, ::-1])  # RGB -> BGR
        faces = app.get(bgr)
        print(f"  {path}: {len(faces)} face(s), image {pil.size}")
        if not faces:
            return None
        f = max(faces, key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]))
        e = np.asarray(f.embedding, dtype="float32")
        n = float(np.linalg.norm(e))
        normed = hasattr(f, "normed_embedding")
        print(f"     embedding dim={e.shape[0]} norm={n:.3f} has_normed={normed}")
        return e / n if n else None

    def cos(a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b))

    paths = sys.argv[1:]
    if not paths:
        print("Pass image paths, e.g. uv run python scripts/diag_face.py me1.jpg me2.jpg")
        return

    print("\n== embeddings ==")
    embs = [embed(p) for p in paths]

    print("\n== determinism (same file twice; want ~1.000) ==")
    a = embed(paths[0])
    b = embed(paths[0])
    if a is not None and b is not None:
        print(f"  cosine(same image, twice) = {cos(a, b):.3f}")

    print("\n== pairwise cosine ==")
    for i in range(len(paths)):
        for j in range(i + 1, len(paths)):
            if embs[i] is not None and embs[j] is not None:
                print(f"  {paths[i]}  vs  {paths[j]} = {cos(embs[i], embs[j]):.3f}")


if __name__ == "__main__":
    main()
