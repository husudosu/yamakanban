from api.model.board import Board
from api.model.user import User
from api.model.list import BoardList
from api.model.card import Card, CardComment

import api.service.board as board_service
import api.service.list as list_service
import api.service.card as card_service

import faker

fake = faker.Faker()


def create_card(user: User, boardlist: BoardList) -> Card:
    return card_service.post_card(
        user,
        boardlist,
        data={
            "title": f"Card - {fake.first_name()} ",
            "description": fake.paragraph(nb_sentences=5)
        }
    )


def create_list(user: User, board: Board) -> BoardList:
    return list_service.post_board_list(
        user,
        board,
        data={
            "title": f"List - {fake.last_name()}"
        }
    )


def create_board(user: User) -> Board:
    return board_service.post_board(
        user,
        {
            "title": "Family"
        }
    )


def create_comment(user: User, card: Card) -> CardComment:
    return card_service.post_card_comment(
        user,
        card,
        {
            "comment": fake.paragraph(nb_sentences=1)
        }
    )
