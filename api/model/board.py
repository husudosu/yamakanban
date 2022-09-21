
import typing
import sqlalchemy as sqla
import sqlalchemy.orm as sqla_orm
from werkzeug.exceptions import NotFound
from api.app import db
from . import BaseMixin, BoardPermission


class BoardRolePermission(db.Model, BaseMixin):
    __tablename__ = "board_role_permission"

    id = sqla.Column(sqla.Integer, primary_key=True)
    board_role_id = sqla.Column(sqla.Integer, sqla.ForeignKey("board_role.id"))

    name = sqla.Column(sqla.String, nullable=False)
    allow = sqla.Column(sqla.Boolean, nullable=False, default=True)


class BoardRole(db.Model, BaseMixin):
    __tablename__ = "board_role"
    id = sqla.Column(sqla.Integer, primary_key=True)
    board_id = sqla.Column(sqla.Integer, sqla.ForeignKey("board.id"))

    name = sqla.Column(sqla.String, nullable=False)
    is_admin = sqla.Column(sqla.Boolean, default=False, nullable=False)

    permissions = sqla_orm.relationship(
        "BoardRolePermission", cascade="all, delete-orphan")

    @classmethod
    def get_board_role_or_404(cls, board_id: int, role_id: int):
        role = cls.query.filter(
            sqla.and_(
                cls.id == role_id,
                cls.board_id == board_id
            )
        ).first()
        if not role:
            raise NotFound("BoardRole not found")
        return role


class BoardAllowedUser(db.Model, BaseMixin):
    __tablename__ = "board_allowed_user"
    # ! NOTE: Do not use db.session.delete here we doing soft delete first!

    id = sqla.Column(sqla.Integer, primary_key=True)
    user_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("user.id"), nullable=False)
    board_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("board.id"), nullable=False)
    board_role_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("board_role.id")
    )
    is_owner = sqla.Column(sqla.Boolean, default=False, nullable=False)
    is_deleted = sqla.Column(sqla.Boolean, default=False,
                             nullable=False, server_default="0")

    board = sqla_orm.relationship("Board", back_populates="board_users")
    role = sqla_orm.relationship("BoardRole", uselist=False)
    user = sqla_orm.relationship("User", uselist=False)

    @classmethod
    def get_by_user_id(cls, board_id: int, user_id: int):
        return cls.query.filter(
            sqla.and_(
                cls.board_id == board_id,
                cls.user_id == user_id
            )
        ).first()

    def has_permission(self, permission: BoardPermission):
        if self.is_deleted:
            return False
        m = BoardRolePermission.query.filter(
            sqla.and_(
                BoardRolePermission.board_role_id == self.board_role_id,
                BoardRolePermission.name == permission.value
            )
        ).first()
        return m.allow if m else False

    assigned_cards = sqla_orm.relationship(
        "CardMember", back_populates="board_user",
        cascade="all, delete-orphan"
    )
    activities = sqla_orm.relationship(
        "CardActivity", back_populates="board_user",
        cascade="all, delete-orphan"
    )


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
    board_roles = sqla_orm.relationship(
        "BoardRole",
        cascade="all, delete-orphan"
    )

    lists = sqla_orm.relationship(
        "BoardList",
        cascade="all, delete-orphan",
        back_populates="board",
        order_by="asc(BoardList.position)"
    )
    owner = sqla_orm.relationship(
        "User",
        back_populates="boards"
    )

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        # Create default roles & permissions for board.
        roles = create_default_roles(self)
        # Create BoardAllowedUser entry for owner
        self.board_users.append(
            BoardAllowedUser(
                user_id=self.owner_id,
                is_owner=True,
                role=roles[0]
            )
        )

    def is_user_can_access(self, user_id: int):
        """Is the user can access this board?
        Args:
            user_id (int): User id
        """
        if self.owner_id == user_id:
            return True
        member = self.get_board_user(user_id)
        if not member or member.is_deleted:
            return False
        return True

    def get_board_user(self, user_id: int) -> BoardAllowedUser:
        """Gets board user.
        Board user only exists when the user at least can observe the board

        Args:
            user_id (int): User id

        Returns:
            BoardAllowedUser: Board user if exists else None
        """
        return BoardAllowedUser.query.filter(
            sqla.and_(
                BoardAllowedUser.board_id == self.id,
                BoardAllowedUser.user_id == user_id
            )
        ).first()


def create_default_roles(board: Board) -> typing.List[BoardRole]:
    admin_role = BoardRole(name="Admin", board_id=board.id, is_admin=True)
    member_role = BoardRole(name="Member", board_id=board.id)
    observer_role = BoardRole(name="Observer", board_id=board.id)

    # Add all permission for admin role
    for permission in BoardPermission:
        admin_role.permissions.append(
            BoardRolePermission(
                name=permission.value,
                allow=True
            )
        )
        # Allow everything for members expect deleting board
        member_role.permissions.append(
            BoardRolePermission(
                name=permission.value,
                allow=permission != BoardPermission.BOARD_DELETE
            )
        )
        # Disable everything for observer role, it has only view access
        observer_role.permissions.append(
            BoardRolePermission(
                name=permission.value,
                allow=False
            )
        )
    board.board_roles.append(admin_role)
    board.board_roles.append(member_role)
    board.board_roles.append(observer_role)
    return [admin_role, member_role, observer_role]


def check_permission_integrity():
    """Checks if all permission object exists for board roles

    Args:
        board (Board): _description_
    """
    permission_names = [val.value for val in BoardPermission]
    for role in BoardRole.query.all():
        current_permissions = [val.name for val in role.permissions]
        # Delete permission not exists anymore.
        for permission in current_permissions:
            if permission not in permission_names:
                # We can remove permission for all roles.
                db.session.query(BoardRolePermission).filter(
                    BoardRolePermission.name == permission
                ).delete()
        # Add non-existing permissions
        for permission in permission_names:
            if permission not in current_permissions:
                role.permissions.append(
                    BoardRolePermission(
                        name=permission,
                        allow=True if role.name != "Observer" else False
                    )
                )
    db.session.commit()
