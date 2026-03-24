from datetime import date

from sqlmodel import Session, col, create_engine, select

from app import crud
from app.core.config import settings
from app.models import TimeEntry, User, UserCreate, Worklog

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    # This works because the models are already imported and registered from app.models
    # SQLModel.metadata.create_all(engine)

    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
        )
        user = crud.create_user(session=session, user_create=user_in)

    def add_demo_worklogs(
        worklogs: list[tuple[Worklog, list[tuple[str, float, float]]]]
    ) -> None:
        for wl, entry_specs in worklogs:
            session.add(wl)
            session.commit()
            session.refresh(wl)
            for desc, hrs, rate in entry_specs:
                session.add(
                    TimeEntry(
                        worklog_id=wl.id,
                        description=desc,
                        hours=hrs,
                        hourly_rate=rate,
                    )
                )
                session.commit()

    existing = session.exec(select(Worklog).limit(1)).first()
    if not existing:
        add_demo_worklogs(
            [
                (
                    Worklog(
                        task_name="Landing page redesign",
                        work_date=date(2026, 3, 1),
                        owner_id=user.id,
                    ),
                    [
                        ("Implementation work", 3.0, 35.0),
                        ("QA and revisions", 1.5, 35.0),
                    ],
                ),
                (
                    Worklog(
                        task_name="Checkout bug fixes",
                        work_date=date(2026, 3, 3),
                        owner_id=user.id,
                    ),
                    [
                        ("Implementation work", 2.5, 40.0),
                        ("QA and revisions", 1.0, 40.0),
                    ],
                ),
                (
                    Worklog(
                        task_name="Analytics integration",
                        work_date=date(2026, 3, 10),
                        owner_id=user.id,
                    ),
                    [
                        ("Implementation work", 4.0, 28.0),
                        ("QA and revisions", 1.0, 28.0),
                    ],
                ),
            ]
        )

    unr = session.exec(select(Worklog).where(col(Worklog.remittance_id).is_(None))).all()
    if len(unr) >= 2:
        return

    add_demo_worklogs(
        [
            (
                Worklog(
                    task_name="Urgent production support",
                    work_date=date(2026, 3, 22),
                    owner_id=user.id,
                ),
                [
                    ("Implementation work", 1.5, 60.0),
                    ("QA and revisions", 0.5, 60.0),
                ],
            ),
            (
                Worklog(
                    task_name="Post-release QA patching",
                    work_date=date(2026, 3, 23),
                    owner_id=user.id,
                ),
                [
                    ("Implementation work", 2.0, 45.0),
                    ("QA and revisions", 1.0, 45.0),
                ],
            ),
        ]
    )
