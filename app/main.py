from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.deps import get_db
from app import models, schemas

app = FastAPI(title="Landman MVP API")

# MVP: hard-coded actor for attribution.
# Replace with real auth later.
ACTOR_USER_ID = "11111111-1111-1111-1111-111111111111"

@app.get("/health")
def health():
    return {"ok": True}

# -----------------------------
# Projects
# -----------------------------
@app.post("/projects", response_model=schemas.ProjectOut)
def create_project(payload: schemas.ProjectCreate, db: Session = Depends(get_db)):
    # Ensure actor exists (helps catch missing seed)
    actor = db.query(models.User).filter(models.User.id == ACTOR_USER_ID).first()
    if not actor:
        raise HTTPException(
            status_code=500,
            detail=f"Seed user missing. Insert user id={ACTOR_USER_ID} into users table."
        )

    p = models.Project(
        name=payload.name,
        client_name=payload.client_name,
        jurisdiction=payload.jurisdiction,
        created_by=ACTOR_USER_ID,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p

@app.get("/projects", response_model=list[schemas.ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.query(models.Project).order_by(models.Project.updated_at.desc()).all()

@app.get("/projects/{project_id}", response_model=schemas.ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)):
    p = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p

# -----------------------------
# Run sheet rows
# -----------------------------
@app.get("/projects/{project_id}/rows", response_model=list[schemas.RunSheetRowOut])
def list_rows(project_id: str, db: Session = Depends(get_db)):
    # Ensure project exists
    p = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    return (
        db.query(models.RunSheetRow)
        .filter(and_(
            models.RunSheetRow.project_id == project_id,
            models.RunSheetRow.is_deleted == False
        ))
        .order_by(models.RunSheetRow.row_order.asc())
        .all()
    )

@app.post("/projects/{project_id}/rows/bulk", response_model=list[schemas.RunSheetRowOut])
def bulk_create_rows(project_id: str, payload: schemas.BulkRowsCreate, db: Session = Depends(get_db)):
    # Ensure project exists
    p = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    # Ensure actor exists
    actor = db.query(models.User).filter(models.User.id == ACTOR_USER_ID).first()
    if not actor:
        raise HTTPException(
            status_code=500,
            detail=f"Seed user missing. Insert user id={ACTOR_USER_ID} into users table."
        )

    created: list[models.RunSheetRow] = []
    for r in payload.rows:
        row = models.RunSheetRow(
            project_id=project_id,
            row_order=r.row_order,
            instrument=r.instrument,
            volume=r.volume,
            page=r.page,
            grantor=r.grantor,
            grantee=r.grantee,
            exec_date=r.exec_date,
            filed_date=r.filed_date,
            legal_description=r.legal_description,
            notes=r.notes,
            created_by=ACTOR_USER_ID,
            updated_by=ACTOR_USER_ID,
            is_deleted=False,
        )
        db.add(row)
        created.append(row)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        # Most common MVP error: duplicate row_order per project (unique constraint)
        raise HTTPException(status_code=400, detail=f"Insert failed: {str(e)}")

    for row in created:
        db.refresh(row)
    return created

@app.patch("/rows/{row_id}", response_model=schemas.RunSheetRowOut)
def patch_row(row_id: str, payload: schemas.RunSheetRowPatch, db: Session = Depends(get_db)):
    row = db.query(models.RunSheetRow).filter(models.RunSheetRow.id == row_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(row, k, v)

    row.updated_by = ACTOR_USER_ID

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Update failed: {str(e)}")

    db.refresh(row)
    return row

@app.delete("/rows/{row_id}")
def soft_delete_row(row_id: str, db: Session = Depends(get_db)):
    row = db.query(models.RunSheetRow).filter(models.RunSheetRow.id == row_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    row.is_deleted = True
    row.deleted_by = ACTOR_USER_ID
    row.updated_by = ACTOR_USER_ID

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Delete failed: {str(e)}")

    return {"ok": True}
