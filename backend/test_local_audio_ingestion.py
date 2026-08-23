import asyncio

from app.db.database import AsyncSessionLocal
from app.services.local_audio_ingestion import (
    ingest_local_audio_features,
)


async def main():
    async with AsyncSessionLocal() as db:
        result = await ingest_local_audio_features(
            db
        )

        print()
        print("========== INGESTION RESULT ==========")
        print(result)
        print("======================================")
        print()


if __name__ == "__main__":
    asyncio.run(main())