from api.model.user import Role, User
from api.util.user import role_required, roles_accepted
from .conftest import do_login


def test_role_creation(app, client):
    """Tests role creation"""
    with app.app_context():
        not_found_role = Role.find("test_role")
        assert not_found_role is None
        test_role = Role.find_or_create("test_role")
        assert isinstance(test_role, Role)
        assert test_role.name == "test_role"


def test_assign_role(app, client, test_users, test_roles):
    """Testing role assignment"""
    with app.app_context():
        usr = User.find_user("usr1")
        assert isinstance(usr, User)
        usr.assign_role("admin")
        assert usr.has_role("admin")


def test_deassign_role(app, client, test_users, test_roles):
    """Testing role deassignment"""
    with app.app_context():
        usr = User.find_user("usr1")

        usr.assign_role("admin")
        usr.assign_role("user")

        assert usr.has_role("admin")
        assert usr.has_role("user")

        usr.deassign_role("admin")
        assert not usr.has_role("admin")
        assert usr.has_role("user")


def test_update_roles(app, client, test_users, test_roles):
    with app.app_context():
        usr = User.find_user("usr1")

        usr.assign_role("admin")
        usr.assign_role("user")

        # Only one role should exist for user
        usr.update_roles(["admin"])

        assert len(usr.roles) == 1
        assert not usr.has_role("user")
        assert usr.has_role("admin")


def test_decorators(app, client, test_users, test_roles):
    """Testing roles_accepted and role_required decorators"""

    with app.app_context():
        @app.route("/accepted_basic_roles")
        @roles_accepted("user", "test_role")
        def test1():
            return "OK"

        @app.route("/admin_required")
        @role_required("admin")
        def test2():
            return "OK"

        # Anonymous test
        anon_resp = client.get("/admin_required")
        assert anon_resp.status_code == 401
        anon_resp = client.get("/accepted_basic_roles")
        assert anon_resp.status_code == 401

        # Test role_required as admin
        admin_tokens = do_login(client, "admin", "admin")
        admin_resp = client.get(
            "/admin_required",
            headers={"Authorization": f"Bearer {admin_tokens['access_token']}"}
        )
        assert admin_resp.status_code == 200

        usr1_tokens = do_login(client, "usr1", "usr1")
        # Don't have role
        usr1_resp = client.get(
            "/admin_required",
            headers={"Authorization": f"Bearer {usr1_tokens['access_token']}"}
        )

        assert usr1_resp.status_code == 403

        # Has the role
        usr1_resp = client.get(
            "/accepted_basic_roles",
            headers={"Authorization": f"Bearer {usr1_tokens['access_token']}"}
        )
        assert usr1_resp.status_code == 200

        # Don't have any accepted roles
        usr2_tokens = do_login(client, "usr2", "usr2")
        usr2_resp = client.get(
            "/accepted_basic_roles",
            headers={"Authorization": f"Bearer {usr2_tokens['access_token']}"}
        )
        assert usr2_resp.status_code == 403
