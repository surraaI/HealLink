import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://heallinkdb_user:zoK7URUjXB16hal9G2vZEJTn42ysGbFQ@dpg-d8e89l4m0tmc73ekqofg-a.oregon-postgres.render.com/heallinkdb"

async def delete_all_users():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Delete dependent data first (handle tables that might not exist)
        tables_to_delete = [
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
            "payments"
        ]
        
        for table in tables_to_delete:
            try:
                await session.execute(text(f"DELETE FROM {table}"))
                print(f"Deleted data from {table}")
            except Exception as e:
                print(f"Table {table} does not exist or error: {e}")
        
        # Delete users
        try:
            await session.execute(text("DELETE FROM providers"))
            print("Deleted providers")
        except Exception as e:
            print(f"Error deleting providers: {e}")
        
        try:
            await session.execute(text("DELETE FROM patients"))
            print("Deleted patients")
        except Exception as e:
            print(f"Error deleting patients: {e}")
        
        await session.commit()
        print("\nAll users and related data deleted successfully")

if __name__ == "__main__":
    asyncio.run(delete_all_users())