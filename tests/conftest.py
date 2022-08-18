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
            roles=[Role.find("user")]  # test_role FIXME: This sucks so bad
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
    with app.app_context():
        usr1 = User.find_user("usr1")
        usr2 = User.find_user("usr2")
        db.session.add(
            Board(
                owner_id=usr1.id,
                title="Test board",
            )
        )
        db.session.add(
            Board(
                owner_id=usr1.id,
                title="Test board 2",
            )
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
