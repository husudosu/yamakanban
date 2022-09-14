from api.model.board import Board
from api.model.list import BoardList
from api.model.user import User
from tests.conftest import do_login


def test_get_list_cards(app, client, test_cards):
    with app.app_context():
        tokens = do_login(client, "usr1", "usr1")
        # usr1 can access board1
        board1: Board = Board.query.get(1)
        board1_list: BoardList = board1.lists[0]
        # usr1 cannot access board3
        board3: Board = Board.query.get(3)
        board3_list: BoardList = board3.lists[0]

        # Forbidden
        resp_forbidden = client.get(
            f"/api/v1/list/{board3_list.id}/card",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert resp_forbidden.status_code == 403

        # Allowed
        resp_allowed = client.get(
            f"/api/v1/list/{board1_list.id}/card",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        assert resp_allowed.status_code == 200
        assert len(resp_allowed.json) > 0


def test_get_card_activities(app, client, test_cards):
    with app.app_context():
        tokens = do_login(client, "usr2", "usr2")
        # Usr2 has no access to board2
        board1: Board = Board.query.get(1)
        board1_list: BoardList = BoardList.query.filter(
            BoardList.board_id == board1.id
        ).first()
        # Usr2 has access to board2 (only observer)
        board2: Board = Board.query.get(2)
        board2_list = BoardList.query.filter(
            BoardList.board_id == board2.id).first()

        # Valid response
        resp = client.get(
            f"/api/v1/card/{board2_list.cards[0].id}/activities",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert resp.status_code == 200

        # Forbidden
        resp_forbidden = client.get(
            f"/api/v1/card/{board1_list.cards[0].id}/activities",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert resp_forbidden.status_code == 403


def test_post_card(app, client, test_boardlists):
    with app.app_context():
        tokens = do_login(client, "usr2", "usr2")
        # Usr2 has no access to board1
        board1: Board = Board.query.get(1)
        board1_list: BoardList = BoardList.query.filter(
            BoardList.board_id == board1.id
        ).first()

        # Usr2 only observer on board2
        board2: Board = Board.query.get(2)
        board2_list = BoardList.query.filter(
            BoardList.board_id == board2.id).first()

        # Usr2 owns board3
        board3: Board = Board.query.get(3)
        board3_list = BoardList.query.filter(
            BoardList.board_id == board3.id).first()

        # Response forbidden
        resp_forbidden = client.post(
            f"/api/v1/list/{board1_list.id}/card",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json={
                "title": "Test"
            }
        )
        assert resp_forbidden.status_code == 403

        # Repsonse forbidden because of role (Observer)
        resp_forbidden = client.post(
            f"/api/v1/list/{board2_list.id}/card",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json={
                "title": "Test"
            }
        )
        assert resp_forbidden.status_code == 403

        # Response validation error
        resp_validation_err = client.post(
            f"/api/v1/list/{board3_list.id}/card",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json={
                "description": "Test"
            }
        )
        assert resp_validation_err.status_code == 400

        # Response valid
        test_data = {
            "title": "Test",
            "description": "Test"
        }
        resp_valid = client.post(
            f"/api/v1/list/{board3_list.id}/card",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json=test_data
        )
        assert resp_valid.status_code == 200
        assert resp_valid.json["title"] == test_data["title"]
        assert resp_valid.json["description"] == test_data["description"]


def test_update_card(app, client, test_cards):
    with app.app_context():
        tokens = do_login(client, "usr2", "usr2")
        # Usr2 has no access to board1
        board1: Board = Board.query.get(1)
        # Usr2 only observer on board2
        board2: Board = Board.query.get(2)
        # Usr2 owns board3
        board3: Board = Board.query.get(3)

        test_data = {
            "title": "Title updated",
        }

        # Response forbidden
        resp_forbidden = client.patch(
            f"/api/v1/card/{board1.lists[0].cards[0].id}",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json=test_data
        )
        assert resp_forbidden.status_code == 403

        # Repsonse forbidden because of role (Observer)
        resp_forbidden = client.patch(
            f"/api/v1/card/{board2.lists[0].cards[0].id}",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json=test_data
        )
        assert resp_forbidden.status_code == 403

        # Response valid
        resp_valid = client.patch(
            f"/api/v1/card/{board3.lists[0].cards[0].id}",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json=test_data
        )
        assert resp_valid.status_code == 200
        assert resp_valid.json["title"] == test_data["title"]

        # Invalid response (Recived list which exists on other board)
        resp_invalid_list = client.patch(
            f"/api/v1/card/{board3.lists[0].cards[0].id}",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json={
                "list_id": board2.lists[0].id
            }
        )
        assert resp_invalid_list.status_code == 400
        assert "list_id" in resp_invalid_list.json["errors"].keys()

        # Valid response moving list
        resp_valid_list = client.patch(
            f"/api/v1/card/{board3.lists[0].cards[0].id}",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json={
                "list_id": board3.lists[1].id
            }
        )
        assert resp_valid_list.status_code == 200


def test_delete_card(app, client, test_cards):
    with app.app_context():
        tokens = do_login(client, "usr2", "usr2")
        # Usr2 has no access to board1
        board1: Board = Board.query.get(1)
        # Usr2 only observer on board2
        board2: Board = Board.query.get(2)
        # Usr2 owns board3
        board3: Board = Board.query.get(3)

        # Response forbidden
        resp_forbidden = client.delete(
            f"/api/v1/card/{board1.lists[0].cards[0].id}",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert resp_forbidden.status_code == 403

        # Repsonse forbidden because of role (Observer)
        resp_forbidden = client.delete(
            f"/api/v1/card/{board2.lists[0].cards[0].id}",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert resp_forbidden.status_code == 403

        # Response valid
        resp_valid = client.delete(
            f"/api/v1/card/{board3.lists[0].cards[0].id}",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert resp_valid.status_code == 200


def test_post_card_comment(app, client, test_cards):
    with app.app_context():
        usr2 = User.find_user("usr2")
        tokens = do_login(client, "usr2", "usr2")
        # Usr2 has no access to board1
        board1: Board = Board.query.get(1)
        # Usr2 only observer on board2
        board2: Board = Board.query.get(2)
        # Usr2 owns board3
        board3: Board = Board.query.get(3)

        test_data = {
            "comment": "Test comment"
        }
        # Response forbidden
        resp_forbidden = client.post(
            f"/api/v1/card/{board1.lists[0].cards[0].id}/comment",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json=test_data
        )
        assert resp_forbidden.status_code == 403

        # Repsonse forbidden because of role (Observer)
        resp_forbidden = client.post(
            f"/api/v1/card/{board2.lists[0].cards[0].id}/comment",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json=test_data
        )
        assert resp_forbidden.status_code == 403

        # Response valid
        resp_valid = client.post(
            f"/api/v1/card/{board3.lists[0].cards[0].id}/comment",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json=test_data
        )
        assert resp_valid.status_code == 200
        assert resp_valid.json["card_id"] == board3.lists[0].cards[0].id
        assert resp_valid.json["comment"]["comment"] == test_data["comment"]
        assert resp_valid.json["comment"]["user_id"] == usr2.id
