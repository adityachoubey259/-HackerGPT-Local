"""FastAPI application startup smoke test."""

from __future__ import annotations

import asyncio

from backend.api.app import create_app


async def main() -> None:
    app = create_app()
    async with app.router.lifespan_context(app):
        print("startup smoke: ok")


if __name__ == "__main__":
    asyncio.run(main())
