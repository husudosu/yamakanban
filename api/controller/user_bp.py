from datetime import datetime
from flask import (
    jsonify, make_response, render_template,
    request, Blueprint, current_app, abort
)
from flask_jwt_extended import (
    create_access_token, jwt_required,
    get_jwt, current_user, verify_jwt_in_request,
    create_refresh_token, decode_token,
    set_access_cookies, set_refresh_cookies,
    unset_jwt_cookies
)
import werkzeug.exceptions as we

from ..app import db
from ..model.user import TokenBlocklist, User
from ..util.schemas import ResetPasswordSchema, UserSchema
from ..mail_middleware import send_async_email
from datetime import timedelta

user_bp = Blueprint("user_bp", __name__, url_prefix="/auth")

user_schema = UserSchema()
guest_user_schema = UserSchema(
    only=(
        "id", "username", "name",
        "avatar_url", "timezone",
        "roles",
    )
)
update_user_schema = UserSchema(
    # FIXME: Dont't know why name field needed here, name required is False!
    partial=("username", "password", "email",),
    exclude=("roles",)
)
register_user_schema = UserSchema(
    exclude=("current_password", "roles",)
)
update_user_schema_admin = UserSchema(
    partial=True, exclude=("current_password",))
reset_password_schema = ResetPasswordSchema()


@user_bp.route("/login", methods=["POST"])
def login():
    username = request.json.get("username", None)
    password = request.json.get("password", None)
    remember_me = request.json.get("remember_me", False)
    usr = User.find_user(username)

    if not usr or not usr.check_password(password):
        raise we.Unauthorized("Invalid username/password!")

    additional_claims = {
        "username": usr.username,
        "email": usr.email,
        "roles": [role.name for role in usr.roles],
        "name": usr.name
    }
    access_token = create_access_token(
        identity=usr,
        additional_claims=additional_claims,
        expires_delta=current_app.config["JWT_ACCESS_TOKEN_EXPIRES"] if not remember_me else timedelta(
            days=365)
    )
    refresh_token = create_refresh_token(
        identity=usr,
        expires_delta=current_app.config["JWT_REFRESH_TOKEN_EXPIRES"] if not remember_me else timedelta(
            days=730)
    )

    # Update login history
    if usr.current_login_at:
        usr.last_login_at = usr.current_login_at
    usr.current_login_at = datetime.now()

    if usr.current_login_ip:
        usr.last_login_ip = usr.current_login_ip
    usr.current_login_ip = request.remote_addr

    db.session.commit()

    # Create response and set cookies
    resp = make_response(
        jsonify(access_token=access_token, refresh_token=refresh_token))
    set_access_cookies(resp, access_token)
    set_refresh_cookies(resp, refresh_token)
    return resp


@user_bp.route("/me", methods=["GET"])
@jwt_required()
def get_user_claims():
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "roles": [role.name for role in current_user.roles],
        "name": current_user.name,
        "timezone": current_user.timezone
    }


@user_bp.route("/register", methods=["POST"])
def register():
    data = register_user_schema.load(request.json)
    usr = User.create(**data)

    # Assign default role
    usr.assign_role("user")

    db.session.add(usr)
    db.session.commit()
    db.session.refresh(usr)

    return user_schema.dump(usr)


@user_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    if not request.json.get("username"):
        raise we.BadRequest("Username/e-mail missing!")

    usr = User.find_user(request.json["username"])
    if not usr:
        raise we.BadRequest("User not found.")
    reset_token = create_access_token(
        identity=usr,
        expires_delta=current_app.config["RESET_PASSWORD_TOKEN_EXPIRES"]
    )
    send_async_email(
        subject="[JWT Auth] reset password requested",
        sender="husudosu94@gmail.com",
        recipients=[usr.email],
        text_body=render_template(
            "forgot_password.txt", reset_token=reset_token),
        html_body=render_template(
            "forgot_password.html", reset_token=reset_token)
    )
    return {"message": "Check your inbox."}


def reset_password(reset_token, new_password):
    decoded_token = decode_token(reset_token)

    # Check if expired
    is_in_blocklist = TokenBlocklist.query.filter(
        TokenBlocklist.jti == decoded_token["jti"]).first()

    if is_in_blocklist:
        raise we.Forbidden("Invalid token. Expired or already used.")

    usr = User.query.get(decoded_token["sub"])
    usr.update(password=new_password)

    db.session.add(TokenBlocklist(
        jti=decoded_token["jti"], created_at=datetime.now()))
    db.session.commit()


