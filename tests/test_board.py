from api.model.board import Board
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
    assert len(resp.json) == 2


def test_get_board_allowed(app, client, test_users, test_boards):
    # ! Only allow getting board info if available for user.
    with app.app_context():
        test_board = Board.query.get(1)
        tokens = do_login(client, "usr1", "usr1")
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


def test_get_board_forbidden(app, client, test_users, test_boards):
    with app.app_context():
        tokens = do_login(client, "usr2", "usr2")
        test_board = Board.query.get(1)
        resp = client.get(
            f"/api/v1/board/{test_board.id}",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        assert resp.status_code == 403


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


# Member add/ remove from board
def test_invalid_add_member(app, client, test_users, test_boards):
    with app.app_context():
        usr2_tokens = do_login(client, "usr2", "usr2")
        usr_tokens = do_login(client, "usr1", "usr1")
        test_board: Board = Board.query.get(1)
        usr1: User = User.find_user("usr1")
        usr2: User = User.find_user("usr2")

        resp_forbidden = client.post(
            f"/api/v1/board/{test_board.id}/add-member",
            headers={"Authorization": f"Bearer {usr2_tokens['access_token']}"},
            json={
                "user_id": usr2.id,
                "board_id": test_board.id,
                "board_role_id": test_board.board_roles[0].id
            }
        )
        assert resp_forbidden.status_code == 403

        # You don't allowed add yourself again.
        resp_add_myself = client.post(
            f"/api/v1/board/{test_board.id}/add-member",
            headers={"Authorization": f"Bearer {usr_tokens['access_token']}"},
            json={
                "user_id": usr1.id,
                "board_id": test_board.id,
                "board_role_id": test_board.board_roles[0].id
            }
        )
        assert resp_add_myself.status_code == 400


def test_valid_add_member(app, client, test_users, test_boards):
    with app.app_context():
        tokens = do_login(client, "usr1", "usr1")
        test_board: Board = Board.query.get(1)
        usr2: User = User.find_user("usr2")

        resp_valid = client.post(
            f"/api/v1/board/{test_board.id}/add-member",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json={
                "user_id": usr2.id,
                "board_id": test_board.id,
                "board_role_id": test_board.board_roles[0].id
            }
        )
        assert resp_valid.status_code == 200


def test_invalid_add_member(app, client, test_users, test_boards):
    with app.app_context():
        tokens = do_login(client, "usr2", "usr2")
        test_board: Board = Board.query.get(1)
        usr1: User = User.find_user("usr1")

        resp_forbidden = client.post(
            f"/api/v1/board/{test_board.id}/add-member",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json={
                "user_id": usr1.id,
                "board_id": test_board.id,
                "board_role_id": test_board.board_roles[0].id
            }
        )
        assert resp_forbidden.status_code == 403


def test_invalid_remove_member(app, client, test_users, test_boards):
    with app.app_context():
        tokens = do_login(client, "usr1", "usr1")
        '''
        Expected behaviour:
            - Admin board role required for adding/removing members
            - At least one admin required for every board!
            - The user can't delete own access from board.
        '''
