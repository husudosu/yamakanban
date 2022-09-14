import typing
import pytest

import sqlalchemy as sqla

from api.app import create_app, db
from api.model.board import Board, BoardRole
from api.model.list import BoardList
from api.model.user import Role, User

from api.service import board as board_service
from api.util import factory


@pytest.fixture()
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": True,
        "JWT_COOKIE_SECURE": False,
        "JWT_TOKEN_LOCATION": ["headers"]
    })
    with app.app_context():
        db.create_all()
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()


@pytest.fixture()
def test_users(app, client, test_roles):
    """Creates these users
    id: 1; username: admin
    id: 2; username: usr1
    id: 3; username: usr2
    """
    with app.app_context():
        # Create admin user too
        user_role = Role.find("user")
        admin = User.create(
            username="admin",
            password="admin",
            email="admin@localhost.com",
            timezone=app.config["DEFAULT_TIMEZONE"],
            roles=[Role.find("admin")]
        )
        usr1 = User.create(
            username="usr1",
            password="usr1",
            email="usr1@localhost.com",
            timezone=app.config["DEFAULT_TIMEZONE"],
            roles=[user_role]
        )
        usr2 = User.create(
            username="usr2",
            password="usr2",
            timezone=app.config["DEFAULT_TIMEZONE"],
            email="usr2@localhost.com",
        )
        db.session.add(admin)
        db.session.add(usr1)
        db.session.add(usr2)
        db.session.commit()
        return [admin, usr1, usr2]


@pytest.fixture()
def test_roles(app):
    """Creates these roles:
    id: 1; name: admin
    id: 2; name: user
    id: 3; name: test_role1
    """
    with app.app_context():
        admin_role = Role.find_or_create("admin")
        user_role = Role.find_or_create("user")
        role1 = Role.find_or_create("test_role1")
        db.session.commit()
        return [admin_role, user_role, role1]


def do_login(client, username, password):
    """Login and returns tokens"""
    return client.post(
        "/api/v1/auth/login",
        json={
            "username": username,
            "password": password
        }
    ).json


@pytest.fixture()
def test_boards(app, test_users):
    """Creates these boards:
    1: owner: usr1
    2: owner: usr1; allowed users: usr2 as observer
    3: owner: usr2
    4: owner: usr2
    """
    with app.app_context():
        usr1 = User.find_user("usr1")
        usr2 = User.find_user("usr2")
        db.session.add(
            Board(
                owner_id=usr1.id,
                title="Test board",
            )
        )

        board2 = Board(
            owner_id=usr1.id,
            title="Test board 2",
        )
        db.session.add(board2)
        db.session.commit()
        observer_role = BoardRole.query.filter(
            sqla.and_(
                BoardRole.board_id == board2.id,
                BoardRole.name == "Observer"
            )
        ).first()
        board_service.add_member(
            usr1,
            board2,
            usr2,
            observer_role
        )

        db.session.add(
            Board(
                owner_id=usr2.id,
                title="Usr2: Test board",
            )
        )
        db.session.add(
            Board(
                owner_id=usr2.id,
                title="Usr2: Test board 2",
            )
        )
        db.session.commit()


@pytest.fixture()
def test_boardlists(app, test_boards):
    with app.app_context():
        boards = Board.query.all()
        for board in boards:
            for i in range(0, 5):
                board.lists.append(
                    BoardList(
                        title=f"Test list {board.id} - {i+1}",
                        position=i+1
                    )
                )
        db.session.commit()


@pytest.fixture()
def test_cards(app, test_boardlists):
    """Creates cards with various activites. Creates for every existing list"""
    with app.app_context():
        lists: typing.List[BoardList] = BoardList.query.all()
        for list in lists:
            db.session.add_all([factory.create_card(list.board.owner, list)
                                for _ in range(0, 5)])
            db.session.commit()
