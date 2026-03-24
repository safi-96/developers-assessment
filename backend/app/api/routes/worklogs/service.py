import uuid
from datetime import date
from typing import Any

from fastapi import HTTPException
from sqlmodel import Session, col, select

from app.models import (
    GenerateRemittancesRequest,
    GenerateRemittancesResponse,
    Remittance,
    RemittancePublic,
    TimeEntry,
    TimeEntryPublic,
    User,
    Worklog,
    WorklogDetailPublic,
    WorklogPublic,
    WorklogsPublic,
)


class WorklogService:
    @staticmethod
    def _entry_amount(entry: TimeEntry) -> float:
        if entry.is_removed or entry.is_disputed:
            return 0.0
        return entry.hours * entry.hourly_rate

    @staticmethod
    def _worklog_amount(entries: list[TimeEntry]) -> float:
        t = 0.0
        for e in entries:
            t += WorklogService._entry_amount(e)
        return round(t, 2)

    @staticmethod
    def _worklog_to_public(session: Session, worklog: Worklog) -> WorklogPublic:
        usr = session.get(User, worklog.owner_id)
        if usr is None:
            raise HTTPException(status_code=404, detail="User not found for worklog")
        entries = session.exec(
            select(TimeEntry).where(TimeEntry.worklog_id == worklog.id)
        ).all()
        amount = WorklogService._worklog_amount(entries)
        status = "REMITTED" if worklog.remittance_id else "UNREMITTED"
        return WorklogPublic(
            id=worklog.id,
            task_name=worklog.task_name,
            work_date=worklog.work_date,
            owner_id=worklog.owner_id,
            freelancer_email=usr.email,
            freelancer_name=usr.full_name,
            remittance_id=worklog.remittance_id,
            remittance_status=status,
            amount=amount,
            is_adjusted=worklog.is_adjusted,
        )

    @staticmethod
    def list_all_worklogs(
        session: Session,
        current_user: Any,
        remittance_status: str | None,
        period_start: date | None,
        period_end: date | None,
    ) -> WorklogsPublic:
        stmt = select(Worklog)
        if not current_user.is_superuser:
            stmt = stmt.where(Worklog.owner_id == current_user.id)
        if period_start:
            stmt = stmt.where(Worklog.work_date >= period_start)
        if period_end:
            stmt = stmt.where(Worklog.work_date <= period_end)
        if remittance_status == "REMITTED":
            stmt = stmt.where(col(Worklog.remittance_id).is_not(None))
        if remittance_status == "UNREMITTED":
            stmt = stmt.where(col(Worklog.remittance_id).is_(None))

        rows = session.exec(stmt).all()
        data = []
        total = 0.0
        for wl in rows:
            r = WorklogService._worklog_to_public(session, wl)
            total += r.amount
            data.append(r)
        return WorklogsPublic(data=data, count=len(data), total_amount=round(total, 2))

    @staticmethod
    def get_worklog_detail(
        session: Session, current_user: Any, worklog_id: uuid.UUID
    ) -> WorklogDetailPublic:
        wl = session.get(Worklog, worklog_id)
        if wl is None:
            raise HTTPException(status_code=404, detail="Worklog not found")
        if not current_user.is_superuser and wl.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not enough permissions")

        base = WorklogService._worklog_to_public(session, wl)
        entries = session.exec(
            select(TimeEntry).where(TimeEntry.worklog_id == wl.id)
        ).all()
        rows: list[TimeEntryPublic] = []
        for e in entries:
            rows.append(
                TimeEntryPublic(
                    id=e.id,
                    worklog_id=e.worklog_id,
                    description=e.description,
                    hours=e.hours,
                    hourly_rate=e.hourly_rate,
                    is_disputed=e.is_disputed,
                    is_removed=e.is_removed,
                    amount=round(WorklogService._entry_amount(e), 2),
                    created_at=e.created_at,
                )
            )
        return WorklogDetailPublic(**base.model_dump(), entries=rows)

    @staticmethod
    def generate_remittances_for_all_users(
        session: Session, current_user: Any, payload: GenerateRemittancesRequest
    ) -> GenerateRemittancesResponse:
        stmt = select(Worklog).where(
            Worklog.work_date >= payload.period_start,
            Worklog.work_date <= payload.period_end,
            col(Worklog.remittance_id).is_(None),
        )
        if not current_user.is_superuser:
            stmt = stmt.where(Worklog.owner_id == current_user.id)

        selected = []
        for wl in session.exec(stmt).all():
            if wl.id in payload.excluded_worklog_ids:
                continue
            if wl.owner_id in payload.excluded_user_ids:
                continue
            selected.append(wl)

        grouped: dict[uuid.UUID, list[Worklog]] = {}
        for wl in selected:
            if wl.owner_id not in grouped:
                grouped[wl.owner_id] = []
            grouped[wl.owner_id].append(wl)

        remits: list[RemittancePublic] = []
        done_worklog_ids: list[uuid.UUID] = []
        total = 0.0
        for owner_id, worklogs in grouped.items():
            owner_total = 0.0
            for wl in worklogs:
                entries = session.exec(
                    select(TimeEntry).where(TimeEntry.worklog_id == wl.id)
                ).all()
                owner_total += WorklogService._worklog_amount(entries)

            rm = Remittance(
                owner_id=owner_id,
                period_start=payload.period_start,
                period_end=payload.period_end,
                status="COMPLETED",
                total_amount=round(owner_total, 2),
            )
            session.add(rm)
            session.commit()
            session.refresh(rm)

            for wl in worklogs:
                wl.remittance_id = rm.id
                session.add(wl)
                session.commit()
                done_worklog_ids.append(wl.id)

            total += rm.total_amount
            remits.append(
                RemittancePublic(
                    id=rm.id,
                    owner_id=rm.owner_id,
                    period_start=rm.period_start,
                    period_end=rm.period_end,
                    status=rm.status,
                    total_amount=rm.total_amount,
                    created_at=rm.created_at,
                )
            )

        return GenerateRemittancesResponse(
            remittances=remits,
            processed_worklog_ids=done_worklog_ids,
            total_amount=round(total, 2),
        )
