import traceback
import click
from werkzeug.exceptions import HTTPException
import json

from flask import Blueprint, Flask, Response
from flask.cli import AppGroup

from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_compress import Compress

from marshmallow.exceptions import ValidationError

from werkzeug.middleware.profiler import ProfilerMiddleware

from config import Config

db = SQLAlchemy()
migrate = Migrate()
cors = CORS()
jwt = JWTManager()
mail = Mail()
compress = Compress()


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    # app.wsgi_app = ProfilerMiddleware(
    #     app.wsgi_app,
    #     restrictions=[5],
    #     profile_dir='./profile'
    # )

    factory_cli = AppGroup("factory")

    cors.init_app(app)

    db.init_app(app)

    from .model import user

    migrate.init_app(app, db, render_as_batch=True)

    jwt.init_app(app)

    mail.init_app(app)

    # Create the API base blueprint
    api_bp = Blueprint("api_bp", __name__, url_prefix="/api/v1")
    from .controller.user_bp import user_bp
    from .controller.board_bp import board_bp
    from .controller.list_bp import list_bp
    from .controller.card_bp import card_bp

    api_bp.register_blueprint(user_bp)
    api_bp.register_blueprint(board_bp)
    api_bp.register_blueprint(list_bp)
    api_bp.register_blueprint(card_bp)

    app.register_blueprint(api_bp)

    compress.init_app(app)
    # @api_bp.after_request
    # def api_after_request(response):
    #     # jsonify all data from API route
    #     response.set_data(jsonify(response.get_data()))
    #     return response

    @jwt.user_identity_loader
    def user_identity_lookup(user):
        return user.id

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        return user.User.query.filter(
            user.User.id == jwt_data["sub"]).one_or_none()

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload: dict) -> bool:
        jti = jwt_payload["jti"]
        token = db.session.query(
            user.TokenBlocklist.id).filter_by(jti=jti).scalar()
        return token is not None

    @app.before_first_request
    def before_first_request():
        admin_role = user.Role.find_or_create("admin")
        user.Role.find_or_create("user")
        # Check if admin user exists
        if not user.User.query.filter(
            user.User.username == "admin"
        ).first():
            app.logger.info("Creating admin user.")
            usr = user.User.create(
                username="admin",
                password="admin",
                avatar_url="https://i.pravatar.cc/300",
                email="admin@localhost.com",
                timezone=app.config["DEFAULT_TIMEZONE"],
                roles=[admin_role]
            )
            db.session.add(usr)

        db.session.commit()

    @app.errorhandler(ValidationError)
    def handle_validation_exception(e):
        return Response(
            status=400,
            response=json.dumps(
                {
                    "message": "validation_error",
                    "errors": e.messages
                }
            ),
            mimetype='application/json'
        )

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        return Response(
            status=e.code,
            response=json.dumps(
                {
                    "code": e.code,
                    "message": e.description,
                }
            ),
            mimetype='application/json'
        )

    @app.errorhandler(Exception)
    def handle_excpetions(e):
        if not isinstance(e, HTTPException):
            app.logger.exception(traceback.format_exc())
            return Response(
                status=500,
                response=json.dumps({
                    'message': 'internal_server_error',
                    'exception': str(e),
                    'traceback': traceback.format_exc(),
                }),
                mimetype='application/json'
            )

    @factory_cli.command("board")
    @click.argument("userid")
    @click.argument("count")
    def create_board(userid: int, count: int):
        from api.model.user import User
        from api.util.factory import create_board
        usr = User.query.get(userid)
        if not usr:
            raise Exception("User not exists.")
        for _ in range(0, int(count)):
            db.session.add(create_board(usr))
        db.session.commit()

    @factory_cli.command("list")
    @click.argument("userid")
    @click.argument("boardid")
    @click.argument("count")
    def create_list(userid: int, boardid: int, count: int):
        from api.model.user import User
        from api.model.board import Board
        from api.util.factory import create_list
        usr = User.query.get(userid)
        if not usr:
            raise Exception("User not exists.")
        board = Board.query.get(boardid)
        if not board:
            raise Exception("Board not exists.")
        for _ in range(0, int(count)):
            create_list(usr, board)
        db.session.commit()

    @factory_cli.command("card")
    @click.argument("userid")
    @click.argument("boardlistid")
    @click.argument("count")
    def create_card(userid: int, boardlistid: int, count: int):
        from api.model.user import User
        from api.model.list import BoardList
        from api.util.factory import create_card 
        usr = User.query.get(userid)
        if not usr:
            raise Exception("User not exists.")
        boardlist = BoardList.query.get(boardlistid)
        if not boardlist:
            raise Exception("Boardlist not exists.")

        for _ in range(0, int(count)):
            db.session.add(create_card(usr, boardlist))
            # Needs commiting every iteration because of position handling!
            db.session.commit()

    @factory_cli.command("comment")
    @click.argument("userid")
    @click.argument("cardid")
    @click.argument("count")
    def crete_comment(userid: int, cardid: int, count: int):
        from api.model.user import User
        from api.model.card import Card
        from api.util.factory import create_comment
        usr = User.query.get(userid)
        if not usr:
            raise Exception("User not exists.")
        card = Card.query.get(cardid)

        if not card:
            raise Exception("Card not exists.")
        for _ in range(0, int(count)):
            db.session.add(create_comment(usr, card))
        db.session.commit()

    app.cli.add_command(factory_cli)

    return app