"""Database configuration and models."""
import os
from sqlalchemy import create_engine, Column, String, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from datetime import datetime

# Database URL - using SQLite for simplicity
# You can change to PostgreSQL or MySQL by modifying the URL
DB_URL = os.getenv('DATABASE_URL', 'sqlite:///./wonderland_cache.db')

# Create engine
engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DB_URL else {},
    echo=False  # Set to True for SQL logging
)

# Create session factory
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

# Base class for models
Base = declarative_base()


class CachedImage(Base):
    """Model for cached images pulled from the endpoint."""
    __tablename__ = "cached_images"
    
    id = Column(Integer, primary_key=True, index=True)
    guid = Column(String, index=True, nullable=False)
    server = Column(String, nullable=False)
    image_url = Column(String, nullable=False)  # Discord CDN URL
    original_url = Column(String, nullable=True)  # Original endpoint URL for reference
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<CachedImage(guid={self.guid}, server={self.server}, created_at={self.created_at})>"


def init_db():
    """Initialize database - create all tables."""
    Base.metadata.create_all(bind=engine)


def get_session():
    """Get a new database session."""
    return SessionLocal()


def close_session():
    """Close the scoped session."""
    SessionLocal.remove()
