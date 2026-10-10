from sqlalchemy import Column, Integer, String, Text
from pgvector.sqlalchemy import Vector
from .database import Base

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    source_url = Column(String, index=True)
    content = Column(Text)
    embedding = Column(Vector(384))  # 384 is default for sentence-transformers all-MiniLM-L6-v2
