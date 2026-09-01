from __future__ import annotations

import asyncio

from app.dependencies import get_ingestion_manager


async def main() -> None:
    manager = get_ingestion_manager()
    result = await manager.ingest_document("")
    print(result.model_dump())


if __name__ == "__main__":
    asyncio.run(main())
