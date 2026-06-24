"""``python -m projectbuddy`` — run the backend with uvicorn."""

from __future__ import annotations

import uvicorn

from projectbuddy.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "projectbuddy.app:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
    )


if __name__ == "__main__":
    main()
