from sqlalchemy import create_engine, Column, String, JSON, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv
import pathlib
from urllib.parse import quote_plus

# Load environment variables
backend_dir = pathlib.Path(__file__).parent
load_dotenv(backend_dir / "wow.env")
load_dotenv(backend_dir / ".env")

def _convert_pg_dsn_to_url(dsn: str) -> str:
    """
    Convert libpq-style DSN string:
      'host=localhost port=5432 dbname=postgres user=postgres password=postgres sslmode=prefer'
    into SQLAlchemy URL:
      'postgresql+psycopg2://user:password@host:port/dbname?sslmode=prefer'
    """
    parts = {}
    for token in dsn.split():
        if "=" in token:
            k, v = token.split("=", 1)
            parts[k.strip()] = v.strip()
    host = parts.get("host", "localhost")
    port = parts.get("port", "5432")
    dbname = parts.get("dbname", "postgres")
    user = parts.get("user", "postgres")
    password = quote_plus(parts.get("password", ""))
    query = f"?sslmode={parts['sslmode']}" if 'sslmode' in parts else ""
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}{query}"

# Database URL from environment or default (supports URL or DSN)
_RAW_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/docrflowise"
)
if "://" not in _RAW_DATABASE_URL and "host=" in _RAW_DATABASE_URL:
    DATABASE_URL = _convert_pg_dsn_to_url(_RAW_DATABASE_URL)
else:
    DATABASE_URL = _RAW_DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class WorkflowModel(Base):
    __tablename__ = "workflows"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    custom_prompt = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    nodes = relationship("NodeModel", back_populates="workflow", cascade="all, delete-orphan")
    connections = relationship("ConnectionModel", back_populates="workflow", cascade="all, delete-orphan")


class NodeModel(Base):
    __tablename__ = "nodes"
    
    id = Column(String, primary_key=True)
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=False)
    node_type = Column(String, nullable=False)
    config = Column(JSON, default={})
    position_x = Column(String)
    position_y = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    workflow = relationship("WorkflowModel", back_populates="nodes")
    connections_as_source = relationship("ConnectionModel", foreign_keys="ConnectionModel.source_node_id", back_populates="source_node")
    connections_as_target = relationship("ConnectionModel", foreign_keys="ConnectionModel.target_node_id", back_populates="target_node")


class ConnectionModel(Base):
    __tablename__ = "connections"
    
    id = Column(String, primary_key=True)
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=False)
    source_node_id = Column(String, ForeignKey("nodes.id"), nullable=False)
    target_node_id = Column(String, ForeignKey("nodes.id"), nullable=False)
    source_output = Column(String, nullable=False)
    target_input = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    workflow = relationship("WorkflowModel", back_populates="connections")
    source_node = relationship("NodeModel", foreign_keys=[source_node_id], back_populates="connections_as_source")
    target_node = relationship("NodeModel", foreign_keys=[target_node_id], back_populates="connections_as_target")


# Create tables
def init_db():
    Base.metadata.create_all(bind=engine)


# Get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

