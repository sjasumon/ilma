import sys
from datetime import datetime, date
from sqlalchemy import (
    create_engine, Column, Integer, SmallInteger, String, Text, Boolean,
    Date, DateTime, Numeric, Enum, ForeignKey, UniqueConstraint, JSON, BigInteger, LargeBinary
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.dialects.mysql import MEDIUMBLOB
from ilma_api.settings import DATABASE_URL

Base = declarative_base()

class Release(Base):
    __tablename__ = "release"
    release_id = Column(String(64), primary_key=True)
    loaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    note = Column(Text, nullable=True)

class Institution(Base):
    __tablename__ = "institution"
    id = Column(Integer, primary_key=True)
    slug = Column(String(64), unique=True, nullable=False)
    name_bn = Column(String(128), nullable=False)
    name_en = Column(String(128), nullable=False)
    type = Column(Enum("bank", "nbfi", name="institution_type"), nullable=False)
    islamic = Column(Boolean, default=False, nullable=False)
    licensed = Column(Boolean, default=True, nullable=False)
    listed = Column(Boolean, default=False, nullable=False)
    coverage = Column(Enum("full", "partial", "licence_only", name="coverage_type"), nullable=False)

    aliases = relationship("InstitutionAlias", back_populates="institution", cascade="all, delete-orphan")
    facts = relationship("Fact", back_populates="institution", cascade="all, delete-orphan")
    ratings = relationship("Rating", back_populates="institution", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="institution", cascade="all, delete-orphan")
    rates = relationship("Rate", back_populates="institution", cascade="all, delete-orphan")

class InstitutionAlias(Base):
    __tablename__ = "institution_alias"
    id = Column(Integer, primary_key=True, autoincrement=True)
    institution_id = Column(Integer, ForeignKey("institution.id"), nullable=False)
    alias = Column(String(128), nullable=False)
    lang = Column(Enum("bn", "en", name="alias_lang"), nullable=False)
    source = Column(String(64), nullable=True)

    institution = relationship("Institution", back_populates="aliases")
    __table_args__ = (UniqueConstraint("institution_id", "alias", name="uq_inst_alias"),)

class Source(Base):
    __tablename__ = "source"
    source_id = Column(String(64), primary_key=True)
    url = Column(Text, nullable=False)
    title = Column(String(255), nullable=False)
    publisher = Column(String(128), nullable=False)
    published_at = Column(Date, nullable=True)  # Unknown publication dates stay unknown.
    page = Column(Integer, nullable=True)
    image_path = Column(String(255), nullable=True)
    checked_by = Column(String(64), nullable=False)
    checked_on = Column(Date, nullable=False)

class Fact(Base):
    __tablename__ = "fact"
    fact_id = Column(String(64), primary_key=True)
    institution_id = Column(Integer, ForeignKey("institution.id"), nullable=False)
    metric = Column(Enum("crar", "npl_ratio", "net_profit", "provision_shortfall", name="metric_type"), nullable=False)
    value = Column(Numeric(20, 6), nullable=False)
    unit = Column(Enum("ratio", "bdt", name="unit_type"), nullable=False)
    period = Column(String(32), nullable=False)
    period_end = Column(Date, nullable=False)
    source_id = Column(String(64), ForeignKey("source.source_id"), nullable=False)
    quote = Column(Text, nullable=False)
    highlight = Column(JSON, nullable=True)
    checked_by = Column(String(64), nullable=False)
    checked_on = Column(Date, nullable=False)
    basis = Column(String(32), nullable=False, default='unknown')

    institution = relationship("Institution", back_populates="facts")
    source = relationship("Source")
    __table_args__ = (UniqueConstraint("institution_id", "metric", "period", name="uq_inst_metric_period"),)

class Rating(Base):
    __tablename__ = "rating"
    fact_id = Column(String(64), primary_key=True)
    institution_id = Column(Integer, ForeignKey("institution.id"), nullable=False)
    agency = Column(String(64), nullable=False)
    long_term = Column(String(32), nullable=False)
    short_term = Column(String(32), nullable=True)
    outlook = Column(Enum("stable", "positive", "negative", "developing", name="outlook_type"), nullable=True)
    rated_on = Column(Date, nullable=False)
    valid_to = Column(Date, nullable=True)
    source_id = Column(String(64), ForeignKey("source.source_id"), nullable=False)
    quote = Column(Text, nullable=False)
    checked_by = Column(String(64), nullable=False)
    checked_on = Column(Date, nullable=False)

    institution = relationship("Institution", back_populates="ratings")
    source = relationship("Source")

class Event(Base):
    __tablename__ = "event"
    event_id = Column(String(64), primary_key=True)
    institution_id = Column(Integer, ForeignKey("institution.id"), nullable=False)
    type = Column(
        Enum(
            "administrator", "board_dissolved", "forced_merger", "licence_cancelled",
            "liquidation", "withdrawal_limit", "emergency_liquidity", "provision_deferral",
            "penalty", "fraud_case", "other",
            name="event_type"
        ),
        nullable=False
    )
    title_bn = Column(String(255), nullable=False)
    title_en = Column(String(255), nullable=False)
    status = Column(
        Enum("reported", "alleged", "case_filed", "charged", "convicted", "settled", "official", name="event_status"),
        nullable=False
    )
    official = Column(Boolean, default=False, nullable=False)
    severity = Column(SmallInteger, nullable=True)
    event_date = Column(Date, nullable=False)
    last_update = Column(Date, nullable=False)
    checked_by = Column(String(64), nullable=False)
    checked_on = Column(Date, nullable=False)

    institution = relationship("Institution", back_populates="events")
    sources = relationship("Source", secondary="event_source")

class EventSource(Base):
    __tablename__ = "event_source"
    event_id = Column(String(64), ForeignKey("event.event_id"), primary_key=True)
    source_id = Column(String(64), ForeignKey("source.source_id"), primary_key=True)


class BankIncident(Base):
    __tablename__ = 'bank_incident'
    incident_id = Column(String(64), primary_key=True)
    institution_id = Column(Integer, ForeignKey('institution.id'), nullable=False, index=True)
    kind = Column(String(32), nullable=False)
    title_bn = Column(String(255), nullable=False)
    title_en = Column(String(255), nullable=False)
    status = Column(String(24), nullable=False)
    official = Column(Boolean, nullable=False)
    status_effect = Column(Boolean, nullable=False, default=False)
    started_on = Column(Date, nullable=True)
    first_reported_on = Column(Date, nullable=False)
    last_update_on = Column(Date, nullable=False)
    checked_by = Column(String(64), nullable=False)
    checked_on = Column(Date, nullable=False)
    sources = relationship('IncidentSource', cascade='all, delete-orphan')
    changes = relationship('IncidentStatusChange', cascade='all, delete-orphan')


class IncidentSource(Base):
    __tablename__ = 'incident_source'
    incident_id = Column(String(64), ForeignKey('bank_incident.incident_id'), primary_key=True)
    source_id = Column(String(64), ForeignKey('source.source_id'), primary_key=True)
    quote = Column(Text, nullable=False)
    language = Column(String(2), nullable=False)
    source = relationship('Source')


class IncidentStatusChange(Base):
    __tablename__ = 'incident_status_change'
    change_id = Column(String(64), primary_key=True)
    incident_id = Column(String(64), ForeignKey('bank_incident.incident_id'), nullable=False, index=True)
    status = Column(String(24), nullable=False)
    changed_on = Column(Date, nullable=False)
    source_id = Column(String(64), ForeignKey('source.source_id'), nullable=False)
    quote = Column(Text, nullable=False)
    source = relationship('Source')

class Rate(Base):
    __tablename__ = "rate"
    fact_id = Column(String(64), primary_key=True)
    institution_id = Column(Integer, ForeignKey("institution.id"), nullable=False)
    product = Column(Enum("fdr", "dps", "savings", name="rate_product"), nullable=False)
    tenor_months = Column(Integer, nullable=False)
    rate = Column(Numeric(6, 4), nullable=False)
    min_amount_bdt = Column(Numeric(15, 2), nullable=True)
    as_of = Column(Date, nullable=False)
    source_id = Column(String(64), ForeignKey("source.source_id"), nullable=False)
    quote = Column(Text, nullable=False)
    checked_by = Column(String(64), nullable=False)
    checked_on = Column(Date, nullable=False)

    institution = relationship("Institution", back_populates="rates")
    source = relationship("Source")

class ServiceOffer(Base):
    __tablename__ = 'service_offer'
    offer_id = Column(String(64), primary_key=True)
    institution_id = Column(Integer, ForeignKey('institution.id'), nullable=False, index=True)
    category = Column(String(24), nullable=False)
    product = Column(String(255), nullable=False)
    product_type = Column(String(40), nullable=False, index=True)
    network = Column(String(32), nullable=True)
    tier = Column(String(32), nullable=True)
    tenor_months = Column(Integer, nullable=True)
    tenor_min_months = Column(Integer, nullable=True)
    tenor_max_months = Column(Integer, nullable=True)
    tenor_options = Column(JSON, nullable=True)
    attribute = Column(String(64), nullable=False)
    value_num = Column(Numeric(20, 6), nullable=True)
    value_text = Column(Text, nullable=False)
    unit = Column(String(24), nullable=False)
    condition = Column(Text, nullable=False)
    basis = Column(String(24), nullable=False)
    doc_date = Column(Date, nullable=False)
    stale = Column(Boolean, nullable=False)
    source_url = Column(Text, nullable=False)
    page = Column(Integer, nullable=False)
    quote = Column(Text, nullable=False)
    column_header = Column(Text, nullable=False)
    variant = Column(String(16), nullable=False, default='main')
    hidden = Column(Boolean, nullable=False, default=False)
    hidden_reason = Column(Text, nullable=False, default='')
    checked_by = Column(String(64), nullable=False)
    checked_on = Column(Date, nullable=False)
    institution = relationship('Institution')


class SharePriceFlag(Base):
    __tablename__ = "share_price_flag"
    institution_id = Column(Integer, ForeignKey("institution.id"), primary_key=True)
    days_below_face = Column(Integer, nullable=False)
    window_end = Column(Date, nullable=False)
    source_id = Column(String(64), ForeignKey("source.source_id"), nullable=False)

    institution = relationship("Institution")
    source = relationship("Source")

class InsuranceRule(Base):
    __tablename__ = "insurance_rule"
    inst_type = Column(Enum("bank", "nbfi", name="inst_insurance_type"), primary_key=True)
    covered = Column(Boolean, nullable=False)
    limit_bdt = Column(Integer, nullable=True)
    payout_working_days = Column(Integer, nullable=True)
    covered_from = Column(Date, nullable=True)
    text_bn = Column(Text, nullable=False)
    text_en = Column(Text, nullable=False)
    source_id = Column(String(64), ForeignKey("source.source_id"), nullable=False)

    source = relationship("Source")

class AppQuestionLog(Base):
    __tablename__ = "app_question_log"
    q_id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    device_hash = Column(String(16), nullable=True)
    input_mode = Column(Enum("voice", "text", "photo", name="input_mode"), nullable=False)
    text_redacted = Column(Text, nullable=False, default="[input omitted]")
    intent = Column(String(32), nullable=False)
    institution_id = Column(Integer, nullable=True)
    fact_ids = Column(JSON, nullable=False, default=list)
    outcome = Column(Enum("answered", "no_data", "refused", "error", name="question_outcome"), nullable=False)
    latency_ms = Column(Integer, nullable=False, default=0)
    cost_micro_usd = Column(Integer, nullable=False, default=0)
    useful = Column(Boolean, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class AppWatchItem(Base):
    __tablename__ = 'app_watch_item'
    device_hash = Column(String(64), primary_key=True)
    institution_id = Column(Integer, ForeignKey('institution.id'), primary_key=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class VoiceDiagnostic(Base):
    __tablename__ = "voice_diagnostic"
    diagnostic_id = Column(String(32), primary_key=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    mime = Column(String(64), nullable=False)
    language = Column(String(2), nullable=False)
    audio = Column(LargeBinary().with_variant(MEDIUMBLOB(), 'mysql'), nullable=False)
    meta_transcript = Column(Text, nullable=True)
    expected_question = Column(Text, nullable=True)
    events = Column(JSON, nullable=False)


class AppContent(Base):
    __tablename__ = "app_content"
    content_key = Column(String(64), primary_key=True)
    lang = Column(Enum("bn", "en", name="content_language"), primary_key=True)
    version = Column(Integer, primary_key=True, default=1)
    text = Column(Text, nullable=False)
    audio_path = Column(String(255), nullable=True)
    status = Column(Enum("draft", "reviewed", "live", name="content_status"), nullable=False, default="draft")


class AppModelCall(Base):
    __tablename__ = 'app_model_call'
    call_id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True, autoincrement=True)
    turn_id = Column(String(32), nullable=False, index=True)
    stage = Column(String(8), nullable=False)
    model = Column(String(128), nullable=False)
    latency_ms = Column(Integer, nullable=False)
    status = Column(String(16), nullable=False)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    failure_reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class BankProfile(Base):
    __tablename__='bank_profile'
    fact_id=Column(String(64),primary_key=True)
    bank_id=Column(Integer,ForeignKey('institution.id'),nullable=False,index=True)
    field=Column(String(32),nullable=False)
    value=Column(Text,nullable=False)
    as_of=Column(Date,nullable=False)
    source_url=Column(Text,nullable=False)
    page=Column(String(32),nullable=False)
    quote=Column(Text,nullable=False)
    checked_by=Column(String(64),nullable=False,default='source-import')
    checked_on=Column(Date,nullable=False,default=date.today)
    __table_args__=(UniqueConstraint('bank_id','field','as_of',name='uq_profile_bank_field_date'),)


class AppConversation(Base):
    __tablename__='app_conversation'
    conversation_id=Column(String(32),primary_key=True)
    memory=Column(JSON,nullable=False)
    created_at=Column(DateTime,nullable=False,default=datetime.utcnow)
    updated_at=Column(DateTime,nullable=False,default=datetime.utcnow)
    expires_at=Column(DateTime,nullable=False,index=True)


class AppRateCounter(Base):
    __tablename__ = "app_rate_counter"
    key = Column(String(80), primary_key=True)
    count = Column(Integer, nullable=False, default=0)
    expires_at = Column(DateTime, nullable=False)


for table in Base.metadata.tables.values():
    table.dialect_options["mysql"]["charset"] = "utf8mb4"

engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"connect_timeout": 5,"read_timeout":5,"write_timeout":5}, pool_recycle=1800, pool_size=5, max_overflow=5, pool_timeout=5)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")


class ExtraItem(Base):
    __tablename__ = 'extra_item'
    item_id = Column(String(64), primary_key=True)
    institution_id = Column(Integer, ForeignKey('institution.id'), nullable=True, index=True)
    kind = Column(String(24), nullable=False, index=True)
    topic = Column(String(40), nullable=False)
    title = Column(Text, nullable=False)
    published_on = Column(Date, nullable=True)
    report_year = Column(Integer, nullable=True)
    source_url = Column(Text, nullable=False)
    source_kind = Column(String(16), nullable=False)
    checked_by = Column(String(64), nullable=False)
    checked_on = Column(Date, nullable=False)


class RelatedEntity(Base):
    __tablename__ = 'related_entity'
    name = Column(String(255), primary_key=True)
    parent_bank_id = Column(Integer, nullable=False)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "create":
        create_tables()