@user_bp.route("/reset-password", methods=["POST"])
def reset_password_api():
    data = reset_password_schema.load(request.json)
    reset_password(data["reset_token"], data["password"])
    return {"message": "Password has been changed."}


@user_bp.route("/reset-password-web", methods=["GET", "POST"])
def reset_password_frontend():
    """Creates a reset password frontend. Useful when you build a mobile app.
    """
    if not request.args.get("reset_token"):
        raise we.BadRequest("Reset token missing!")

    if request.method == "GET":
        return render_template("reset_password.html")
    else:
        reset_password(
            request.args["reset_token"],
            request.form["newPassword"]
        )
        return "Password has been changed."


@user_bp.route("/users/<id>", methods=["GET"])
@jwt_required(optional=True)
def get_user(id: int):
    """Gets User if it's allowed

    Args:
        id (int): User id
    """
    id = int(id)
    is_admin = False
    if not current_app.config["VIEW_USER_AS_ANONYMOUS"]:
        verify_jwt_in_request()
        is_admin = current_user.has_role("admin")

    if current_user and current_user.id == id:
        return user_schema.dump(current_user)
    elif is_admin:
        return user_schema.dump(User.query.get_or_404(id))
    elif current_app.config["VIEW_USER_AS_ANONYMOUS"]:
        return guest_user_schema.dump(User.query.get_or_404(id))
    elif current_app.config["ALLOW_TO_VIEW_OTHER_USER"]:
        if is_admin:
            return user_schema.dump(User.query.get_or_404(id))
        return guest_user_schema.dump(User.query.get_or_404(id))
    else:
        raise we.Forbidden("You don't have permission!")


@user_bp.route("/users/<id>", methods=["PATCH"])
@jwt_required()
def patch_user(id: int):
    if current_user.id == int(id):
        data = update_user_schema.load(
            request.json, session=db.session, instance=current_user)
        current_user.update(**data)
        db.session.commit()
        db.session.refresh(current_user)
        return user_schema.dump(current_user)
    elif not current_user.has_role("admin"):
        raise we.Forbidden("Don't have permission.")
    else:
        usr = User.query.get(id)
        if not usr:
            raise we.NotFound("User not found.")
        data = update_user_schema_admin.load(
            request.json, session=db.session, instance=usr)
        usr.update(**data)
        db.session.commit()
        db.session.refresh(usr)
        return user_schema.dump(usr)


@user_bp.route("/users/<id>", methods=["DELETE"])
@jwt_required()
def delete_user(id: int):
    if current_user.id == int(id):
        db.session.delete(current_user)
        db.session.commit()
        return {}
    elif not current_user.has_role("admin"):
        raise we.Forbidden("Don't have permission.")
    else:
        usr = User.query.get(id)
        if not usr:
            raise we.NotFound("User not found.")
        db.session.delete(usr)
        db.session.commit()
        return {}


@user_bp.route("/users/me", methods=["GET", "PATCH", "DELETE"])
@jwt_required()
def get_me():
    if request.method == "GET":
        return user_schema.dump(current_user)
    elif request.method == "PATCH":
        return patch_user(current_user.id)
    else:
        return delete_user(current_user.id)


@user_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    access_token = create_access_token(
        identity=current_user,
        additional_claims={"roles": [role.name for role in current_user.roles]}
    )
    return jsonify(access_token=access_token)


@user_bp.route("/logout", methods=["POST"])
@jwt_required(verify_type=False)
def logout():
    # Can apply to Access token and refresh token too!
    token = get_jwt()
    db.session.add(
        TokenBlocklist(
            user_id=current_user.id,
            jti=token["jti"],
            type=token["type"],
            created_at=datetime.now()
        )
    )
    db.session.commit()

    response = jsonify({"message": "Token revoked"})
    unset_jwt_cookies(response)
    return response


@user_bp.route("/find-user", methods=["POST"])
def find_user():
    usr = User.find_user(request.json["username"])
    return guest_user_schema.dump(usr) if usr else abort(404)
