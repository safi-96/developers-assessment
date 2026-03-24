import uuid
from datetime import date

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.models import TimeEntry, Worklog
from tests.utils.user import create_random_user


def _create_worklog_with_entries(db: Session) -> Worklog:
    usr = create_random_user(db)
    wl = Worklog(task_name="Test task", work_date=date(2026, 3, 10), owner_id=usr.id)
    db.add(wl)
    db.commit()
    db.refresh(wl)
    db.add(
        TimeEntry(
            worklog_id=wl.id,
            description="Feature work",
            hours=2.0,
            hourly_rate=25.0,
        )
    )
    db.commit()
    db.add(
        TimeEntry(
            worklog_id=wl.id,
            description="Fixes",
            hours=1.0,
            hourly_rate=25.0,
        )
    )
    db.commit()
    return wl


def test_list_all_worklogs(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    _create_worklog_with_entries(db)
    response = client.get(
        f"{settings.API_V1_STR}/list-all-worklogs",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert "data" in content
    assert "total_amount" in content
    assert content["count"] >= 1


def test_read_worklog_detail(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    wl = _create_worklog_with_entries(db)
    response = client.get(
        f"{settings.API_V1_STR}/worklogs/{wl.id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["id"] == str(wl.id)
    assert len(content["entries"]) == 2
    assert content["amount"] == 75.0


def test_read_worklog_detail_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/worklogs/{uuid.uuid4()}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Worklog not found"


def test_generate_remittances_for_all_users(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    wl = _create_worklog_with_entries(db)
    payload = {
        "period_start": "2026-03-01",
        "period_end": "2026-03-31",
        "excluded_worklog_ids": [],
        "excluded_user_ids": [],
    }
    response = client.post(
        f"{settings.API_V1_STR}/generate-remittances-for-all-users",
        headers=superuser_token_headers,
        json=payload,
    )
    assert response.status_code == 200
    content = response.json()
    assert "remittances" in content
    assert str(wl.id) in content["processed_worklog_ids"]
