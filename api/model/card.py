from datetime import datetime
import sqlalchemy as sqla
import sqlalchemy.orm as sqla_orm

from api.app import db
from . import BaseMixin


class BoardActivity(db.Model, BaseMixin):
    """Card activity log"""
    __tablename__ = "card_activity"  # TODO: Change this to board_activity.
    id = sqla.Column(sqla.Integer, primary_key=True)
    board_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("board.id", ondelete="CASCADE"), nullable=False
    )
    card_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("card.id", ondelete="CASCADE"))

    board_user_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("board_allowed_user.id", ondelete="CASCADE"), nullable=False)
    activity_on = sqla.Column(
        sqla.DateTime,
        default=datetime.utcnow
    )

    entity_id = sqla.Column(sqla.Integer)
    event = sqla.Column(sqla.String(255), nullable=False)  # CardActivityEvent
    changes = sqla.Column(sqla.Text, default="{}")

    # Card
    card = sqla_orm.relationship("Card", uselist=False)

    # User
    board_user = sqla_orm.relationship("BoardAllowedUser", uselist=False)

    comment = sqla_orm.relationship(
        "CardComment", cascade="all, delete-orphan", uselist=False,
    )


class CardMember(db.Model, BaseMixin):
    """Card member assignment"""
    __tablename__ = "card_member_assignment"

    id = sqla.Column(sqla.Integer, primary_key=True)

    card_id = sqla.Column(
        sqla.ForeignKey("card.id", ondelete="CASCADE"), nullable=False)
    board_user_id = sqla.Column(sqla.ForeignKey(
        "board_allowed_user.id", ondelete="CASCADE"), nullable=False)

    send_notification = sqla.Column(sqla.Boolean, default=True, nullable=False)

    board_user = sqla_orm.relationship("BoardAllowedUser")


class CardComment(db.Model, BaseMixin):
    __tablename__ = "card_comment"
    id = sqla.Column(sqla.Integer, primary_key=True)
    board_user_id = sqla.Column(sqla.ForeignKey(
        "board_allowed_user.id", ondelete="CASCADE"), nullable=False)
    activity_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("card_activity.id", ondelete="CASCADE"))
    board_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("board.id", ondelete="CASCADE"), nullable=False
    )

    comment = sqla.Column(sqla.Text)

    created = sqla.Column(
        sqla.DateTime, default=datetime.utcnow
    )
    updated = sqla.Column(sqla.DateTime)

    activity = sqla_orm.relationship("BoardActivity", back_populates="comment")
    board = sqla_orm.relationship("Board")

    def update(self, **kwargs):
        super().update(**kwargs)
        self.updated = datetime.utcnow()


class CardDate(db.Model, BaseMixin):

    __tablename__ = "card_date"

    id = sqla.Column(sqla.Integer, primary_key=True)
    card_id = sqla.Column(sqla.Integer, sqla.ForeignKey(
        "card.id", ondelete="CASCADE"))
    board_id = sqla.Column(sqla.Integer, sqla.ForeignKey(
        "board.id", ondelete="CASCADE"))

    dt_from = sqla.Column(sqla.DateTime)
    dt_to = sqla.Column(sqla.DateTime, nullable=False)

    description = sqla.Column(sqla.Text)
    complete = sqla.Column(sqla.Boolean, default=False,
                           nullable=False, server_default="0")

    board = sqla_orm.relationship("Board")
    card = sqla_orm.relationship("Card", back_populates="dates", uselist=False)


class CardFileUpload(db.Model, BaseMixin):

    __tablename__ = "card_file_upload"
    id = sqla.Column(sqla.Integer, primary_key=True)
    card_id = sqla.Column(sqla.Integer, sqla.ForeignKey(
        "card.id", ondelete="CASCADE"))
    board_id = sqla.Column(sqla.Integer, sqla.ForeignKey(
        "board.id", ondelete="CASCADE"))

    file_name = sqla.Column(sqla.String, nullable=False)
    created_on = sqla.Column(
        sqla.DateTime, default=datetime.utcnow, server_default="NOW()")

    card = sqla_orm.relationship("Card", back_populates="file_uploads")


class Card(db.Model, BaseMixin):

    __tablename__ = "card"

    id = sqla.Column(sqla.Integer, primary_key=True)
    list_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("list.id", ondelete="CASCADE"), nullable=False)
    board_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("board.id", ondelete="CASCADE"), nullable=False
    )

    title = sqla.Column(sqla.Text, nullable=False)
    description = sqla.Column(sqla.Text)
    position = sqla.Column(sqla.SmallInteger, default=0)

    archived = sqla.Column(sqla.Boolean, server_default="0", default=False)
    archived_by_list = sqla.Column(
        sqla.Boolean, server_default="0", default=False)
    archived_on = sqla.Column(sqla.DateTime)
    created_on = sqla.Column(
        sqla.DateTime, nullable=False, default=datetime.utcnow, server_default="NOW()")

    board_list = sqla_orm.relationship(
        "BoardList", back_populates="cards"
    )
    activities = sqla_orm.relationship(
        "BoardActivity", cascade="all, delete-orphan",
        back_populates="card",
        order_by="desc(BoardActivity.activity_on)",
        lazy="noload",
        uselist=True
    )
    checklists = sqla_orm.relationship(
        "CardChecklist", cascade="all, delete-orphan",
    )
    assigned_members = sqla_orm.relationship(
        "CardMember", cascade="all, delete-orphan"
    )
    dates = sqla_orm.relationship(
        "CardDate", cascade="all, delete-orphan",
        order_by="asc(CardDate.dt_to)",
        back_populates="card"
    )
    board_list = sqla_orm.relationship(
        "BoardList", back_populates="cards"
    )

    board = sqla_orm.relationship("Board")
    file_uploads = sqla_orm.relationship(
        "CardFileUpload", back_populates="card"
    )
