import asyncio
import os
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.provider import Provider, ProviderType


async def create_doctor():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    email = "rabumamilisha@gmail.com"
    password = "rabumamilisha@gmail.com"
    
    async with async_session() as session:
        # Check if doctor already exists
        from sqlalchemy import select
        existing = await session.scalar(select(Provider).where(Provider.email == email))
        if existing:
            print(f"Doctor with email {email} already exists")
            return
        
        # Create new doctor
        doctor = Provider(
            name="Dr. Rabu Mamilisha",
            provider_type=ProviderType.DOCTOR,
            email=email,
            hashed_password=hash_password(password),
            phone="+250788123456",
            specialization="General Medicine",
            license_number="MED-2024-001",
            tin_number="100123456789",
            location="Kigali",
            address="Kigali, Rwanda",
            description="General practitioner with expertise in family medicine",
            is_verified=True,  # Email verified
            verification_status="approved",  # Documents verified
        )
        
        session.add(doctor)
        await session.commit()
        await session.refresh(doctor)
        
        print(f"Doctor created successfully!")
        print(f"Email: {email}")
        print(f"Password: {password}")
        print(f"Email Verified: True")
        print(f"Documents Verified: True")
        print(f"Provider ID: {doctor.id}")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_doctor())
