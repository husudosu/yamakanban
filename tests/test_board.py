import sqlalchemy as sqla

from api.model.board import Board, BoardRole
from api.model.user import User
from .conftest import do_login


def test_get_boards(client, test_users, test_boards):
    tokens = do_login(client, "usr2", "usr2")
    resp = client.get(
        "/api/v1/board",
        headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )

    assert resp.status_code == 200
    # Check if got only available boards for user
    assert len(resp.json) == 3


def test_get_board(app, client, test_users, test_boards):
    # ! Only allow getting board info if available for user.
    with app.app_context():
        tokens = do_login(client, "usr1", "usr1")
        test_board = Board.query.get(1)

        # usr1 has no access to board 3
        board3 = Board.query.get(3)

        resp_forbidden = client.get(
            f"/api/v1/board/{board3.id}",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        assert resp_forbidden.status_code == 403

        # Test forbidden
        resp = client.get(
            f"/api/v1/board/{test_board.id}",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )

        assert resp.status_code == 200
        assert resp.json["id"] == test_board.id
        assert resp.json["title"] == test_board.title
        assert resp.json["owner_id"] == test_board.owner_id
        assert resp.json["background_image"] == test_board.background_image
        assert resp.json["background_color"] == test_board.background_color


def test_create_board(app, client, test_users):
    with app.app_context():
        tokens = do_login(client, "usr1", "usr1")
        test_data = {
            "title": "My board",
            "background_image": "Test",
            "background_color": "#FFF",
        }

        resp = client.post(
            "/api/v1/board",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json=test_data
        )

        assert resp.status_code == 200
        assert "id" in resp.json.keys()
        assert resp.json["title"] == test_data["title"]
        assert resp.json["background_image"] == test_data["background_image"]
        assert resp.json["background_color"] == test_data["background_color"]


def test_update_board(app, client, test_users, test_boards):
    with app.app_context():
        tokens = do_login(client, "usr1", "usr1")
        # TODO: Method to change ownership for boards
        test_board = Board.query.get(1)
        test_data = {
            "title": "My board updated"
        }

        resp = client.patch(
            f"/api/v1/board/{test_board.id}",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json=test_data
        )

        assert resp.status_code == 200
        assert resp.json["title"] == test_data["title"]


def test_delete_board(app, client, test_users, test_boards):
    with app.app_context():
        tokens = do_login(client, "usr1", "usr1")
        test_board = Board.query.get(1)

        resp = client.delete(
            f"/api/v1/board/{test_board.id}",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert resp.status_code == 200


def test_remove_member(app, client, test_users, test_boards):
    with app.app_context():
        '''
        Expected behaviour:
            - Admin board role required for adding/removing members
            - At least one admin required for every board!
            - The user can't delete own access from board.
        '''
        tokens = do_login(client, "usr1", "usr1")
        board1: Board = Board.query.get(1)
        board3: Board = Board.query.get(3)
        usr2: User = User.find_user("usr2")
        usr1: User = User.find_user("usr1")

        # Forbidden
        resp_forbidden = client.delete(
            f"/api/v1/board/{board3.id}/member/{usr1.id}",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert resp_forbidden.status_code == 403

        # Add a valid member
        client.post(
            f"/api/v1/board/{board1.id}/member",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json={
                "user_id": usr2.id,
                "board_id": board1.id,
                "board_role_id": board1.board_roles[0].id
            }
        )
        # Remove member
        resp_remove = client.delete(
            f"/api/v1/board/{board1.id}/member/{usr2.id}",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        assert resp_remove.status_code == 200

        # Check if it's deleted.
        usr2_tokens = do_login(client, "usr2", "usr2")
        resp_forbidden = client.get(
            f"/api/v1/board/{board1.id}",
            headers={"Authorization": f"Bearer {usr2_tokens['access_token']}"}
        )
        assert resp_forbidden.status_code == 403


def test_board_permissions(app, client, test_users, test_boards):
    with app.app_context():
        tokens = do_login(client, "usr2", "usr2")
        test_board1: Board = Board.query.get(1)
        test_board2: Board = Board.query.get(2)
        usr2: User = User.find_user("usr2")
        observer_role: BoardRole = BoardRole.query.filter(
            sqla.and_(
                BoardRole.board_id == test_board2.id,
                BoardRole.name == "Observer"
            )
        ).first()

        resp_forbidden = client.get(
            f"/api/v1/board/{test_board1.id}/user-claims",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        assert resp_forbidden.status_code == 403

        resp_claims = client.get(
            f"/api/v1/board/{test_board2.id}/user-claims",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        assert resp_claims.status_code == 200
        assert "id" in resp_claims.json.keys()
        assert resp_claims.json["user_id"] == usr2.id
        assert resp_claims.json["board_id"] == test_board2.id
        assert resp_claims.json["board_role_id"] == observer_role.id
        assert resp_claims.json["is_owner"] == False
        assert "role" in resp_claims.json.keys()
        assert "permissions" in resp_claims.json["role"].keys()
        # Check role permissions
        for permission in resp_claims.json["role"]["permissions"]:
            assert permission["allow"] == False


def test_board_roles(app, client, test_users, test_boards):
    with app.app_context():
        tokens = do_login(client, "usr1", "usr1")
        test_board1: Board = Board.query.get(1)
        test_board3: Board = Board.query.get(3)

        resp_roles = client.get(
            f"/api/v1/board/{test_board1.id}/roles",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )

        assert resp_roles.status_code == 200
        for role in resp_roles.json:
            assert "id" in role.keys()
            assert "name" in role.keys()
            assert "is_admin" in role.keys()
            assert "permissions" in role.keys()

        # usr1 can't access board3
        resp_roles_forbidden = client.get(
            f"/api/v1/board/{test_board3.id}/roles",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        assert resp_roles_forbidden.status_code == 403


def test_find_member(app, client, test_users, test_boards):
    with app.app_context():
        usr1_tokens = do_login(client, "usr1", "usr1")
        usr2: User = User.find_user("usr2")

        # usr1 has access to 1
        board1: Board = Board.query.get(1)
        # usr1 and usr2 (as observer) has access to board 2
        board2: Board = Board.query.get(2)
        board2_observer: BoardRole = BoardRole.query.filter(
            sqla.and_(
                BoardRole.board_id == board2.id,
                BoardRole.name == "Observer"
            )
        ).first()
        assert board2_observer is not None
        # usr1 has no access to 3
        board3: Board = Board.query.get(3)

        # usr1 has no access to board: 3
        resp_forbidden = client.post(
            f"/api/v1/board/{board3.id}/find-member",
            headers={"Authorization": f"Bearer {usr1_tokens['access_token']}"},
            json={
                "user_id": usr2.id
            }
        )
        assert resp_forbidden.status_code == 403

        # usr1 has access to board 1 but specified user not member of board
        resp_allowed_not_found = client.post(
            f"/api/v1/board/{board1.id}/find-member",
            headers={"Authorization": f"Bearer {usr1_tokens['access_token']}"},
            json={
                "user_id": usr2.id
            }
        )

        assert resp_allowed_not_found.status_code == 404

        # usr1 has access to board 2 and usr2 is observer
        resp_allowed_success = client.post(
            f"/api/v1/board/{board2.id}/find-member",
            headers={"Authorization": f"Bearer {usr1_tokens['access_token']}"},
            json={
                "user_id": usr2.id
            }
        )
        assert resp_allowed_success.status_code == 200
        assert resp_allowed_success.json["board_id"] == board2.id
        assert resp_allowed_success.json["board_role_id"] == board2_observer.id

        # Get all members

        # usr1 has no access to 3
        resp_getall_forbidden = client.get(
            f"/api/v1/board/{board3.id}/member",
            headers={"Authorization": f"Bearer {usr1_tokens['access_token']}"},
        )
        assert resp_getall_forbidden.status_code == 403

        # usr1 has access to board 1
        resp_allowed_getall = client.get(
            f"/api/v1/board/{board1.id}/member",
            headers={"Authorization": f"Bearer {usr1_tokens['access_token']}"},
        )

        assert resp_allowed_getall.status_code == 200
        assert len(resp_allowed_getall.json) == 1


def test_add_member(app, client, test_users, test_boards):
    with app.app_context():
        usr1_tokens = do_login(client, "usr1", "usr1")
        usr2: User = User.find_user("usr2")

        # usr1 has access to 1
        board1: Board = Board.query.get(1)
        board1_observer: BoardRole = BoardRole.query.filter(
            sqla.and_(
                BoardRole.board_id == board1.id,
                BoardRole.name == "Observer"
            )
        ).first()
        assert board1_observer is not None
        # usr1 has no access to 3
        board3: Board = Board.query.get(3)
        board3_observer: BoardRole = BoardRole.query.filter(
            sqla.and_(
                BoardRole.board_id == board3.id,
                BoardRole.name == "Observer"
            )
        ).first()

        # TODO: Need to check board allowed user before anything! Read below
        # creating a decorator would be the best for this task.
        # for now providing valid role id

        test_data_board1 = {
            "user_id": usr2.id,
            "board_role_id": board1_observer.id
        }
        test_data_board3 = {
            "user_id": usr2.id,
            "board_role_id": board3_observer.id
        }
        test_data_invalid = {
            "user_id": usr2.id,
            "board_role_id": 400
        }
        # usr1 has no access to 3
        resp_forbidden = client.post(
            f"/api/v1/board/{board3.id}/member",
            headers={"Authorization": f"Bearer {usr1_tokens['access_token']}"},
            json=test_data_board3
        )
        assert resp_forbidden.status_code == 403

        # usr1 has access to 1
        # invalid board_role_id
        resp_invalid = client.post(
            f"/api/v1/board/{board1.id}/member",
            headers={"Authorization": f"Bearer {usr1_tokens['access_token']}"},
            json=test_data_invalid
        )
        assert resp_invalid.status_code == 404

        # valid add member request
        resp_valid = client.post(
            f"/api/v1/board/{board1.id}/member",
            headers={"Authorization": f"Bearer {usr1_tokens['access_token']}"},
            json=test_data_board1
        )
        assert resp_valid.status_code == 200
        assert resp_valid.json["user_id"] == test_data_board1["user_id"]
        assert resp_valid.json["board_role_id"] == test_data_board1["board_role_id"]
