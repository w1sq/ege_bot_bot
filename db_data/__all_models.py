import sqlalchemy
from .db_session import SqlAlchemyBase
from sqlalchemy import orm

records_table = sqlalchemy.Table('record_user', SqlAlchemyBase.metadata,
    sqlalchemy.Column('left_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id')),
    sqlalchemy.Column('right_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('records.id'))
)

class User(SqlAlchemyBase):
    __tablename__ = "users"

    id = sqlalchemy.Column(sqlalchemy.Integer, nullable=False, primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    records = orm.relationship("StudyRecord", secondary=records_table, back_populates='user')

class StudyRecord(SqlAlchemyBase):
    __tablename__ = "records"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    date = sqlalchemy.Column(sqlalchemy.Date)
    minutes = sqlalchemy.Column(sqlalchemy.Integer, default=0)
    user = orm.relationship("User", secondary=records_table, back_populates='records')

    def __str__(self):
        if self.minutes:
            if self.minutes % 60 < 10:
                return f'{self.minutes // 60}:0{self.minutes % 60}'
            else:
                return f'{self.minutes // 60}:{self.minutes % 60}'
        return '0'