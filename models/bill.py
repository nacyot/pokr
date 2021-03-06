# -*- coding: utf-8 -*-

import os

from sqlalchemy import Boolean, Column, Date, func, Integer, select, String, Text, Unicode
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import column_property, relationship
from sqlalchemy.sql.expression import distinct

from database import Base, db_session
from models.bill_keyword import bill_keyword
from models.bill_status import BillStatus
from models.candidacy import Candidacy
from models.cosponsorship import cosponsorship
from models.election import Election
from models.party import Party
from models.person import Person

try:
    from conf.storage import BILLPDF_DIR, BILLTXT_DIR
except ImportError as e:
    import sys
    sys.stderr.write('Error: Update conf/storage.py\n')
    sys.exit(1)


class Bill(Base):
    __tablename__ = 'bill'

    id = Column(String(20), primary_key=True)
    name = Column(Unicode(256), index=True, nullable=False)
    summary = Column(Text)

    age = Column(Integer, index=True, nullable=False)
    proposed_date = Column(Date, index=True)
    decision_date = Column(Date, index=True)

    is_processed = Column(Boolean, index=True)
    link_id = Column(String(40), index=True)
    document_url = Column(Text)

    sponsor = Column(Unicode(80), index=True)
    status_id = Column(Integer, nullable=False)
    status_ids = Column(ARRAY(Integer))
    reviews = relationship('BillReview', backref='bill')

    status = column_property(select([BillStatus.name])\
                             .where(BillStatus.id==status_id), deferred=True)
    keywords = relationship('Keyword',
            secondary=bill_keyword,
            order_by='desc(bill_keyword.c.weight)')

    @property
    def document_pdf_path(self):
        assembly_id = assembly_id_by_bill_id(self.id)
        filepath = '%s/%d/%s.pdf' % (BILLPDF_DIR, assembly_id, self.id)
        if os.path.exists(filepath):
            return filepath
        else:
            return None

    @property
    def document_text_path(self):
        assembly_id = assembly_id_by_bill_id(self.id)
        filepath = '%s/%d/%s.txt' % (BILLTXT_DIR, assembly_id, self.id)
        if os.path.exists(filepath):
            return filepath
        else:
            return None

    @property
    def party_counts(self):
        party_counts = db_session.query(Party.name,
                                        func.count(distinct(Person.id)))\
                                 .join(Candidacy)\
                                 .join(Election)\
                                 .filter(Election.age == self.age)\
                                 .join(Person)\
                                 .join(cosponsorship)\
                                 .join(Bill)\
                                 .filter(Bill.id == self.id)\
                                 .group_by(Party.id)
        return [(party, int(count)) for party, count in party_counts]

    @property
    def representative_people(self):
        return [cosponsor
                for cosponsor in self.cosponsors
                if cosponsor.name in self.sponsor]


bill_and_status = select([func.row_number().over().label('status_order'),
                        func.unnest(Bill.status_ids).label('bill_status_id'),
                        Bill.id.label('bill_id')]).alias()


Bill.statuses = relationship("BillStatus",
            secondary=bill_and_status,
            primaryjoin=Bill.id == bill_and_status.c.bill_id,
            secondaryjoin=bill_and_status.c.bill_status_id == BillStatus.id,
            order_by=bill_and_status.c.status_order,
            viewonly=True,
            backref='bills')


def assembly_id_by_bill_id(bill_id):
    return int(bill_id.lstrip('Z')[:2])

