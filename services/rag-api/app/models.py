from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Integer, String, Text

from .database import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    source_url = Column(String, index=True)
    content = Column(Text)
    embedding = Column(Vector(768))  # 768 is default for BAAI/bge-base-en-v1.5
