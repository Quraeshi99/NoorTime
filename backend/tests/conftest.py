# backend/tests/conftest.py

import pytest
from project import create_app, db as _db
from project.models import User, Permission, RolePermission, UserPermission
from project.utils.constants import Roles
import jwt
import time
from unittest.mock import patch, MagicMock
import datetime

# Use a simple secret key for HS256 algorithm in tests
TEST_SECRET_KEY = "your-super-secret-and-long-enough-test-key-for-hs256"

@pytest.fixture(scope='session')
def app():
    """Session-wide application for testing."""
    app = create_app('testing')
    # Configure the app with the same secret key for decoding tokens during tests
    app.config['JWT_SECRET_KEY'] = TEST_SECRET_KEY
    app.config['LOCATIONIQ_API_KEY'] = 'dummy_key'
    app.config['OPENWEATHERMAP_API_KEY'] = 'dummy_key'
    return app

@pytest.fixture(scope='function')
def db(app):
    """Function-level database setup. Creates and tears down tables for each test function."""
    with app.app_context():
        _db.create_all()
        
        # Seed initial permissions
        permissions_to_add = [
            Permission(name='can_view_users', description='View list of all users'),
            Permission(name='can_manage_user_roles', description='Assign/revoke user roles'),
            Permission(name='can_manage_user_permissions', description='Assign/revoke individual user permissions'),
            Permission(name='can_delete_users', description='Delete user accounts'),
            Permission(name='can_view_popups', description='View list of popups'),
            Permission(name='can_create_popups', description='Create new popups'),
            Permission(name='can_update_popups', description='Update existing popups'),
            Permission(name='can_delete_popups', description='Delete popups'),
            Permission(name='can_view_app_settings', description='View global app settings'),
            Permission(name='can_manage_app_settings', description='Manage global app settings'),
            Permission(name='can_send_notifications', description='Send push notifications'),
            Permission(name='can_update_own_settings', description='Update own user settings'),
            Permission(name='can_view_revenue', description='View application revenue'),
            Permission(name='can_view_analytics', description='View application analytics'),
            Permission(name='can_manage_subscriptions', description='Manage user subscriptions'),
            Permission(name='can_process_payments', description='Process payments'),
        ]
        _db.session.add_all(permissions_to_add)
        _db.session.commit()

        # Seed default role permissions
        perms = {p.name: p.id for p in Permission.query.all()}
        role_perms_to_add = []
        client_perms = ['can_update_own_settings']
        for p_name in client_perms:
            role_perms_to_add.append(RolePermission(role_name=Roles.CLIENT, permission_id=perms[p_name]))
        manager_perms = ['can_view_users', 'can_view_popups', 'can_create_popups', 'can_update_popups', 'can_view_revenue', 'can_view_analytics']
        for p_name in manager_perms:
            role_perms_to_add.append(RolePermission(role_name=Roles.MANAGER, permission_id=perms[p_name]))
        super_admin_perms = [p.name for p in permissions_to_add] # All permissions
        for p_name in super_admin_perms:
            role_perms_to_add.append(RolePermission(role_name=Roles.SUPER_ADMIN, permission_id=perms[p_name]))
        _db.session.add_all(role_perms_to_add)
        _db.session.commit()

        yield _db

        _db.session.remove()
        _db.drop_all()

@pytest.fixture(scope='function')
def test_client(app, db):
    """A test client for the app, ensuring the DB is initialized."""
    return app.test_client()


@pytest.fixture(autouse=True)
def mock_auth_dependencies(mocker):
    """
    Mocks authentication-related external calls and JWT decoding.
    This applies to all tests automatically.
    """
    # Mock get_jwks_client to prevent network calls and provide a dummy signing key
    mock_jwks_client_instance = MagicMock()
    mock_signing_key = MagicMock()
    mock_signing_key.key = TEST_SECRET_KEY # The key attribute is what jwt.decode expects
    mock_jwks_client_instance.get_signing_key_from_jwt.return_value = mock_signing_key
    mocker.patch('project.utils.auth.get_jwks_client', return_value=mock_jwks_client_instance)

    # Mock jwt.decode to bypass external validation and use HS256
    original_jwt_decode = jwt.decode
    def mock_decode_logic(token, key, algorithms, audience=None, issuer=None):
        # In our tests, we bypass the key/issuer check but still validate audience.
        return original_jwt_decode(token, TEST_SECRET_KEY, algorithms=["HS256"], audience=audience)
    
    mocker.patch('jwt.decode', side_effect=mock_decode_logic)


@pytest.fixture(autouse=True)
def mock_api_prayer_times_service(mocker):
    """Mocks the get_api_prayer_times_for_date_from_service function."""
    mock_data = {
        "Fajr": "05:00", "Sunrise": "06:30", "Dhuhr": "13:00",
        "Asr": "17:00", "Sunset": "18:30", "Maghrib": "18:45",
        "Isha": "20:00", "Imsak": "04:50", "gregorian_date": "10-08-2025",
        "gregorian_weekday": "Sunday", "hijri_date": "06-02-1447",
        "hijri_month_en": "Rajab", "hijri_year": "1447",
        "temperatureC": "25", "weather_description": "Clear Sky"
    }
    mocker.patch('project.services.prayer_time_service.get_api_prayer_times_for_date_from_service', return_value=mock_data)





def create_test_token(user_id, supabase_role, email):
    """Helper to create a JWT using HS256."""
    payload = {
        'sub': user_id,
        'role': supabase_role,
        'email': email,
        'aud': 'authenticated',
        'exp': int(time.time()) + 3600,
        'iat': int(time.time())
    }
    token = jwt.encode(payload, TEST_SECRET_KEY, algorithm="HS256")
    return {'Authorization': f'Bearer {token}'}

@pytest.fixture(scope='function')
def client_user_in_db(db):
    """Creates a Client user in the database and returns their object."""
    user = User(supabase_user_id='client-user-id', email='client@example.com', role=Roles.CLIENT)
    _db.session.add(user)
    _db.session.commit()
    return user

@pytest.fixture(scope='function')
def manager_user_in_db(db):
    """Creates a Manager user in the database and returns their object."""
    user = User(supabase_user_id='manager-user-id', email='manager@example.com', role=Roles.MANAGER)
    _db.session.add(user)
    _db.session.commit()
    return user

@pytest.fixture(scope='function')
def super_admin_user_in_db(db):
    """Creates a Super Admin user in the database and returns their object."""
    user = User(supabase_user_id='super-admin-id', email='superadmin@example.com', role=Roles.SUPER_ADMIN)
    _db.session.add(user)
    _db.session.commit()
    return user

@pytest.fixture(scope='function')
def auth_headers_for_client(client_user_in_db):
    """Auth headers for a regular Client."""
    return create_test_token(client_user_in_db.supabase_user_id, 'authenticated', client_user_in_db.email)

@pytest.fixture(scope='function')
def auth_headers_for_manager(manager_user_in_db):
    """Auth headers for a Manager."""
    return create_test_token(manager_user_in_db.supabase_user_id, 'authenticated', manager_user_in_db.email)

@pytest.fixture(scope='function')
def auth_headers_for_super_admin(super_admin_user_in_db):
    """Auth headers for a Super Admin."""
    return create_test_token(super_admin_user_in_db.supabase_user_id, 'service_role', super_admin_user_in_db.email)
