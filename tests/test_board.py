from api.model.board import Board
from .conftest import do_login


def test_get_boards(client, test_users, private_boards):
    tokens = do_login(client, "usr2", "usr2")
    resp = client.get(
        "/api/v1/board",
        headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    
    assert resp.status_code == 200
    # Check if got only available boards for user
    assert len(resp.json) == 2


def test_get_board_allowed(app, client, test_users, private_boards):
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


def test_get_board_forbidden(app, client, test_users, private_boards):
    with app.app_context():
        tokens = do_login(client, "usr2", "usr2")
        test_board = Board.query.get(1)
        resp = client.get(
            f"/api/v1/board/{test_board.id}",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        assert resp.status_code == 403


def test_create_private_board(app, client, test_users):
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


def test_update_private_board(app, client, test_users, private_boards):
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


def test_delete_board(app, client, test_users, private_boards):
    with app.app_context():
        tokens = do_login(client, "usr1", "usr1")
        test_board = Board.query.get(1)

        resp = client.delete(
            f"/api/v1/board/{test_board.id}",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert resp.status_code == 200

