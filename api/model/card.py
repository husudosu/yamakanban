from datetime import datetime
import sqlalchemy as sqla
import sqlalchemy.orm as sqla_orm

from api.app import db
from . import BaseMixin

'''
TODO: Add board_id to:
- Card
- Checklist
- ChecklistItem
Why need it?
For permission checking we require to get BoardAllowedUser by using
get_board_user method of board model. It seems more efficent to store board
id on multiple places and run less queries to check permissions of board user.

Example:
When patching Checklistitem:
We should go through:
    - checklist
    - card 
    - list
to reach board.
Of course we also need query (maybe we can do caching here):
    - Board allowed user,
    - Board role,
    - Board role permission -> permission,
This seems at least 6 queries for me just to do permission checking
'''


class CardActivity(db.Model, BaseMixin):
    """Card activity log"""
    __tablename__ = "card_activity"
    id = sqla.Column(sqla.Integer, primary_key=True)
    card_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("card.id"), nullable=False)
    user_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("user.id"), nullable=False)
    activity_on = sqla.Column(
        sqla.DateTime,
        default=datetime.utcnow
    )

    entity_id = sqla.Column(sqla.Integer)
    event = sqla.Column(sqla.SmallInteger, nullable=False)
    changes = sqla.Column(sqla.Text, default="{}")

    # Card
    card = sqla_orm.relationship("Card", uselist=False)

    # User
    user = sqla_orm.relationship("User", uselist=False)

    comment = sqla_orm.relationship(
        "CardComment", cascade="all, delete-orphan", uselist=False,
    )
    member = sqla_orm.relationship(
        "CardMember", cascade="all, delete-orphan", uselist=False,
    )


class CardMember(db.Model, BaseMixin):
    """Card member assignment"""
    __tablename__ = "card_member_assignment"

    id = sqla.Column(sqla.Integer, primary_key=True)

    activity_id = sqla.Column(
        sqla.ForeignKey("card_activity.id"), nullable=False)
    user_id = sqla.Column(sqla.ForeignKey("user.id"), nullable=False)

    send_notification = sqla.Column(sqla.Boolean, default=True, nullable=False)

    user = sqla_orm.relationship("User")


class ChecklistItem(db.Model, BaseMixin):
    """Card checklist item"""
    __tablename__ = "card_checklist_item"
    id = sqla.Column(sqla.Integer, primary_key=True)
    checklist_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("card_checklist.id"))
    marked_complete_user_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("user.id"))
    assigned_user_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("user.id")
    )
    board_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("board.id"), nullable=False
    )

    title = sqla.Column(sqla.Text)
    due_date = sqla.Column(sqla.DateTime)
    completed = sqla.Column(sqla.Boolean, default=False, nullable=False)
    marked_complete_on = sqla.Column(sqla.DateTime)

    board = sqla_orm.relationship("Board")


class CardChecklist(db.Model, BaseMixin):
    """Card checklist"""

    __tablename__ = "card_checklist"
    id = sqla.Column(sqla.Integer, primary_key=True)
    card_id = sqla.Column(sqla.Integer, sqla.ForeignKey("card.id"))
    board_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("board.id"), nullable=False
    )
    title = sqla.Column(sqla.Text)

    items = sqla_orm.relationship(
        "ChecklistItem", cascade="all, delete-orphan")
    card = sqla_orm.relationship(
        "Card", back_populates="checklists"
    )
    board = sqla_orm.relationship("Board")


class CardComment(db.Model, BaseMixin):
    __tablename__ = "card_comment"
    id = sqla.Column(sqla.Integer, primary_key=True)
    user_id = sqla.Column(sqla.Integer, sqla.ForeignKey("user.id"))
    activity_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("card_activity.id"))
    board_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("board.id"), nullable=False
    )

    comment = sqla.Column(sqla.Text)

    created = sqla.Column(
        sqla.DateTime, default=datetime.utcnow
    )
    updated = sqla.Column(sqla.DateTime)

    activity = sqla_orm.relationship("CardActivity", back_populates="comment")
    board = sqla_orm.relationship("Board")

    def update(self, **kwargs):
        self.update(**kwargs)
        self.updated = datetime.utcnow()


class Card(db.Model, BaseMixin):

    __tablename__ = "card"

    id = sqla.Column(sqla.Integer, primary_key=True)
    list_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("list.id"), nullable=False)
    owner_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("user.id"), nullable=False)
    board_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("board.id"), nullable=False
    )

    title = sqla.Column(sqla.Text, nullable=False)
    description = sqla.Column(sqla.Text)
    due_date = sqla.Column(sqla.DateTime)
    position = sqla.Column(sqla.SmallInteger, default=0)

    board_list = sqla_orm.relationship(
        "BoardList", back_populates="cards"
    )
    activities = sqla_orm.relationship(
        "CardActivity", cascade="all, delete-orphan",
        back_populates="card",
        order_by="desc(CardActivity.activity_on)"
    )
    checklists = sqla_orm.relationship(
        "CardChecklist", cascade="all, delete-orphan",
    )
    board = sqla_orm.relationship("Board")
