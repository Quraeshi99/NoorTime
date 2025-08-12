# backend/tests/test_management_routes.py

import json
import pytest
from project.models import User, Permission, RolePermission, UserPermission
from project.utils.constants import Roles

# --- Unauthenticated Tests ---

def test_get_users_unauthenticated(test_client, init_database):
    response = test_client.get('/api/management/users')
    assert response.status_code == 401

# --- Permission Tests for Different Roles ---

@pytest.fixture(scope='function')
def setup_users_and_permissions(init_database, client_user_in_db, manager_user_in_db, super_admin_user_in_db):
    """
    Ensures users are in DB and returns them.
    Permissions are handled by module-scoped fixtures.
    """
    return client_user_in_db, manager_user_in_db, super_admin_user_in_db

# --- Test can_view_users permission ---

def test_get_users_as_client_without_permission(test_client, setup_users_and_permissions, auth_headers_for_client, mock_jwks_client):
    """
    Client should not be able to view users by default.
    """
    # Client role does not have 'can_view_users' by default
    response = test_client.get('/api/management/users', headers=auth_headers_for_client)
    assert response.status_code == 403
    assert json.loads(response.data.decode('utf-8'))['error'] == "Permission 'can_view_users' required."

def test_get_users_as_manager_with_permission(test_client, setup_users_and_permissions, auth_headers_for_manager, mock_jwks_client):
    """
    Manager should be able to view users by default.
    """
    response = test_client.get('/api/management/users', headers=auth_headers_for_manager)
    assert response.status_code == 200
    assert len(json.loads(response.data.decode('utf-8'))) == 3

def test_get_users_as_super_admin_with_permission(test_client, setup_users_and_permissions, auth_headers_for_super_admin, mock_jwks_client):
    """
    Super Admin should be able to view users by default.
    """
    response = test_client.get('/api/management/users', headers=auth_headers_for_super_admin)
    assert response.status_code == 200
    assert len(json.loads(response.data.decode('utf-8'))) == 3

# --- Test can_manage_user_roles permission ---

def test_assign_role_as_manager_without_permission(test_client, setup_users_and_permissions, auth_headers_for_manager, mock_jwks_client):
    """
    Manager should not be able to assign roles by default.
    """
    client_user, _, _ = setup_users_and_permissions
    response = test_client.post(f'/api/management/users/{client_user.id}/assign-role', 
                                headers=auth_headers_for_manager, 
                                json={"role": Roles.MANAGER})
    assert response.status_code == 403
    assert json.loads(response.data.decode('utf-8'))['error'] == "Permission 'can_manage_user_roles' required."

def test_assign_role_as_super_admin_with_permission(test_client, setup_users_and_permissions, auth_headers_for_super_admin, mock_jwks_client):
    """
    Super Admin should be able to assign roles by default.
    """
    client_user, _, _ = setup_users_and_permissions
    assert client_user.role == Roles.CLIENT # Pre-condition

    response = test_client.post(f'/api/management/users/{client_user.id}/assign-role', 
                                headers=auth_headers_for_super_admin, 
                                json={"role": Roles.MANAGER})
    assert response.status_code == 200

    # Verify the change in the database
    updated_user = User.query.get(client_user.id)
    assert updated_user.role == Roles.MANAGER

# --- Test can_manage_user_permissions permission ---

def test_get_user_permissions_as_super_admin(test_client, setup_users_and_permissions, auth_headers_for_super_admin, mock_jwks_client):
    """
    Super Admin should be able to view user permissions.
    """
    client_user, _, _ = setup_users_and_permissions
    response = test_client.get(f'/api/management/users/{client_user.id}/permissions', headers=auth_headers_for_super_admin)
    assert response.status_code == 200
    data = json.loads(response.data.decode('utf-8'))
    assert "explicit_permissions" in data
    assert "all_available_permissions" in data

