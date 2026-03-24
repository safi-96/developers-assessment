import uuid
from datetime import date
from typing import Any, Literal

from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.api.routes.worklogs.service import WorklogService
from app.models import (
    GenerateRemittancesRequest,
    GenerateRemittancesResponse,
    WorklogDetailPublic,
    WorklogsPublic,
)

router = APIRouter(tags=["worklogs"])


@router.get("/list-all-worklogs", response_model=WorklogsPublic)
def list_all_worklogs(
    session: SessionDep,
    current_user: CurrentUser,
    remittanceStatus: Literal["REMITTED", "UNREMITTED"] | None = None,
    periodStart: date | None = None,
    periodEnd: date | None = None,
) -> Any:
    return WorklogService.list_all_worklogs(
        session, current_user, remittanceStatus, periodStart, periodEnd
    )


@router.get("/worklogs/{worklog_id}", response_model=WorklogDetailPublic)
def read_worklog_detail(
    session: SessionDep, current_user: CurrentUser, worklog_id: uuid.UUID
) -> Any:
    return WorklogService.get_worklog_detail(session, current_user, worklog_id)


@router.post(
    "/generate-remittances-for-all-users", response_model=GenerateRemittancesResponse
)
def generate_remittances_for_all_users(
    session: SessionDep, current_user: CurrentUser, payload: GenerateRemittancesRequest
) -> Any:
    return WorklogService.generate_remittances_for_all_users(
        session, current_user, payload
    )
