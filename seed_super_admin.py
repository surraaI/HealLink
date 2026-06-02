import asyncio
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.super_admin import SuperAdmin
from sqlalchemy import select


async def seed_super_admin():
    email = "superadmin@heallink.com"
    password = "SuperAdmin123!"
    full_name = "Super Admin"

    async with AsyncSessionLocal() as session:
        # Check if super admin already exists
        result = await session.execute(select(SuperAdmin).where(SuperAdmin.email == email))
        existing = result.scalar_one_or_none()

        if existing:
            print(f"Super admin with email {email} already exists.")
            return

        # Create super admin
        hashed_pw = hash_password(password)
        admin = SuperAdmin(
            email=email,
            hashed_password=hashed_pw,
            full_name=full_name,
            is_active=True,
        )
        session.add(admin)
        await session.commit()
        print(f"Super admin created successfully!")
        print(f"Email: {email}")
        print(f"Password: {password}")
        print(f"Full Name: {full_name}")


if __name__ == "__main__":
    asyncio.run(seed_super_admin())
