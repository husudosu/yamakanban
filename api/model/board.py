
import sqlalchemy as sqla
import sqlalchemy.orm as sqla_orm

from api.app import db
from . import BaseMixin, BoardPermissions


class BoardPermission(db.Model, BaseMixin):
    __tablename__ = "board_permission"

    id = sqla.Column(sqla.Integer, primary_key=True)
    board_user_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("board_allowed_user.id"))
    permission_name = sqla.Column(sqla.String, nullable=False)

    read = sqla.Column(sqla.Boolean, default=True, nullable=False)
    update = sqla.Column(sqla.Boolean, default=True, nullable=False)
    write = sqla.Column(sqla.Boolean, default=True, nullable=False)
    delete = sqla.Column(sqla.Boolean, default=True, nullable=False)

    @classmethod
    def get_by_name(cls, board_user_id: int, name: str):
        return cls.query.filter(
            sqla.and_(
                cls.board_user_id == board_user_id,
                cls.permission_name == name,
            )
        ).first()

    def __init__(self, **kwargs):
        # Check logic of read update write permissions
        if kwargs.get("read", False):
            kwargs["read"] = False
            kwargs["update"] = False
            kwargs["write"] = False
            kwargs["delete"] = False
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)


class BoardAllowedUser(db.Model, BaseMixin):
    __tablename__ = "board_allowed_user"

    id = sqla.Column(sqla.Integer, primary_key=True)
    user_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("user.id"), nullable=False)
    board_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("board.id"), nullable=False)

    permissions = sqla_orm.relationship(
        "BoardPermission",
        cascade="all, delete-orphan"
    )
    board = sqla_orm.relationship("Board", back_populates="board_users")

    def __init__(self, **kwargs):
        permissions = kwargs.pop("permissions", [])
        permission_values = [item.value for item in BoardPermissions]

        for permission in permissions:
            if permission.get("permission_name") in permission_values:
                self.permissions.append(BoardPermission(**permission))
                permission_values.remove(permission["permission_name"])
            else:
                raise Exception(
                    f"{permission.get('permission_name')} not exists on BoardPermissions enum!")
        # If permission not created create it with read only
        for permission in permission_values:
            self.permissions.append(
                BoardPermission(
                    permission_name=permission,
                    read=True,
                )
            )
        # Populate object itself
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def update(self, **kwargs):
        permissions = kwargs.pop("permissions", [])
        permission_values = [item.value for item in BoardPermissions]
        self.update(**kwargs)

        for permission in permissions:
            p = BoardPermission.get_by_name(self.id, permission.get("permission_name"))
            if p:
                p.update(**permission)
            elif permission.get("permission_name") in permission_values:
                # Add if it's valid permission but not exists.
                self.permissions.append(BoardPermission(**permission))
            else:
                raise Exception(
                    f"{permission.get('permission_name')} not exists on BoardPermissions enum!")
        # Update object.
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)        


class Board(db.Model, BaseMixin):
    __tablename__ = "board"

    id = sqla.Column(sqla.Integer, primary_key=True)
    owner_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("user.id"), nullable=False)
    title = sqla.Column(sqla.Text, nullable=False)

    background_image = sqla.Column(sqla.Text)
    background_color = sqla.Column(sqla.Text)

    board_users = sqla_orm.relationship(
        "BoardAllowedUser",
        cascade="all, delete-orphan",
        back_populates="board"
    )
    lists = sqla_orm.relationship(
        "BoardList",
        cascade="all, delete-orphan",
        back_populates="board",
        order_by="asc(BoardList.position)"
    )

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def is_user_can_access(self, user_id: int):
        """Is the user can access this board?

        Args:
            user_id (int): User id
        """
        if self.owner_id == user_id:
            return True
        m = BoardAllowedUser.query.filter(
            sqla.and_(
                BoardAllowedUser.board_id == self.id,
                BoardAllowedUser.user_id == user_id
            )
        ).first()
        if m:
            return True
        return False
