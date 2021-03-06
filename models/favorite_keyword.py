# -*- coding: utf-8 -*-

from sqlalchemy import Column, ForeignKey, Integer
from database import Base


class FavoriteKeyword(Base):
    __tablename__ = 'favorite_keyword'

    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id', onupdate='CACADE', ondelete='CASCADE'),
            nullable=False, index=True, unique='uix_favorite_keyword')
    keyword_id = Column(Integer, ForeignKey('keyword.id', onupdate='CACADE', ondelete='CASCADE'),
            nullable=False, index=True, unique='uix_favorite_keyword')

