

from api.model.board import Board
from api.model.list import BoardList

from tests.conftest import do_login


def test_get_board_lists(app, client, test_users, test_boardlists):
    with app.app_context():
        tokens = do_login(client, "usr1", "usr1")
        test_board = Board.query.get(1)
        resp = client.get(
            f"/api/v1/board/{test_board.id}/list",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )

        assert resp.status_code == 200
        assert len(resp.json) == 5
        # Check data of resp
        # ! Lists should be ordered by position!
        for i, entry in enumerate(resp.json):
            assert entry["title"] == f"Test list {test_board.id} - {i + 1}"
            assert entry["position"] == i + 1


def test_get_board_lists_forbidden(app, client, test_users, test_boardlists):
    with app.app_context():
        tokens = do_login(client, "usr2", "usr2")
        test_board = Board.query.get(1)
        resp = client.get(
            f"/api/v1/board/{test_board.id}/list",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        resp.status_code == 403


def test_add_board_lists(app, client, test_users, private_boards):
    with app.app_context():
        tokens = do_login(client, "usr1", "usr1")
        test_board = Board.query.get(1)
        test_data = {
            "board_id": test_board.id,
            "title": "Test list",
            "position": 1
        }
        resp = client.post(
            f"/api/v1/board/{test_board.id}/list",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json=test_data
        )
        assert resp.status_code == 200
        assert resp.json["board_id"] == test_board.id
        assert resp.json["title"] == test_data["title"]
        assert resp.json["position"] == test_data["position"]


def test_add_board_lists_forbidden(app, client, test_users, private_boards):
    with app.app_context():
        tokens = do_login(client, "usr2", "usr2")
        test_board = Board.query.get(1)
        test_data = {
            "board_id": test_board.id,
            "title": "Test list",
            "position": 1
        }
        resp = client.post(
            f"/api/v1/board/{test_board.id}/list",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json=test_data
        )
        assert resp.status_code == 403


def test_update_board_list(app, client, test_users, test_boardlists):
    with app.app_context():
        tokens = do_login(client, "usr1", "usr1")
        test_boardlist = BoardList.query.get(1)
        test_data = {
            "title": "Test list updated",
        }
        resp = client.patch(
            f"/api/v1/list/{test_boardlist.id}",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json=test_data
        )
        assert resp.status_code == 200
        assert resp.json["title"] == test_data["title"]


def test_delete_boardlist(app, client, test_users, test_boardlists):
    with app.app_context():
        tokens = do_login(client, "usr1", "usr1")
        test_boardlist = BoardList.query.get(1)
        resp = client.delete(
            f"/api/v1/list/{test_boardlist.id}",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert resp.status_code == 200
        assert BoardList.query.get(1) is None
