# model.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Company(Base):
    __tablename__ = 'company'

    company_id = Column(Integer, primary_key=True, autoincrement=True)
    company_name = Column(String(100), nullable=False)
    ai_bot_name = Column(String(100))
    system_prompt = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 1:N 관계 정의
    documents = relationship('Document', back_populates='company', cascade='all, delete-orphan')
    company_chats = relationship('CompanyChat', back_populates='company', cascade='all, delete-orphan')


class Document(Base):
    __tablename__ = 'document'

    doc_id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('company.company_id', ondelete='CASCADE'), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)

    company = relationship('Company', back_populates='documents')


class CompanyChat(Base):
    __tablename__ = 'companyChats'

    chat_id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('company.company_id', ondelete='CASCADE'), nullable=False)

    user_message = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=False)

    sentiment = Column(String(50))
    topic = Column(String(100))

    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship('Company', back_populates='company_chats')