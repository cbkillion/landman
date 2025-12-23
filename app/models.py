import uuid
from sqlalchemy import (
    Column,
    String,
    Enum,
    Boolean,
    Integer,
    Date,
    Text,
    ForeignKey,
    TIMESTAMP,
    func,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def uuid_str() -> str:
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=uuid_str)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    global_role = Column(Enum("admin", "user"), nullable=False, default="user")
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=uuid_str)
    name = Column(String(255), nullable=False)
    client_name = Column(String(255))
    jurisdiction = Column(String(255))
    status = Column(Enum("draft", "in_review", "delivered", "archived"), nullable=False, default="draft")

    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)

    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    rows = relationship("RunSheetRow", back_populates="project")

class RunSheetRow(Base):
    __tablename__ = "run_sheet_rows"
    __table_args__ = (
        UniqueConstraint("project_id", "row_order", name="uq_project_row_order"),
    )

    id = Column(String(36), primary_key=True, default=uuid_str)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    row_order = Column(Integer, nullable=False)

    instrument = Column(String(255), nullable=False)
    volume = Column(String(50))
    page = Column(String(50))
    grantor = Column(String(255), nullable=False)
    grantee = Column(String(255), nullable=False)
    exec_date = Column(Date)
    filed_date = Column(Date)
    legal_description = Column(Text)
    notes = Column(Text)

    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    updated_by = Column(String(36), ForeignKey("users.id"), nullable=False)

    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_by = Column(String(36), ForeignKey("users.id"))
    deleted_at = Column(TIMESTAMP)

    project = relationship("Project", back_populates="rows")
