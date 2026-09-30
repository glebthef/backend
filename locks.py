from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import User


async def lock_user(session: AsyncSession, user_id: int) -> User | None:
    stmt = (
        select(User).where(User.id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return await session.scalar(stmt)
