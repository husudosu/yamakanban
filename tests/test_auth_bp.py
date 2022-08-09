from flask_jwt_extended import decode_token
from .conftest import do_login
from api.model.user import User


def test_valid_register(client):
    """Tests a valid, ideal register case"""
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "username": "my_test_user",
            "password": "my_test_user",
            "email": "my_test_user@localhost.com",
            "full_name": "My Test User",
        }
    )
    assert resp.status_code == 200
    assert resp.json["id"]
    assert resp.json["roles"]
    assert resp.json["username"] == "my_test_user"
    assert "password" not in resp.json.keys()
    assert resp.json["email"] == "my_test_user@localhost.com"
    assert resp.json["full_name"] == "My Test User"


def test_invalid_register(client):
    """Test an invalid registration"""

    # Do a valid register for testing unique variables.
    test_valid_register(client)

    resp = client.post(
        "/api/v1/auth/register",
        json={
            "username": "my_test_user",
            "password": "test",
            "email": "my_test_user@localhost.com"
        }
    )
    assert resp.status_code == 400
    assert resp.json["message"] == "validation_error"
    assert "Username already taken." in resp.json["errors"]["username"]
    assert "Email already taken." in resp.json["errors"]["email"]


def test_valid_login(client, app, test_users):
    """Test login."""

    # Valid login
    resp = client.post(
        "/api/v1/auth/login",
        json={
            "username": "usr1",
            "password": "usr1"
        }
    )

    assert resp.status_code == 200
    assert "access_token" in resp.json
    assert "refresh_token" in resp.json

    # Decode Access Token and check additional claims
    with app.app_context():
        decoded_token = decode_token(resp.json["access_token"])
        assert "roles" in decoded_token
        assert decoded_token["username"] == "usr1"
        assert decoded_token["email"] == "usr1@localhost.com"

    # Test if logged in user works
    me = client.get("/api/v1/auth/users/me",
                    headers={"Authorization": f"Bearer {resp.json['access_token']}"})
    assert me.status_code == 200


def test_logout(client, test_users):
    """Testing logout procedures, revoking tokens."""

    # Not logged in should fail
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 401

    # Test with logged-in user.
    tokens = do_login(client, "usr1", "usr1")

    # Revoke both access and refresh tokens.
    revoke_access = client.post(
        "/api/v1/auth/logout", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert revoke_access.status_code == 200

    revoke_refresh = client.post(
        "/api/v1/auth/logout", headers={"Authorization": f"Bearer {tokens['refresh_token']}"})
    assert revoke_refresh.status_code == 200

    # Test a route
    test_resp = client.get(
        "/api/v1/auth/users/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert test_resp.status_code == 401
    assert test_resp.json["message"] == "Token has been revoked"


def test_refresh_token(client, test_users):
    """Tests refreshing token"""
    tokens = do_login(client, "usr1", "usr1")

    # Revoke access token
    revoke_access = client.post(
        "/api/v1/auth/logout", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert revoke_access.status_code == 200

    refresh_token = client.post(
        "/api/v1/auth/refresh", headers={"Authorization": f"Bearer {tokens['refresh_token']}"}
    )
    assert refresh_token.status_code == 200
    assert refresh_token.json["access_token"]

    # Try new token
    test_resp = client.get(
        "/api/v1/auth/users/me",
        headers={
            "Authorization": f"Bearer {refresh_token.json['access_token']}"}
    )
    assert test_resp.status_code == 200


def test_invalid_login(client):
    """Test invalid login"""
    resp = client.post(
        "/api/v1/auth/login",
        json={
            "username": "abc",
            "password": "abc"
        }
    )

    assert resp.status_code == 401
    assert resp.json["message"] == "Invalid username/password!"


def test_user_get_me(client, test_users):
    """Test get currently logged in user."""
    # Test as anonymous
    resp = client.get(
        "/api/v1/auth/users/me"
    )
    assert resp.status_code == 401

    tokens = do_login(client, "usr1", "usr1")
    resp = client.get(
        "/api/v1/auth/users/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert resp.json["username"] == "usr1"
    assert "password" not in resp.json.keys()
    assert resp.json["email"] == "usr1@localhost.com"
    assert "roles" in resp.json.keys()
    assert "last_login_ip" in resp.json.keys()
    assert "current_login_ip" in resp.json.keys()
    assert "last_login_at" in resp.json.keys()
    assert "current_login_at" in resp.json.keys()



def test_user_patch_me(client, test_users, test_admin):
    """Test updating logged in user"""
    tokens = do_login(client, "usr1", "usr1")

    resp_invalid = client.patch(
        "/api/v1/auth/users/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={
            "roles": ["admin"],
            "current_password": "invalid_current_password"
        }
    )
    print(resp_invalid.json)

    assert resp_invalid.status_code == 400
    # Role editing for regular user should be disabled
    assert "roles" in resp_invalid.json["errors"].keys()

    valid_edit_missing_pw = client.patch(
        "/api/v1/auth/users/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={
            "email": "test_one@localhost.com"
        }
    )
    assert valid_edit_missing_pw.status_code == 400
    assert "current_password" in valid_edit_missing_pw.json["errors"].keys()

    valid_edit = client.patch(
        "/api/v1/auth/users/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={
            "username": "usr1",
            "email": "test_one@localhost.com",
            "password": "usr1_newpw",
            "current_password": "usr1"
        }
    )
    assert valid_edit.status_code == 200
    assert valid_edit.json["username"] == "usr1"
    assert valid_edit.json["email"] == "test_one@localhost.com"

    # Check unique
    unique_failure = client.patch(
        "/api/v1/auth/users/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={
            "username": "usr2",
            "email": "usr2@localhost.com",
            "current_password": "usr1"
        }
    )
    assert unique_failure.status_code == 400
    assert "username" in unique_failure.json["errors"].keys()
    assert "email" in unique_failure.json["errors"].keys()


def test_patch_otheruser(client, app, test_users):
    """Test patching as other user"""

    with app.app_context():
        tokens = do_login(client, "usr1", "usr1")
        # Try edit other user profile
        resp = client.patch(
            "/api/v1/auth/users/2",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json={"email": "test@localhost.com"})
        print(resp.json)
        assert resp.status_code == 403
        # Now do a login as admin
        tokens = do_login(client, "admin", "admin")
        resp = client.patch(
            "/api/v1/auth/users/2",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json={"roles": ["admin"]}
        )
        assert resp.status_code == 200
        assert "admin" in resp.json["roles"]


def test_delete_user(client, app, test_users, test_admin):
    """Tests deleting of user"""

    with app.app_context():
        usr_tokens = do_login(client, "usr1", "usr1")

        # Try to delete other user.
        resp_invalid = client.delete(
            "/api/v1/auth/users/2",
            headers={"Authorization": f"Bearer {usr_tokens['access_token']}"},
        )
        assert resp_invalid.status_code == 403

        resp_valid_delete = client.delete(
            "/api/v1/auth/users/me",
            headers={"Authorization": f"Bearer {usr_tokens['access_token']}"},
        )
        assert resp_valid_delete.status_code == 200

        # Check if the user really deleted
        usr = User.find_user("usr1")
        assert usr is None

        admin_tokens = do_login(client, "admin", "admin")
        resp_valid_admin = client.delete(
            "/api/v1/auth/users/2",
            headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
        )
        assert resp_valid_admin.status_code == 200
        usr = User.query.get(2)
        assert usr is None
