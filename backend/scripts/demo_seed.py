"""
QueueWise AI — Live Demo Dataset Seeder

Generates a realistic, rich demonstration state in the database:
- 12 completed tokens with realistic service durations and historical events
- 2 currently active/serving tokens at Counter 1 and Counter 2
- 8 waiting tokens across GEN, DOC, and CASH with priority mixes
- 2 skipped (no-show) and 1 cancelled token
- Immutable ServiceEvent records for all transactions

Run via:
    cd backend
    python -m scripts.demo_seed
"""
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
import random

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, delete

from app.core.config import settings
from app.models.token import Token, TokenStatus
from app.models.counter import Counter, CounterStatus
from app.models.service_category import ServiceCategory
from app.models.service_event import ServiceEvent, ServiceEventType
from app.models.notification import Notification
from app.core.seed import seed_initial_data


import sys
import io

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from typing import Optional

async def seed_demo_data(session: Optional[AsyncSession] = None):
    if session is not None:
        await _seed_demo_with_session(session)
        return

    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as sess:
        await _seed_demo_with_session(sess)


async def _seed_demo_with_session(session: AsyncSession):
        print("[1/5] Ensuring initial services and counters...")
        await seed_initial_data(session)

        # Retrieve services
        services_res = await session.execute(select(ServiceCategory))
        services = {s.code: s for s in services_res.scalars().all()}

        # Retrieve counters
        counters_res = await session.execute(select(Counter))
        counters = counters_res.scalars().all()
        c1 = next((c for c in counters if "1" in c.name), counters[0])
        c2 = next((c for c in counters if "2" in c.name), counters[1] if len(counters) > 1 else counters[0])

        # Reset counters and clean up any prior demo records for idempotency
        for c in counters:
            c.current_token_id = None
            c.status = CounterStatus.OPEN_IDLE
        await session.flush()

        prior_demo_res = await session.execute(
            select(Token.id).where(Token.public_id.like("demo-%"))
        )
        prior_ids = prior_demo_res.scalars().all()
        if prior_ids:
            await session.execute(
                delete(ServiceEvent).where(ServiceEvent.token_id.in_(prior_ids))
            )
            await session.execute(
                delete(Notification).where(Notification.token_id.in_(prior_ids))
            )
            await session.execute(
                delete(Token).where(Token.id.in_(prior_ids))
            )
            await session.flush()

        now = datetime.now(timezone.utc)
        session_id = "default"

        print("[2/5] Seeding completed historical tokens with service events...")
        # 12 completed tokens over the past 4 hours
        for i in range(1, 13):
            svc_code = random.choice(["GEN", "DOC", "CASH"])
            svc = services[svc_code]
            created_offset = random.randint(30, 240)  # minutes ago
            created_at = now - timedelta(minutes=created_offset)
            wait_duration = random.randint(180, 720)  # 3-12 min wait
            called_at = created_at + timedelta(seconds=wait_duration)
            service_duration = random.randint(120, 480)  # 2-8 min service
            completed_at = called_at + timedelta(seconds=service_duration)

            tok = Token(
                public_id=f"demo-hist-{i:03d}",
                display_number=f"{svc_code}-{i:03d}",
                service_category_id=svc.id,
                session_id=session_id,
                status=TokenStatus.COMPLETED,
                priority=5 if i % 4 == 0 else 0,
                created_at=created_at,
                called_at=called_at,
                service_started_at=called_at,
                completed_at=completed_at,
                called_counter_id=c1.id if i % 2 == 0 else c2.id,
            )
            session.add(tok)
            await session.flush()

            # Record lifecycle events
            session.add(ServiceEvent(
                token_id=tok.id,
                counter_id=tok.called_counter_id,
                event_type=ServiceEventType.TOKEN_CREATED,
                timestamp=created_at,
                reason="Citizen token issued at kiosk",
            ))
            session.add(ServiceEvent(
                token_id=tok.id,
                counter_id=tok.called_counter_id,
                event_type=ServiceEventType.TOKEN_CALLED,
                timestamp=called_at,
                reason="Counter staff called next token",
            ))
            session.add(ServiceEvent(
                token_id=tok.id,
                counter_id=tok.called_counter_id,
                event_type=ServiceEventType.TOKEN_COMPLETED,
                timestamp=completed_at,
                reason="Service successfully concluded",
            ))

        print("[3/5] Setting active serving tokens at Counter 1 and Counter 2...")
        # Currently serving tokens
        t_serv1 = Token(
            public_id="demo-serv-001",
            display_number="GEN-013",
            service_category_id=services["GEN"].id,
            session_id=session_id,
            status=TokenStatus.SERVING,
            priority=0,
            created_at=now - timedelta(minutes=15),
            called_at=now - timedelta(minutes=3),
            service_started_at=now - timedelta(minutes=3),
            called_counter_id=c1.id,
        )
        c1.status = CounterStatus.OPEN_SERVING
        c1.current_token_id = t_serv1.id
        session.add(t_serv1)

        t_serv2 = Token(
            public_id="demo-serv-002",
            display_number="DOC-014",
            service_category_id=services["DOC"].id,
            session_id=session_id,
            status=TokenStatus.SERVING,
            priority=5,
            created_at=now - timedelta(minutes=20),
            called_at=now - timedelta(minutes=5),
            service_started_at=now - timedelta(minutes=5),
            called_counter_id=c2.id,
        )
        c2.status = CounterStatus.OPEN_SERVING
        c2.current_token_id = t_serv2.id
        session.add(t_serv2)

        print("[4/5] Seeding live waiting queue (8 citizens waiting)...")
        waiting_configs = [
            ("GEN", 5, "Senior Citizen Assistance"),
            ("DOC", 0, "Passport verification"),
            ("CASH", 0, "Challan deposit"),
            ("GEN", 0, "Inquiry"),
            ("DOC", 5, "Emergency Medical Certificate"),
            ("CASH", 0, "License fee"),
            ("GEN", 0, "General query"),
            ("DOC", 0, "Document stamp"),
        ]

        for idx, (code, prio, contact) in enumerate(waiting_configs, start=15):
            t_wait = Token(
                public_id=f"demo-wait-{idx:03d}",
                display_number=f"{code}-{idx:03d}",
                service_category_id=services[code].id,
                session_id=session_id,
                status=TokenStatus.WAITING,
                priority=prio,
                contact_info=contact,
                created_at=now - timedelta(minutes=(25 - idx)),
            )
            session.add(t_wait)
            await session.flush()
            session.add(ServiceEvent(
                token_id=t_wait.id,
                event_type=ServiceEventType.TOKEN_CREATED,
                timestamp=t_wait.created_at,
                reason="Citizen joined waiting line",
            ))

        print("[5/5] Seeding skipped and cancelled tokens for churn analytics...")
        t_skip = Token(
            public_id="demo-skip-023",
            display_number="GEN-023",
            service_category_id=services["GEN"].id,
            session_id=session_id,
            status=TokenStatus.SKIPPED,
            created_at=now - timedelta(minutes=45),
            called_at=now - timedelta(minutes=35),
            called_counter_id=c1.id,
        )
        session.add(t_skip)

        t_cancel = Token(
            public_id="demo-cancel-024",
            display_number="CASH-024",
            service_category_id=services["CASH"].id,
            session_id=session_id,
            status=TokenStatus.CANCELLED,
            created_at=now - timedelta(minutes=50),
        )
        session.add(t_cancel)

        await session.commit()
        print("[OK] Demo dataset successfully populated!")
        print("   - 12 Completed Tokens with accurate service durations")
        print("   - 2 Actively Serving Counters (Counter 1: GEN-013, Counter 2: DOC-014)")
        print("   - 8 Waiting Tokens with Priority mix (GEN-015 to DOC-022)")
        print("   - 2 Skipped & Cancelled tokens for accurate telemetry")


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
