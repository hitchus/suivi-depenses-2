import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.recurring import RecurringRuleCreate, RecurringRuleResponse
from app.services import recurring_service

router = APIRouter(prefix="/recurring", tags=["recurring"])


@router.get("", response_model=list[RecurringRuleResponse])
async def list_rules(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await recurring_service.get_rules(db, current_user.id)


@router.post("", response_model=RecurringRuleResponse, status_code=201)
async def create_rule(
    body: RecurringRuleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await recurring_service.create_rule(db, current_user.id, body)


@router.delete("/{rule_id}", response_model=RecurringRuleResponse)
async def deactivate_rule(
    rule_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await recurring_service.deactivate_rule(db, rule_id, current_user.id)
