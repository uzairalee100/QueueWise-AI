"""
QueueWise AI — Initial Data Seeder

Seeds standard service categories and counters for development, testing,
and instant demo readiness.
"""
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.service_category import ServiceCategory
from app.models.counter import Counter
from app.models.enums import CounterStatus
from app.core.logging import get_logger

logger = get_logger(__name__)

DEFAULT_SERVICES = [
    {
        "name": "General Inquiries & Token Issuance",
        "code": "GEN",
        "description": "General assistance, reception, and info desk",
        "default_duration_seconds": 180,  # 3 minutes
        "priority_policy": "FIFO",
    },
    {
        "name": "Document Verification & Submissions",
        "code": "DOC",
        "description": "Official paperwork, certificate verification, and identity checks",
        "default_duration_seconds": 360,  # 6 minutes
        "priority_policy": "FIFO",
    },
    {
        "name": "Cashier & Fee Payments",
        "code": "CASH",
        "description": "Fee deposits, fine payments, and receipt collection",
        "default_duration_seconds": 240,  # 4 minutes
        "priority_policy": "FIFO",
    },
]

DEFAULT_COUNTERS = [
    {"name": "Counter 1", "status": CounterStatus.OPEN_IDLE},
    {"name": "Counter 2", "status": CounterStatus.OPEN_IDLE},
    {"name": "Counter 3", "status": CounterStatus.CLOSED},
]


async def seed_initial_data(session: AsyncSession) -> None:
    """Populate default services and counters if none exist."""
    # Check if services already exist
    count_services = await session.execute(select(func.count(ServiceCategory.id)))
    if (count_services.scalar() or 0) == 0:
        created_services = []
        for svc_data in DEFAULT_SERVICES:
            svc = ServiceCategory(**svc_data, is_active=True)
            session.add(svc)
            created_services.append(svc)
        await session.flush()
        logger.info("seeded_services", count=len(created_services))

        # Check if counters exist
        count_counters = await session.execute(select(func.count(Counter.id)))
        if (count_counters.scalar() or 0) == 0:
            for counter_data in DEFAULT_COUNTERS:
                counter = Counter(**counter_data)
                # Assign all default services to each counter initially
                counter.supported_services = list(created_services)
                session.add(counter)
            await session.flush()
            logger.info("seeded_counters", count=len(DEFAULT_COUNTERS))

        await session.commit()
