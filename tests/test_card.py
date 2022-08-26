from api.model.board import Board
from api.model.list import BoardList
from tests.conftest import do_login


def test_get_card_activities(app, client, test_cards):
    with app.app_context():
        tokens = do_login(client, "usr2", "usr2")
        # Usr2 has no access to board2
        board1: Board = Board.query.get(1)
        board1_list: BoardList = BoardList.query.filter(
            BoardList.board_id == board1.id
        ).first()
        # Usr2 has access to board2
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
