"""
QueueWise AI — Services API Endpoints

CRUD and listing for institution service categories.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.service_category import ServiceCategory
from app.schemas.service import ServiceCategoryCreate, ServiceCategoryResponse

router = APIRouter()


@router.get("", response_model=List[ServiceCategoryResponse])
async def list_services(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """List all available service categories."""
    stmt = select(ServiceCategory)
    if active_only:
        stmt = stmt.where(ServiceCategory.is_active == True)
    stmt = stmt.order_by(ServiceCategory.name.asc())

    result = await db.execute(stmt)
    services = result.scalars().all()
    return list(services)


@router.post("", response_model=ServiceCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_service(
    payload: ServiceCategoryCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new service category."""
    # Check duplicate code
    stmt = select(ServiceCategory).where(ServiceCategory.code == payload.code.upper())
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Service with code '{payload.code.upper()}' already exists.",
        )

    service = ServiceCategory(
        name=payload.name,
        code=payload.code.upper(),
        description=payload.description,
        default_duration_seconds=payload.default_duration_seconds,
        priority_policy=payload.priority_policy,
        is_active=payload.is_active,
    )
    db.add(service)
    await db.commit()
    await db.refresh(service)
    return service
