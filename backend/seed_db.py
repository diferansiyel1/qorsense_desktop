#!/usr/bin/env python3
"""
Database Seed Script

Creates initial demo data for the QorSense application:
- Pikolab Demo Org organization
- Super admin user (super_admin role)

Usage:
    python -m backend.seed_db
    
Or from project root:
    python backend/seed_db.py
"""

import asyncio
import sys
import os
import uuid

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import AsyncSessionLocal, engine, Base
from backend.models_db import Organization, User, Role
from backend.core.security import get_password_hash


# ==============================================================================
# SEED DATA CONFIGURATION
# ==============================================================================

DEMO_ORG = {
    "id": "pikolab-demo-0001",
    "name": "Pikolab Demo Org",
    "subscription_plan": "Enterprise",
}

SUPER_ADMIN_USER = {
    "email": "admin@pikolab.com",
    "password": "admin123",  # Will be hashed
    "full_name": "Pikolab Super Admin",
    "role": Role.SUPER_ADMIN,
}


# ==============================================================================
# SEED FUNCTIONS
# ==============================================================================

async def seed_organization(db: AsyncSession) -> Organization:
    """
    Create or get the demo organization.
    
    Returns existing org if already exists.
    """
    # Check if org already exists
    result = await db.execute(
        select(Organization).where(Organization.name == DEMO_ORG["name"])
    )
    existing_org = result.scalar_one_or_none()
    
    if existing_org:
        print(f"✓ Organization '{DEMO_ORG['name']}' already exists (ID: {existing_org.id})")
        return existing_org
    
    # Create new organization
    org = Organization(
        id=DEMO_ORG["id"],
        name=DEMO_ORG["name"],
        subscription_plan=DEMO_ORG["subscription_plan"],
    )
    db.add(org)
    await db.flush()
    
    print(f"✓ Created organization '{org.name}' (ID: {org.id})")
    return org


async def seed_super_admin(db: AsyncSession, org: Organization) -> User:
    """
    Create or get the super admin user.
    
    Returns existing user if already exists.
    """
    email = SUPER_ADMIN_USER["email"]
    
    # Check if user already exists
    result = await db.execute(
        select(User).where(User.email == email)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        print(f"✓ User '{email}' already exists (ID: {existing_user.id})")
        return existing_user
    
    # Create new user
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        hashed_password=get_password_hash(SUPER_ADMIN_USER["password"]),
        full_name=SUPER_ADMIN_USER["full_name"],
        role=SUPER_ADMIN_USER["role"],
        organization_id=org.id,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    
    print(f"✓ Created super admin user '{email}' (ID: {user.id})")
    print(f"  Password: {SUPER_ADMIN_USER['password']}")
    return user


async def run_seed():
    """
    Main seed function.
    
    Creates all demo data in a single transaction.
    """
    print("=" * 50)
    print("QorSense Database Seed Script")
    print("=" * 50)
    print()
    
    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSessionLocal() as db:
        try:
            # Seed organization
            org = await seed_organization(db)
            
            # Seed super admin
            user = await seed_super_admin(db, org)
            
            # Commit all changes
            await db.commit()
            
            print()
            print("=" * 50)
            print("✅ Seed completed successfully!")
            print("=" * 50)
            print()
            print("Login credentials:")
            print(f"  Email:    {SUPER_ADMIN_USER['email']}")
            print(f"  Password: {SUPER_ADMIN_USER['password']}")
            print(f"  Role:     {SUPER_ADMIN_USER['role'].value}")
            print()
            
        except Exception as e:
            await db.rollback()
            print(f"❌ Seed failed: {e}")
            raise


def main():
    """Entry point for the seed script."""
    asyncio.run(run_seed())


if __name__ == "__main__":
    main()
