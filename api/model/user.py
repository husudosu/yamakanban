from datetime import datetime
from typing import List, Union

import sqlalchemy as sqla
import sqlalchemy.orm as sqla_orm
from werkzeug.security import generate_password_hash, check_password_hash

from flask import current_app

from . import BaseMixin

from ..app import db


class TokenBlocklist(db.Model):
    __tablename__ = "token_blocklist"

    id = sqla.Column(sqla.Integer, primary_key=True)
    user_id = sqla.Column(sqla.Integer, sqla.ForeignKey("user.id"))

    jti = sqla.Column(sqla.String(36), nullable=False, index=True)
    created_at = sqla.Column(sqla.DateTime, nullable=False)
    type = db.Column(db.String(16), nullable=False,
                     server_default="access_token")


class Role(db.Model):
    __tablename__ = "role"

    id = sqla.Column(sqla.Integer, primary_key=True)
    name = sqla.Column(sqla.String, nullable=False)

    @classmethod
    def find_or_create(cls, role: str):
        """Finds or creating a role

        Args:
            role (str): Role name

        Returns:
            Role: Role object
        """
        obj = cls.query.filter(cls.name == role).first()
        if not obj:
            obj = cls(name=role)
            db.session.add(obj)
        return obj

    @classmethod
    def find(cls, role: str):
        """Finds a role

        Args:
            role (str): Role name

        Returns:
            Role: Returns Role object or none.
        """
        return cls.query.filter(cls.name == role).first()


user_roles = sqla.Table(
    'user_roles',
    db.metadata,
    sqla.Column('user_id', sqla.ForeignKey('user.id')),
    sqla.Column('role_id', sqla.ForeignKey('role.id'))
)


class User(db.Model, BaseMixin):
    __tablename__ = "user"

    id = sqla.Column(sqla.Integer, primary_key=True)
    name = sqla.Column(sqla.Text)
    username = sqla.Column(sqla.String(255), nullable=False, unique=True)
    email = sqla.Column(sqla.String(255), nullable=False, unique=True)
    password = sqla.Column(sqla.String(255), nullable=False)
    avatar_url = sqla.Column(sqla.Text)

    registered_date = sqla.Column(sqla.DateTime, default=datetime.now)

    # History related stuff
    current_login_at = sqla.Column(sqla.DateTime)
    last_login_at = sqla.Column(sqla.DateTime)
    current_login_ip = sqla.Column(sqla.String(64))
    last_login_ip = sqla.Column(sqla.String(64))

    roles = sqla_orm.relationship(
        "Role",
        secondary=user_roles
    )
    tokens = sqla_orm.relationship(
        "TokenBlocklist",
        cascade="all, delete-orphan"
    )

    def check_password(self, password):
        return check_password_hash(self.password, password)

    @classmethod
    def find_user(cls, user_or_mail: str):
        """Finds user by username or e-mail address

        Args:
            user_or_mail (str): Username/E-mail

        Returns:
            User: Returns user or none
        """
        return cls.query.filter(
            sqla.or_(
                cls.username == user_or_mail,
                cls.email == user_or_mail
            )
        ).first()

    @classmethod
    def create(cls, **kwargs):
        """Creates an User object

        Returns:
            User: Created user
        """
        user = cls(**kwargs)
        # Generate hashed password for user

        # Add default timezone if not exists.
        if "timezone" not in kwargs.keys():
            user.timezone = current_app.config["DEFAULT_TIMEZONE"]

        user.password = generate_password_hash(user.password)
        return user

    def update_roles(self, roles: List[Union[Role, str]]):
        """Update roles

        Args:
            roles (List[Union[Role, str]]): List including role names/role orm obj
        """
        for role in roles:
            self.assign_role(role)

        # FIXME: Need better solution for removing roles!
        remove_roles = []
        for role in self.roles:
            if role.name not in roles:
                remove_roles.append(role.name)
        for role in remove_roles:
            self.deassign_role(role)

    def update(self, **kwargs):
        """Updates an User object"""
        for key, value in kwargs.items():
            if key == "password":
                self.password = generate_password_hash(kwargs["password"])
            elif key == "roles":
                self.update_roles(value)
            else:
                # We don't have to use hasattr here,
                # because we get data using marshmallow schema.
                setattr(self, key, value)

    def has_role(self, role: Union[str, Role]):
        if isinstance(role, Role):
            return role in self.roles
        return Role.query.filter(Role.name == role).first() in self.roles

    def assign_role(self, role: Union[str, Role]):
        role_obj = role
        if not isinstance(role, Role):
            role_obj = Role.query.filter(Role.name == role).first()

        if role_obj and role_obj not in self.roles:
            self.roles.append(role_obj)

    def deassign_role(self, role: Union[str, Role]):
        role_obj = role
        if not isinstance(role, Role):
            role_obj = Role.query.filter(Role.name == role).first()

        if role_obj and role_obj in self.roles:
            self.roles.remove(role_obj)

    timezone = sqla.Column(sqla.Text, nullable=False)

    boards = sqla_orm.relationship("Board")
