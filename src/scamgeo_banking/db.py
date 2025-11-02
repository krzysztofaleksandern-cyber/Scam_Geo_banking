@"
from typing import Optional, Iterator
from sqlmodel import SQLModel, Field, create_engine, Session, select, UniqueConstraint
import os

DEFAULT_DB_PATH = "scamgeo_banking.db"

def get_engine():
    db_path = os.getenv("DB_PATH", DEFAULT_DB_PATH)
    connect_args = {"check_same_thread": False} if db_path.endswith(".db") else {}
    return create_engine(f"sqlite:///{db_path}", echo=False, connect_args=connect_args)

class Channel(SQLModel, table=True):
    __tablename__ = "channels"
    id: Optional[int] = Field(default=None, primary_key=True)
    handle: str = Field(index=True)
    platform: str = Field(default="telegram")
    __table_args__ = (UniqueConstraint("handle", "platform", name="uq_channel_handle_platform"),)

class Snapshot(SQLModel, table=True):
    __tablename__ = "snapshots"
    id: Optional[int] = Field(default=None, primary_key=True)
    channel_id: int = Field(index=True, foreign_key="channels.id")
    ts_utc: int = Field(index=True)
    meta_json: str

class Admin(SQLModel, table=True):
    __tablename__ = "admins"
    id: Optional[int] = Field(default=None, primary_key=True)
    channel_id: int = Field(index=True, foreign_key="channels.id")
    username: str = Field(index=True)
    user_id: Optional[str] = None
    __table_args__ = (UniqueConstraint("channel_id", "username", name="uq_admin_channel_username"),)

class WhoisRecord(SQLModel, table=True):
    __tablename__ = "whois"
    id: Optional[int] = Field(default=None, primary_key=True)
    domain: str = Field(index=True)
    ts_utc: int = Field(index=True)
    raw_json: str

def init_db():
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    return engine

def session_scope() -> Iterator[Session]:
    engine = get_engine()
    with Session(engine) as s:
        yield s

def get_or_create_channel(s: Session, handle: str, platform: str = "telegram") -> Channel:
    q = select(Channel).where(Channel.handle == handle, Channel.platform == platform)
    ch = s.exec(q).first()
    if ch:
        return ch
    ch = Channel(handle=handle, platform=platform)
    s.add(ch)
    s.commit()
    s.refresh(ch)
    return ch
"@ | Set-Content -Encoding utf8 .\src\scamgeo_banking\db.py




