from datetime import datetime
from flask import Blueprint, request, current_app, make_response, jsonify, abort, render_template
from flask.views import MethodView
from flask_jwt_extended import (
    create_access_token, jwt_required,
    get_jwt, current_user,
    create_refresh_token, decode_token,
    set_access_cookies, set_refresh_cookies,
    unset_jwt_cookies
)
from datetime import timedelta
import sqlalchemy as sqla
from api.app import db
from api.util.dto import UserDTO
from api.model.user import User, Token
from api.task_queue.sendmail import send_mail


user_bp = Blueprint("user_bp", __name__, url_prefix="/auth")


def create_additional_claims(usr: User):
    return {
        "username": usr.username,
        "email": usr.email,
        "roles": [role.name for role in usr.roles],
        "name": usr.name
    }


class LoginAPI(MethodView):
    decorators = [jwt_required(optional=True)]

    def post(self):
        """
        Create Login.
        """
        if current_user:
            abort(400, "Already logged in!")

        login = UserDTO.login_schema.load(request.json)
        usr: User = User.find_user(login["username"])

        if not usr or not usr.check_password(login["password"]):
            abort(401, "Invalid username/password")
        if usr.archived:
            abort(401, "Your user has been archived!")

        access_token = create_access_token(
            identity=usr,
            additional_claims=create_additional_claims(usr),
            expires_delta=current_app.config["JWT_ACCESS_TOKEN_EXPIRES"] if not login["remember_me"] else timedelta(
                days=365)
        )
        refresh_token = create_refresh_token(
            identity=usr,
            expires_delta=current_app.config["JWT_REFRESH_TOKEN_EXPIRES"] if not login["remember_me"] else timedelta(
                days=730)
        )
        access_token_decoded = decode_token(access_token)
        refresh_token_decoded = decode_token(refresh_token)
        # Add tokens to db
        db.session.add_all(
            [
                Token(
                    user_id=usr.id,
                    jti=access_token_decoded["jti"],
                    type=access_token_decoded["type"],
                    created_at=datetime.now()
                ),
                Token(
                    user_id=usr.id,
                    jti=refresh_token_decoded["jti"],
                    type=refresh_token_decoded["type"],
                    created_at=datetime.now()
                ),
            ]
        )
        usr.update_login_history(request.remote_addr)

        # Create response and set cookies
        resp = make_response(
            jsonify(access_token=access_token, refresh_token=refresh_token))
        set_access_cookies(resp, access_token)
        set_refresh_cookies(resp, refresh_token)

        return resp


class RegisterAPI(MethodView):
    decorators = [jwt_required(optional=True)]

    def post(self):
        """
        Create Register.
        """
        if current_user:
            abort(400, "Already logged in!")
        data = UserDTO.register_schema.load(request.json)
        usr = User.create(**data)

        # Assign default role
        usr.assign_role("user")

        db.session.add(usr)
        db.session.commit()

        return UserDTO.user_schema.dump(usr)


class ForgotPasswordAPI(MethodView):
    decorators = [jwt_required(optional=True)]

    def post(self):
        """
        Create ForgotPassword.
        """
        if current_user:
            abort(400, "Already logged in!")

        if not request.json.get("username"):
            abort(400, "Username/e-mail missing!")

        usr = User.find_user(request.json["username"])
        if not usr:
            abort(400, "Username/e-mail not found!")
        if usr.archived:
            abort(400, "Your user has been archived!")

        reset_token = create_access_token(
            identity=usr,
            expires_delta=current_app.config["RESET_PASSWORD_TOKEN_EXPIRES"]
        )
        reset_token_decoded = decode_token(reset_token)
        db.session.add(
            Token(
                user_id=usr.id,
                jti=reset_token_decoded["jti"],
                type=reset_token_decoded["type"],
                created_at=datetime.now()
            )
        )
        db.session.commit()
        send_mail.delay(
            current_app.config["MAIL_DEFAULT_SENDER"],
            usr.email,
            "Yamakanban: Reset password request",
            render_template("auth/forgot_password.html",
                            reset_token=reset_token),
            render_template("auth/forgot_password.txt",
                            reset_token=reset_token)
        )
        return {"message": "Check your inbox."}


class ResetPasswordAPI(MethodView):
    decorators = [jwt_required(optional=True)]

    def check_if_token_expired(self):
        decoded_token = decode_token(request.args["reset_token"])
        # Check if token already expired
        is_in_blocklist = Token.query.filter(
            sqla.and_(
                Token.jti == decoded_token["jti"],
                Token.revoked == True
            )
        ).first()

        if is_in_blocklist:
            raise abort(403, "Invalid token. Expired or already used.")

    def get(self):
        if current_user:
            abort(400, "You already logged in!")
        if not request.args.get("reset_token"):
            abort(400, "Reset token missing!")

        self.check_if_token_expired()
        return render_template("auth/reset_password.html")

    def post(self):
        """
        Create ResetPassword.
        """
        decoded_token = decode_token(request.args["reset_token"])

        # Check if expired
        self.check_if_token_expired()

        usr = User.query.get(decoded_token["sub"])
        usr.update(password=request.form["newPassword"])

        Token.query.filter(
            Token.jti == decoded_token["jti"]
        ).update({"revoked": True})
        # db.session.add(
        #     Token(
        #         jti=decoded_token["jti"],
        #         created_at=datetime.now(),
        #         revoked=True
        #     )
        # )
        db.session.commit()

        return "Password has been changed."


