from datetime import date, datetime
from fastapi import APIRouter, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.deps import get_db
from app import models

router = APIRouter(prefix="/ui", tags=["ui"])
templates = Jinja2Templates(directory="templates")

# MVP: hard-coded actor for attribution
ACTOR_USER_ID = "11111111-1111-1111-1111-111111111111"

@router.get("", response_class=HTMLResponse)
def ui_root():
    return RedirectResponse(url="/ui/projects", status_code=302)

@router.get("/projects", response_class=HTMLResponse)
def projects_page(request: Request, db: Session = Depends(get_db)):
    projects = db.query(models.Project).order_by(models.Project.updated_at.desc()).all()
    return templates.TemplateResponse(
        "projects.html",
        {"request": request, "projects": projects, "title": "Projects"},
    )

@router.post("/projects")
def create_project(
    name: str = Form(...),
    client_name: str = Form(""),
    jurisdiction: str = Form(""),
    db: Session = Depends(get_db),
):
    # Ensure actor exists (matches your DB FK constraints)
    actor = db.query(models.User).filter(models.User.id == ACTOR_USER_ID).first()
    if not actor:
        # if you haven't seeded the actor user yet, do that first
        return RedirectResponse(url="/ui/projects?error=seed_user_missing", status_code=302)

    p = models.Project(
        name=name.strip(),
        client_name=(client_name.strip() or None),
        jurisdiction=(jurisdiction.strip() or None),
        created_by=ACTOR_USER_ID,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return RedirectResponse(url=f"/ui/projects/{p.id}", status_code=302)

@router.get("/projects/{project_id}", response_class=HTMLResponse)
def project_detail(request: Request, project_id: str, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        return RedirectResponse(url="/ui/projects", status_code=302)

    rows = (
        db.query(models.RunSheetRow)
        .filter(and_(models.RunSheetRow.project_id == project_id, models.RunSheetRow.is_deleted == False))
        .order_by(models.RunSheetRow.row_order.asc())
        .all()
    )

    # Suggest next row_order (10,20,30...) based on max
    max_order = (
        db.query(func.max(models.RunSheetRow.row_order))
        .filter(and_(models.RunSheetRow.project_id == project_id, models.RunSheetRow.is_deleted == False))
        .scalar()
    )
    next_row_order = 10 if not max_order else int(max_order) + 10

    return templates.TemplateResponse(
        "project_detail.html",
        {"request": request, "project": project, "rows": rows, "next_row_order": next_row_order, "title": project.name},
    )

@router.post("/projects/{project_id}/rows")
def add_row(
    project_id: str,
    row_order: int = Form(...),
    instrument: str = Form(...),
    volume: str = Form(""),
    page: str = Form(""),
    grantor: str = Form(...),
    grantee: str = Form(...),
    exec_date: str = Form(""),
    filed_date: str = Form(""),
    legal_description: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        return RedirectResponse(url="/ui/projects", status_code=302)

    def parse_date(s: str) -> date | None:
        s = (s or "").strip()
        if not s:
            return None
        return date.fromisoformat(s)

    row = models.RunSheetRow(
        project_id=project_id,
        row_order=row_order,
        instrument=instrument.strip(),
        volume=(volume.strip() or None),
        page=(page.strip() or None),
        grantor=grantor.strip(),
        grantee=grantee.strip(),
        exec_date=parse_date(exec_date),
        filed_date=parse_date(filed_date),
        legal_description=(legal_description.strip() or None),
        notes=(notes.strip() or None),
        created_by=ACTOR_USER_ID,
        updated_by=ACTOR_USER_ID,
        is_deleted=False,
    )
    db.add(row)
    try:
        db.commit()
    except Exception:
        db.rollback()
        # simplest MVP behavior: redirect back; you can add error messages later
        return RedirectResponse(url=f"/ui/projects/{project_id}", status_code=302)

    return RedirectResponse(url=f"/ui/projects/{project_id}", status_code=302)

def _parse_date_loose(s: str) -> date | None:
    s = (s or "").strip()
    if not s:
        return None

    # Try ISO first: YYYY-MM-DD
    try:
        return date.fromisoformat(s)
    except Exception:
        pass

    # Try common US format: MM/DD/YYYY (or M/D/YYYY)
    try:
        return datetime.strptime(s, "%m/%d/%Y").date()
    except Exception:
        pass

    # Try MM/DD/YY
    try:
        return datetime.strptime(s, "%m/%d/%y").date()
    except Exception:
        return None


def _split_vol_pg(volpg: str) -> tuple[str | None, str | None]:
    volpg = (volpg or "").strip()
    if not volpg:
        return None, None

    # Allow "123/45", "123 / 45", "123 45", "123-45"
    normalized = volpg.replace(" ", "").replace("-", "/")
    if "/" in normalized:
        parts = normalized.split("/", 1)
        vol = parts[0].strip() or None
        pg = parts[1].strip() or None
        return vol, pg

    # Fallback: split on whitespace if user pasted "123 45"
    parts = (volpg or "").strip().split()
    if len(parts) >= 2:
        return parts[0].strip() or None, parts[1].strip() or None

    # If only one token, treat as volume and leave page blank
    return volpg.strip() or None, None


@router.post("/projects/{project_id}/rows/paste")
def paste_rows(
    project_id: str,
    tsv: str = Form(""),
    db: Session = Depends(get_db),
):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        return RedirectResponse(url="/ui/projects", status_code=302)

    # Determine starting row_order (10, 20, 30...)
    max_order = (
        db.query(func.max(models.RunSheetRow.row_order))
        .filter(and_(models.RunSheetRow.project_id == project_id, models.RunSheetRow.is_deleted == False))
        .scalar()
    )
    next_order = 10 if not max_order else int(max_order) + 10

    raw = (tsv or "").strip("\n")
    if not raw.strip():
        return RedirectResponse(url=f"/ui/projects/{project_id}", status_code=302)

    imported = 0
    skipped = 0

    lines = [ln for ln in raw.splitlines() if ln.strip()]
    for ln in lines:
        # Excel copy/paste typically produces TSV
        cols = ln.split("\t")

        # Expect at least 4 columns; full is 8
        # 0 Instrument
        # 1 Vol/Pg
        # 2 Grantor
        # 3 Grantee
        # 4 Exec Date
        # 5 Filed Date
        # 6 Legal Desc
        # 7 Notes
        if len(cols) < 4:
            skipped += 1
            continue

        instrument = (cols[0] if len(cols) > 0 else "").strip()
        volpg = (cols[1] if len(cols) > 1 else "").strip()
        grantor = (cols[2] if len(cols) > 2 else "").strip()
        grantee = (cols[3] if len(cols) > 3 else "").strip()
        exec_date_s = (cols[4] if len(cols) > 4 else "").strip()
        filed_date_s = (cols[5] if len(cols) > 5 else "").strip()
        legal = (cols[6] if len(cols) > 6 else "").strip()
        notes = (cols[7] if len(cols) > 7 else "").strip()

        # Skip header row if user pasted headers
        header_like = instrument.lower() in ("instrument", "instr", "document type")
        if header_like:
            skipped += 1
            continue

        # Minimum required fields
        if not instrument or not grantor or not grantee:
            skipped += 1
            continue

        volume, page = _split_vol_pg(volpg)

        row = models.RunSheetRow(
            project_id=project_id,
            row_order=next_order,
            instrument=instrument,
            volume=volume,
            page=page,
            grantor=grantor,
            grantee=grantee,
            exec_date=_parse_date_loose(exec_date_s),
            filed_date=_parse_date_loose(filed_date_s),
            legal_description=legal or None,
            notes=notes or None,
            created_by=ACTOR_USER_ID,
            updated_by=ACTOR_USER_ID,
            is_deleted=False,
        )
        db.add(row)

        next_order += 10
        imported += 1

    try:
        db.commit()
    except Exception:
        db.rollback()
        # On any DB error, go back without crashing the UI
        return RedirectResponse(url=f"/ui/projects/{project_id}?imported=0&skipped={len(lines)}", status_code=302)

    return RedirectResponse(url=f"/ui/projects/{project_id}?imported={imported}&skipped={skipped}", status_code=302)

@router.post("/rows/{row_id}/update")
def update_row(
    row_id: str,
    project_id: str = Form(...),
    row_order: int = Form(...),
    instrument: str = Form(...),
    volume: str = Form(""),
    page: str = Form(""),
    grantor: str = Form(...),
    grantee: str = Form(...),
    exec_date: str = Form(""),
    filed_date: str = Form(""),
    legal_description: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    row = db.query(models.RunSheetRow).filter(models.RunSheetRow.id == row_id).first()
    if not row:
        return RedirectResponse(url=f"/ui/projects/{project_id}", status_code=302)

    def parse_date(s: str) -> date | None:
        s = (s or "").strip()
        if not s:
            return None
        return date.fromisoformat(s)

    row.row_order = row_order
    row.instrument = instrument.strip()
    row.volume = volume.strip() or None
    row.page = page.strip() or None
    row.grantor = grantor.strip()
    row.grantee = grantee.strip()
    row.exec_date = parse_date(exec_date)
    row.filed_date = parse_date(filed_date)
    row.legal_description = legal_description.strip() or None
    row.notes = notes.strip() or None
    row.updated_by = ACTOR_USER_ID

    try:
        db.commit()
    except Exception:
        db.rollback()

    return RedirectResponse(url=f"/ui/projects/{project_id}", status_code=302)

@router.post("/rows/{row_id}/delete")
def delete_row(row_id: str, project_id: str = Form(...), db: Session = Depends(get_db)):
    row = db.query(models.RunSheetRow).filter(models.RunSheetRow.id == row_id).first()
    if row:
        row.is_deleted = True
        row.deleted_by = ACTOR_USER_ID
        row.updated_by = ACTOR_USER_ID
        db.commit()

    return RedirectResponse(url=f"/ui/projects/{project_id}", status_code=302)