def test_assign_user_permissions_as_super_admin(test_client, setup_users_and_permissions, auth_headers_for_super_admin, mock_jwks_client):
    """
    Super Admin should be able to assign individual user permissions.
    """
    client_user, _, _ = setup_users_and_permissions
    assign_data = [
        {"name": "can_view_users", "has_permission": True},
        {"name": "can_create_popups", "has_permission": True},
    ]
    response = test_client.post(f'/api/management/users/{client_user.id}/permissions', headers=auth_headers_for_super_admin, json=assign_data)
    assert response.status_code == 200

    # Verify in DB
    user_perms = UserPermission.query.filter_by(user_id=client_user.id).all()
    assert len(user_perms) == 2
    perm_names = {Permission.query.get(p.permission_id).name for p in user_perms}
    assert "can_view_users" in perm_names
    assert "can_create_popups" in perm_names

# --- Test Popup Management permissions ---

def test_create_popup_as_manager(test_client, setup_users_and_permissions, auth_headers_for_manager, mock_jwks_client):
    """
    Manager should be able to create popups by default.
    """
    popup_data = {"name": "Manager Popup", "content": "Created by manager"}
    response = test_client.post('/api/management/popups', headers=auth_headers_for_manager, json=popup_data)
    assert response.status_code == 201

def test_delete_popup_as_manager_without_permission(test_client, setup_users_and_permissions, auth_headers_for_manager, mock_jwks_client):
    """
    Manager should not be able to delete popups by default.
    """
    # Create a popup first
    popup_data = {"name": "Temp Popup", "content": "To be deleted"}
    create_response = test_client.post('/api/management/popups', headers=auth_headers_for_manager, json=popup_data)
    popup_id = json.loads(create_response.data.decode('utf-8'))['id']

    response = test_client.delete(f'/api/management/popups/{popup_id}', headers=auth_headers_for_manager)
    assert response.status_code == 403
    assert json.loads(response.data.decode('utf-8'))['error'] == "Permission 'can_delete_popups' required."

def test_delete_popup_as_super_admin_with_permission(test_client, setup_users_and_permissions, auth_headers_for_super_admin, mock_jwks_client):
    """
    Super Admin should be able to delete popups by default.
    """
    # Create a popup first
    popup_data = {"name": "Admin Delete Popup", "content": "To be deleted by admin"}
    create_response = test_client.post('/api/management/popups', headers=auth_headers_for_super_admin, json=popup_data)
    popup_id = json.loads(create_response.data.decode('utf-8'))['id']

    response = test_client.delete(f'/api/management/popups/{popup_id}', headers=auth_headers_for_super_admin)
    assert response.status_code == 200

# --- Test Role Permission Management APIs ---

def test_get_all_permissions_as_super_admin(test_client, setup_users_and_permissions, auth_headers_for_super_admin, mock_jwks_client):
    """
    Super Admin should be able to get all permissions.
    """
    response = test_client.get('/api/management/permissions', headers=auth_headers_for_super_admin)
    assert response.status_code == 200
    data = json.loads(response.data.decode('utf-8'))
    assert len(data) > 0 # Should return a list of permissions
    assert "can_view_users" in [p['name'] for p in data]

def test_assign_role_permissions_as_super_admin(test_client, setup_users_and_permissions, auth_headers_for_super_admin, mock_jwks_client):
    """
    Super Admin should be able to assign permissions to roles.
    """
    # Assign new permissions to Client role
    new_client_perms = ["can_view_users", "can_create_popups"]
    response = test_client.post('/api/management/roles/Client/permissions', headers=auth_headers_for_super_admin, json=new_client_perms)
    assert response.status_code == 200

    # Verify by fetching role permissions
    get_response = test_client.get('/api/management/roles/Client/permissions', headers=auth_headers_for_super_admin)
    assert get_response.status_code == 200
    data = json.loads(get_response.data.decode('utf-8'))
    assigned_perms = [p['name'] for p in data]
    assert "can_view_users" in assigned_perms
    assert "can_create_popups" in assigned_perms
    assert len(assigned_perms) == 2

# --- Test Super Admin self-demotion prevention ---

def test_super_admin_cannot_demote_self(test_client, super_admin_user_in_db, auth_headers_for_super_admin, mock_jwks_client):
    """
    Super Admin should not be able to demote themselves.
    """
    response = test_client.post(f'/api/management/users/{super_admin_user_in_db.id}/assign-role', 
                                headers=auth_headers_for_super_admin, 
                                json={"role": Roles.MANAGER})
    assert response.status_code == 400
    assert json.loads(response.data.decode('utf-8'))['error'] == "Super Admin cannot demote themselves."