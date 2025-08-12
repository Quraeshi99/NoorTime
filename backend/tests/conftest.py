# backend/tests/conftest.py

import pytest
from project import create_app, db
from project.models import User, Permission, RolePermission # Import new models
from project.utils.constants import Roles # Import role constants
import jwt
import time
from unittest.mock import MagicMock

# Dummy RSA key pair for testing. In a real-world scenario, never commit private keys.
TEST_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQDL+08eI3dSAH4t
... (dummy private key) ...
-----END PRIVATE KEY-----"""

TEST_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAy/tPHiN3UgB+LQ
... (dummy public key) ...
-----END PUBLIC KEY-----"""

@pytest.fixture(scope='session')
def app_instance():
    return create_app('testing')

@pytest.fixture(scope='module')
def test_app(app_instance):
    with app_instance.app_context():
        yield app_instance

@pytest.fixture(scope='module')
def test_client(test_app):
    return test_app.test_client()

@pytest.fixture(scope='module')
def init_database(test_app, initial_permissions, default_role_permissions):
    """
    Initializes the test database for a module.
    Ensures all tables are created and default permissions are loaded.
    """
    with test_app.app_context():
        db.create_all()
        # Permissions are loaded by initial_permissions fixture
        # Role permissions are loaded by default_role_permissions fixture
        yield db
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope='function')
def mock_jwks_client(monkeypatch):
    """Mocks the JWKS client to prevent real HTTP requests during tests."""
    mock_client = MagicMock()
    signing_key = jwt.jwk.construct(TEST_PUBLIC_KEY, "RS256")
    mock_client.get_signing_key_from_jwt.return_value = signing_key
    monkeypatch.setattr('project.utils.auth.get_jwks_client', lambda: mock_client)

def create_test_token(user_id, supabase_role, email):
    """
    Helper to create a JWT. The 'role' in the token payload represents the
    Supabase role, which our app then maps to an internal role.
    """
    payload = {
        'sub': user_id,
        'role': supabase_role, # This is the role from Supabase JWT
        'email': email,
        'aud': 'authenticated',
        'exp': int(time.time()) + 3600,
        'iat': int(time.time())
    }
    token = jwt.encode(payload, TEST_PRIVATE_KEY, algorithm="RS256")
    return {'Authorization': f'Bearer {token}'}

@pytest.fixture(scope='module')
def initial_permissions(test_app):
    """
    Inserts all predefined permissions into the database.
    """
    with test_app.app_context():
        permissions_to_add = [
            # User Management
            Permission(name='can_view_users', description='View list of all users'),
            Permission(name='can_manage_user_roles', description='Assign/revoke user roles'),
            Permission(name='can_manage_user_permissions', description='Assign/revoke individual user permissions'),
            Permission(name='can_delete_users', description='Delete user accounts'),
            # Popup Management
            Permission(name='can_view_popups', description='View list of popups'),
            Permission(name='can_create_popups', description='Create new popups'),
            Permission(name='can_update_popups', description='Update existing popups'),
            Permission(name='can_delete_popups', description='Delete popups'),
            # App Settings
            Permission(name='can_view_app_settings', description='View global app settings'),
            Permission(name='can_manage_app_settings', description='Manage global app settings'),
            # Notifications
            Permission(name='can_send_notifications', description='Send push notifications'),
            # Client-specific
            Permission(name='can_update_own_settings', description='Update own user settings'),
            # Future Features (Placeholders)
            Permission(name='can_view_revenue', description='View application revenue'),
            Permission(name='can_view_analytics', description='View application analytics'),
            Permission(name='can_manage_subscriptions', description='Manage user subscriptions'),
            Permission(name='can_process_payments', description='Process payments'),
        ]
        db.session.add_all(permissions_to_add)
        db.session.commit()
        return permissions_to_add

@pytest.fixture(scope='module')
def default_role_permissions(test_app, initial_permissions):
    """
    Inserts default permissions for each role into the database.
    """
    with test_app.app_context():
        # Fetch permission IDs
        perms = {p.name: p.id for p in Permission.query.all()}

        role_perms_to_add = []

        # Client Role Permissions
        client_perms = [
            'can_update_own_settings',
        ]
        for p_name in client_perms:
            role_perms_to_add.append(RolePermission(role_name=Roles.CLIENT, permission_id=perms[p_name]))

        # Manager Role Permissions
        manager_perms = [
            'can_view_users',
            'can_view_popups',
            'can_create_popups',
            'can_update_popups',
            'can_view_revenue',
            'can_view_analytics',
        ]
        for p_name in manager_perms:
            role_perms_to_add.append(RolePermission(role_name=Roles.MANAGER, permission_id=perms[p_name]))

        # Super Admin Role Permissions (all permissions)
        super_admin_perms = [p.name for p in initial_permissions] # All permissions
        for p_name in super_admin_perms:
            role_perms_to_add.append(RolePermission(role_name=Roles.SUPER_ADMIN, permission_id=perms[p_name]))
        
        db.session.add_all(role_perms_to_add)
        db.session.commit()
        return role_perms_to_add

@pytest.fixture(scope='function')
def client_user_in_db(init_database):
    """
    Creates a Client user in the database and returns their object.
    This user will have default Client role permissions.
    """
    user = User(supabase_user_id='client-user-id', email='client@example.com', role=Roles.CLIENT)
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture(scope='function')
def manager_user_in_db(init_database):
    """
    Creates a Manager user in the database and returns their object.
    This user will have default Manager role permissions.
    """
    user = User(supabase_user_id='manager-user-id', email='manager@example.com', role=Roles.MANAGER)
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture(scope='function')
def super_admin_user_in_db(init_database):
    """
    Creates a Super Admin user in the database and returns their object.
    This user will have default Super Admin role permissions.
    """
    user = User(supabase_user_id='super-admin-id', email='superadmin@example.com', role=Roles.SUPER_ADMIN)
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture(scope='function')
def auth_headers_for_client(client_user_in_db):
    """Auth headers for a regular Client."""
    return create_test_token(client_user_in_db.supabase_user_id, 'authenticated', client_user_in_db.email)

@pytest.fixture(scope='function')
def auth_headers_for_manager(manager_user_in_db):
    """
    Auth headers for a Manager.
    Note: Supabase role is 'authenticated', but our backend maps it to 'Manager' based on DB.
    """
    return create_test_token(manager_user_in_db.supabase_user_id, 'authenticated', manager_user_in_db.email)

@pytest.fixture(scope='function')
def auth_headers_for_super_admin(super_admin_user_in_db):
    """
    Auth headers for a Super Admin, using the 'service_role' from Supabase.
    """
    return create_test_token(super_admin_user_in_db.supabase_user_id, 'service_role', super_admin_user_in_db.email)