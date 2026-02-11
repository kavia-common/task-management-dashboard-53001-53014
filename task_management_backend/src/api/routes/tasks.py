import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.db.models import Task, User
from src.api.db.session import get_db
from src.api.realtime.manager import manager
from src.api.schemas import TaskCreate, TaskPublic, TaskUpdate
from src.api.security.auth import get_current_user

router = APIRouter(prefix="/tasks", tags=["tasks"])

_ALLOWED_SORT_FIELDS = {
    "created_at": Task.created_at,
    "updated_at": Task.updated_at,
    "due_date": Task.due_date,
    "priority": Task.priority,
    "status": Task.status,
    "title": Task.title,
}


def _task_to_public(task: Task) -> TaskPublic:
    return TaskPublic.model_validate(task, from_attributes=True)


async def _broadcast_task_event(event: str, task: Task) -> None:
    await manager.broadcast(
        {
            "type": "task_event",
            "event": event,  # created|updated|deleted
            "task": _task_to_public(task).model_dump(mode="json"),
            "ts": datetime.utcnow().isoformat() + "Z",
        }
    )


@router.post(
    "",
    response_model=TaskPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Create task",
    description="Create a task for the authenticated user.",
    operation_id="create_task",
)
async def create_task(
    payload: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskPublic:
    """Create a new task."""
    task = Task(
        owner_id=current_user.id,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        due_date=payload.due_date,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    await _broadcast_task_event("created", task)
    return _task_to_public(task)


@router.get(
    "",
    response_model=list[TaskPublic],
    summary="List tasks",
    description=(
        "List tasks for the authenticated user with filtering and sorting.\n\n"
        "Filters:\n"
        "- status: todo|in_progress|done\n"
        "- priority: low|medium|high\n"
        "- q: text search in title/description\n\n"
        "Sorting:\n"
        "- sort_by: created_at|updated_at|due_date|priority|status|title\n"
        "- sort_dir: asc|desc"
    ),
    operation_id="list_tasks",
)
async def list_tasks(
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    priority: str | None = Query(None, description="Filter by priority"),
    q: str | None = Query(None, description="Search in title/description"),
    sort_by: str = Query("updated_at", description="Sort field"),
    sort_dir: str = Query("desc", description="Sort direction: asc|desc"),
    limit: int = Query(50, ge=1, le=200, description="Page size"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TaskPublic]:
    """List tasks belonging to current user."""
    stmt: Select[tuple[Task]] = select(Task).where(Task.owner_id == current_user.id)

    if status_filter:
        stmt = stmt.where(Task.status == status_filter)
    if priority:
        stmt = stmt.where(Task.priority == priority)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(func.lower(Task.title).like(like) | func.lower(Task.description).like(like))

    sort_col = _ALLOWED_SORT_FIELDS.get(sort_by, Task.updated_at)
    if sort_dir.lower() == "asc":
        stmt = stmt.order_by(sort_col.asc().nullslast())
    else:
        stmt = stmt.order_by(sort_col.desc().nullslast())

    stmt = stmt.limit(limit).offset(offset)
    res = await db.execute(stmt)
    tasks = res.scalars().all()
    return [_task_to_public(t) for t in tasks]


@router.get(
    "/{task_id}",
    response_model=TaskPublic,
    summary="Get task",
    description="Fetch a single task by id (must belong to current user).",
    operation_id="get_task",
)
async def get_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskPublic:
    """Get a task."""
    res = await db.execute(select(Task).where(Task.id == task_id, Task.owner_id == current_user.id))
    task = res.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_to_public(task)


@router.patch(
    "/{task_id}",
    response_model=TaskPublic,
    summary="Update task",
    description="Update task fields (must belong to current user).",
    operation_id="update_task",
)
async def update_task(
    task_id: uuid.UUID,
    payload: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskPublic:
    """Update a task."""
    res = await db.execute(select(Task).where(Task.id == task_id, Task.owner_id == current_user.id))
    task = res.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if payload.title is not None:
        task.title = payload.title
    if payload.description is not None:
        task.description = payload.description
    if payload.status is not None:
        task.status = payload.status
    if payload.priority is not None:
        task.priority = payload.priority
    if payload.due_date is not None:
        task.due_date = payload.due_date

    await db.commit()
    await db.refresh(task)

    await _broadcast_task_event("updated", task)
    return _task_to_public(task)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete task",
    description="Delete a task (must belong to current user).",
    operation_id="delete_task",
)
async def delete_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a task."""
    res = await db.execute(select(Task).where(Task.id == task_id, Task.owner_id == current_user.id))
    task = res.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    await db.delete(task)
    await db.commit()

    # Broadcast with minimal payload; reuse TaskPublic derived from the object before deletion.
    await _broadcast_task_event("deleted", task)
    return None
