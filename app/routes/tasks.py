from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import SessionLocal
from app.models.task import Task
from app.models.project import Project
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate, TaskStatusUpdate, TaskResponse
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/tasks", tags=["Tasks"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    task: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == task.project_id).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Admin can create task in any project
    if current_user.role == "admin":
        pass

    # Team lead can create task only in their assigned projects
    elif current_user.role == "team_lead":
        if project.team_lead_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can create tasks only in your assigned projects"
            )

    # Employee cannot create tasks
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employees are not allowed to create tasks"
        )

    # If assigned_to is given, validate employee exists
    if task.assigned_to is not None:
        assigned_user = db.query(User).filter(User.id == task.assigned_to).first()

        if not assigned_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assigned user not found"
            )

        if assigned_user.role != "employee":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tasks can only be assigned to employees"
            )

    new_task = Task(
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        due_date=task.due_date,
        project_id=task.project_id,
        assigned_to=task.assigned_to
    )

    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    return new_task


@router.get("/", response_model=List[TaskResponse])
def get_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Admin sees all tasks
    if current_user.role == "admin":
        return db.query(Task).all()

    # Team lead sees tasks only from their own projects
    elif current_user.role == "team_lead":
        return (
            db.query(Task)
            .join(Project, Task.project_id == Project.id)
            .filter(Project.team_lead_id == current_user.id)
            .all()
        )

    # Employee sees only tasks assigned to them
    elif current_user.role == "employee":
        return db.query(Task).filter(Task.assigned_to == current_user.id).all()

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid role"
    )


@router.get("/{task_id}", response_model=TaskResponse)
def get_task_by_id(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Admin can access any task
    if current_user.role == "admin":
        return task

    # Team lead can access task only if it belongs to their project
    if current_user.role == "team_lead":
        project = db.query(Project).filter(Project.id == task.project_id).first()

        if not project or project.team_lead_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to access this task"
            )
        return task

    # Employee can access only their assigned tasks
    if current_user.role == "employee":
        if task.assigned_to != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can access only your assigned tasks"
            )
        return task

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid role"
    )


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    task_data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    project = db.query(Project).filter(Project.id == task.project_id).first()

    # Admin can update any task
    if current_user.role == "admin":
        pass

    # Team lead can update only tasks of their own project
    elif current_user.role == "team_lead":
        if not project or project.team_lead_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can update tasks only in your assigned projects"
            )

    # Employee cannot use this full update route
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employees cannot fully update tasks"
        )

    # If assigned_to is being updated, validate employee
    if task_data.assigned_to is not None:
        assigned_user = db.query(User).filter(User.id == task_data.assigned_to).first()

        if not assigned_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assigned user not found"
            )

        if assigned_user.role != "employee":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tasks can only be assigned to employees"
            )

    if task_data.title is not None:
        task.title = task_data.title
    if task_data.description is not None:
        task.description = task_data.description
    if task_data.status is not None:
        task.status = task_data.status
    if task_data.priority is not None:
        task.priority = task_data.priority
    if task_data.due_date is not None:
        task.due_date = task_data.due_date
    if task_data.assigned_to is not None:
        task.assigned_to = task_data.assigned_to

    db.commit()
    db.refresh(task)

    return task


@router.put("/{task_id}/status", response_model=TaskResponse)
def update_my_task_status(
    task_id: int,
    task_data: TaskStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Only employee should use this route in v1
    if current_user.role != "employee":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employees can update task status here"
        )

    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    if task.assigned_to != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can update status only for your assigned tasks"
        )

    task.status = task_data.status

    db.commit()
    db.refresh(task)

    return task


@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    project = db.query(Project).filter(Project.id == task.project_id).first()

    # Admin can delete any task
    if current_user.role == "admin":
        pass

    # Team lead can delete only tasks from their own project
    elif current_user.role == "team_lead":
        if not project or project.team_lead_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can delete tasks only from your assigned projects"
            )

    # Employee cannot delete tasks
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employees are not allowed to delete tasks"
        )

    db.delete(task)
    db.commit()

    return {"message": f"Task with id {task_id} deleted successfully"}