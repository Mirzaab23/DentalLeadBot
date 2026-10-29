"""SQLite models for business discovery and resumable scraping jobs."""
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

def now():
    return datetime.now(timezone.utc)

class Base(DeclarativeBase):
    pass

class Business(Base):
    __tablename__ = 'businesses'
    __table_args__ = (UniqueConstraint('source', 'source_url'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, index=True)
    niche: Mapped[str] = mapped_column(String, default='')
    category: Mapped[str] = mapped_column(String, default='')
    address: Mapped[str] = mapped_column(String, default='')
    city: Mapped[str] = mapped_column(String, default='', index=True)
    state: Mapped[str] = mapped_column(String, default='', index=True)
    phone: Mapped[str] = mapped_column(String, default='')
    website: Mapped[str] = mapped_column(String, default='')
    source: Mapped[str] = mapped_column(String)
    source_url: Mapped[str] = mapped_column(String)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String, default='pending')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class Email(Base):
    __tablename__ = 'emails'
    __table_args__ = (UniqueConstraint('business_id', 'email', 'source_url'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey('businesses.id'), index=True)
    email: Mapped[str] = mapped_column(String)
    source_url: Mapped[str] = mapped_column(String)
    syntax_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    mx_valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    validation_status: Mapped[str] = mapped_column(String, default='unverified_mailbox')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class SocialProfile(Base):
    __tablename__ = 'social_profiles'
    __table_args__ = (UniqueConstraint('business_id', 'platform', 'profile_url'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey('businesses.id'), index=True)
    platform: Mapped[str] = mapped_column(String)
    profile_url: Mapped[str] = mapped_column(String)
    source_url: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class ScrapingJob(Base):
    __tablename__ = 'scraping_jobs'
    id: Mapped[int] = mapped_column(primary_key=True)
    niche: Mapped[str] = mapped_column(String)
    city: Mapped[str] = mapped_column(String)
    state: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)
    target_count: Mapped[int] = mapped_column(Integer)
    discovered_count: Mapped[int] = mapped_column(Integer, default=0)
    processed_count: Mapped[int] = mapped_column(Integer, default=0)
    email_found_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, default='pending')
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str] = mapped_column(Text, default='')

class VisitedPage(Base):
    __tablename__ = 'visited_pages'
    __table_args__ = (UniqueConstraint('business_id', 'url'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey('businesses.id'), index=True)
    url: Mapped[str] = mapped_column(String)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    crawl_status: Mapped[str] = mapped_column(String)
    visited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

def initialize(url='sqlite:///data/leads.db'):
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    return engine

class JobBusiness(Base):
    __tablename__ = 'job_businesses'
    __table_args__ = (UniqueConstraint('job_id', 'business_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey('scraping_jobs.id'), index=True)
    business_id: Mapped[int] = mapped_column(ForeignKey('businesses.id'), index=True)

class ProcessedBusiness(Base):
    __tablename__ = 'processed_businesses'
    __table_args__ = (UniqueConstraint('job_id', 'business_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey('scraping_jobs.id'), index=True)
    business_id: Mapped[int] = mapped_column(ForeignKey('businesses.id'), index=True)

class JobSeed(Base):
    __tablename__ = 'job_seeds'
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey('scraping_jobs.id'), unique=True)
    url: Mapped[str] = mapped_column(String)

class JobLocation(Base):
    __tablename__ = 'job_locations'
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey('scraping_jobs.id'), unique=True)
    country: Mapped[str] = mapped_column(String)

class Person(Base):
    __tablename__ = 'people'
    __table_args__ = (UniqueConstraint('source', 'source_url', 'name', 'business_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int | None] = mapped_column(ForeignKey('businesses.id'), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    title: Mapped[str] = mapped_column(String, default='')
    email: Mapped[str] = mapped_column(String, default='')
    email_status: Mapped[str] = mapped_column(String, default='unavailable')
    phone: Mapped[str] = mapped_column(String, default='')
    city: Mapped[str] = mapped_column(String, default='')
    state: Mapped[str] = mapped_column(String, default='')
    linkedin: Mapped[str] = mapped_column(String, default='')
    source: Mapped[str] = mapped_column(String)
    source_url: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
