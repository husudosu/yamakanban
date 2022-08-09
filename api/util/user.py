from functools import wraps
from flask import jsonify

from flask_jwt_extended import verify_jwt_in_request, get_jwt


def role_required(role: str):
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()

            if role in claims['roles']:
                return fn(*args, **kwargs)
            else:
                return jsonify(msg="You don't have permission!"), 403
        return decorator
    return wrapper


def roles_accepted(*roles):
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()

            for role in roles:
                if role in claims['roles']:
                    return fn(*args, **kwargs)
            return jsonify(msg="You don't have permission!"), 403
        return decorator
    return wrapper