class UserAPI(MethodView):
    decorators = [jwt_required()]

    def get(self, id):
        """
        Gets User.
        """
        if not current_user:
            abort(401, "Not logged in!")

        if id == "me":
            # Returns current user claims
            return {
                "id": current_user.id,
                "username": current_user.username,
                "email": current_user.email,
                "roles": [role.name for role in current_user.roles],
                "name": current_user.name,
                "timezone": current_user.timezone
            }
        elif id:
            if current_user.id == int(id):
                return UserDTO.user_schema.dump(current_user)
            elif current_user.has_role("admin"):
                return UserDTO.user_schema.dump(User.get_or_404(id))
        else:
            return UserDTO.guest_user_schema.dump(User.query.all(), many=True)

    def patch(self, id: int):
        """
        Updates User.
        """
        if current_user.id == int(id):
            data = UserDTO.update_user_schema.load(
                request.json, session=db.session, instance=current_user)
            current_user.update(**data)
            db.session.commit()
            return UserDTO.user_schema.dump(current_user)
        elif not current_user.has_role("admin"):
            abort(403, "Don't have permission!")
        else:
            # Update user as admin
            usr = User.query.get(id)
            if not usr:
                abort(404, "User not found.")
            data = UserDTO.update_user_schema_admin.load(
                request.json, session=db.session, instance=usr)
            usr.update(**data)
            db.session.commit()
            return UserDTO.user_schema.dump(usr)

    def delete(self, id: int):
        """
        Deletes User.
        """
        if current_user.id == int(id):
            current_user.archived = True
            Token.revoke_all_tokens_for_user(current_user.id)
            db.session.commit()
            return {}
        elif not current_user.has_role("admin"):
            abort(403, "Don't have permission")
        else:
            usr = User.get_or_404(id)
            if not usr.archived:
                usr.archived = True
                Token.revoke_all_tokens_for_user(usr.id)
                db.session.commit()
            else:
                db.session.delete(usr)
                db.session.commit()
            return {}


class LogoutAPI(MethodView):
    decorators = [jwt_required(verify_type=False)]

    def post(self):
        """
        Create Logout.
        """
        # Can apply to Access token and refresh token too!
        Token.revoke_token(get_jwt())

        response = jsonify({"message": "Token revoked"})
        unset_jwt_cookies(response)
        return response


class RefreshTokenAPI(MethodView):
    decorators = [jwt_required(refresh=True)]

    def post(self):
        if current_user.archived:
            response = make_response(
                jsonify({"message": "Your user has been archived!"}),
                401
            )
            unset_jwt_cookies(response)
            return response

        access_token = create_access_token(
            identity=current_user,
            additional_claims=create_additional_claims(current_user)
        )
        return jsonify(access_token=access_token)


class FindUserAPI(MethodView):
    decorators = []

    def post(self):
        usr = User.find_user(request.json["username"])
        return UserDTO.guest_user_schema.dump(usr) if usr else abort(404)


login_view = LoginAPI.as_view("login-view")
register_view = RegisterAPI.as_view("register-view")
forgotpassword_view = ForgotPasswordAPI.as_view("forgotpassword-view")
user_view = UserAPI.as_view("user-view")
logout_view = LogoutAPI.as_view("logout-view")
refreshtoken_view = RefreshTokenAPI.as_view("refreshtoken-view")
finduser_view = FindUserAPI.as_view("finduser-view")
resetpassword_view = ResetPasswordAPI.as_view("resetpassword-view")

user_bp.add_url_rule("/login", view_func=login_view, methods=["POST"])
user_bp.add_url_rule("/register", view_func=register_view, methods=["POST"])
user_bp.add_url_rule("/forgot-password",
                     view_func=forgotpassword_view, methods=["POST"])
user_bp.add_url_rule("/users/<id>", view_func=user_view,
                     methods=["GET", "PATCH", "DELETE"])
user_bp.add_url_rule("/logout", view_func=logout_view, methods=["POST"])
user_bp.add_url_rule("/refresh", view_func=refreshtoken_view, methods=["POST"])
user_bp.add_url_rule("/find-user", view_func=finduser_view, methods=["POST"])
user_bp.add_url_rule(
    "/reset-password", view_func=resetpassword_view, methods=["GET", "POST"])
