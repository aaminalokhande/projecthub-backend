from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.dependencies.auth import get_current_user
from app.database import SessionLocal
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.dependencies.auth import require_admin

router = APIRouter(prefix="/projects", tags=["Projects"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    project: ProjectCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    # If team lead is provided, verify that user exists and is actually a team_lead
    if project.team_lead_id is not None:
        team_lead = db.query(User).filter(User.id == project.team_lead_id).first()

        if not team_lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assigned team lead user not found"
            )

        if team_lead.role != "team_lead":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned user is not a team lead"
            )

    new_project = Project(
        title=project.title,
        description=project.description,
        status=project.status,
        start_date=project.start_date,
        due_date=project.due_date,
        owner_id=current_user.id,   # admin who created the project
        team_lead_id=project.team_lead_id
    )

    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    return new_project

@router.get("/", response_model=List[ProjectResponse])
def get_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Admin sees all projects
    if current_user.role == "admin":
        projects = db.query(Project).all()
        return projects

    # Team lead sees only projects assigned to them
    elif current_user.role == "team_lead":
        projects = db.query(Project).filter(Project.team_lead_id == current_user.id).all()
        return projects

    # Employee sees no projects directly in v1
    elif current_user.role == "employee":
        return []

    # Any unexpected role
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid role"
    )


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project_by_id(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Admin can access any project
    if current_user.role == "admin":
        return project

    # Team lead can access only projects assigned to them
    if current_user.role == "team_lead":
        if project.team_lead_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to access this project"
            )
        return project

    # Employee cannot access project details directly in v1
    if current_user.role == "employee":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employees cannot access project details directly"
        )

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid role"
    )

@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # If admin is changing team lead, validate the new user
    if project_data.team_lead_id is not None:
        team_lead = db.query(User).filter(User.id == project_data.team_lead_id).first()

        if not team_lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assigned team lead user not found"
            )

        if team_lead.role != "team_lead":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned user is not a team lead"
            )

    # Update only provided fields
    if project_data.title is not None:
        project.title = project_data.title

    if project_data.description is not None:
        project.description = project_data.description

    if project_data.status is not None:
        project.status = project_data.status

    if project_data.start_date is not None:
        project.start_date = project_data.start_date

    if project_data.due_date is not None:
        project.due_date = project_data.due_date

    if project_data.team_lead_id is not None:
        project.team_lead_id = project_data.team_lead_id

    db.commit()
    db.refresh(project)

    return project


@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    db.delete(project)
    db.commit()

    return {"message": f"Project with id {project_id} deleted successfully"}
