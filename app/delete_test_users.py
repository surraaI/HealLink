import asyncio
import os
import sys
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine


ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings


TABLES_TO_DELETE = [
    "notifications",
    "qr_checkins",
    "refresh_tokens",
    "appointments",
    "service_slots",
    "service_catalog",
    "account_action_tokens",
    "provider_schedules",
    "diagnostic_results",
    "reviews",
    "payments",
    "providers",
    "patients",
]

async def delete_all_users():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        existing_tables = await conn.run_sync(
            lambda sync_conn: set(inspect(sync_conn).get_table_names(schema="public"))
        )
        tables_to_clear = [table for table in TABLES_TO_DELETE if table in existing_tables]
        skipped_tables = [table for table in TABLES_TO_DELETE if table not in existing_tables]

        if tables_to_clear:
            quoted_tables = ", ".join(f'"{table}"' for table in tables_to_clear)
            await conn.execute(text(f"TRUNCATE TABLE {quoted_tables} RESTART IDENTITY CASCADE"))
            print(f"Cleared tables: {', '.join(tables_to_clear)}")

        if skipped_tables:
            print(f"Skipped missing tables: {', '.join(skipped_tables)}")

    print("\nAll users and related data deleted successfully")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(delete_all_users())