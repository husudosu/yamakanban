import pytest

from api.app import create_app, db
from api.model.board import Board
from api.model.list import BoardList
from api.model.user import Role, User


@pytest.fixture()
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": True
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
    with app.app_context():
        usr1 = User.create(
            username="usr1",
            password="usr1",
            email="usr1@localhost.com",
            roles=[test_roles[0]]  # test_role FIXME: This sucks so bad
        )
        usr2 = User.create(
            username="usr2",
            password="usr2",
            email="usr2@localhost.com"
        )
        db.session.add(usr1)
        db.session.add(usr2)
        db.session.commit()
        return [usr1, usr2]


@pytest.fixture()
def test_admin(app):
    """Create admin user for testing"""
    with app.app_context():
        Role.find_or_create("admin")
        usr = User.create(
            username="admin",
            password="admin",
            email="admin@localhost.com",
            roles=["admin"]
        )
        return usr


@pytest.fixture()
def test_roles(app):
    with app.app_context():
        role = Role.find_or_create("test_role")
        role1 = Role.find_or_create("test_role1")
        db.session.commit()
        return [role, role1]


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
def private_boards(app, test_users):
    with app.app_context():
        usr = User.query.get(1)
        usr1 = User.query.get(2)
        db.session.add(
            Board(
                owner_id=usr.id,
                title="Test board",
            )
        )
        db.session.add(
            Board(
                owner_id=usr.id,
                title="Test board 2",
            )
        )
        db.session.add(
            Board(
                owner_id=usr1.id,
                title="Usr1: Test board",
            )
        )
        db.session.add(
            Board(
                owner_id=usr1.id,
                title="Usr1: Test board 2",
            )
        )
        db.session.commit()


@pytest.fixture()
def test_boardlists(app, private_boards):
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
