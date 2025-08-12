# backend/project/routes/management_routes.py

from flask import Blueprint, jsonify, request, current_app, g
from .. import db
from ..models import User, UserSettings, AppSettings, Popup, Permission, RolePermission, UserPermission
from ..utils.auth import has_permission # Import the new permission decorator
from ..utils.constants import Roles
from ..services.notification_service import notification_service

# Renamed from admin_bp to management_bp to reflect its broader purpose
management_bp = Blueprint('management', __name__)

# --- Helper for Permission Management ---

def _get_permission_object(permission_name):
    perm = Permission.query.filter_by(name=permission_name).first()
    if not perm:
        # Create permission if it doesn't exist (useful for new features)
        perm = Permission(name=permission_name, description=f"Permission to {permission_name.replace('_', ' ')}")
        db.session.add(perm)
        db.session.commit()
        current_app.logger.info(f"Created new permission: {permission_name}")
    return perm

# --- User & Role Management ---

@management_bp.route('/users', methods=['GET'])
@has_permission('can_view_users') # Now checks for specific permission
def get_all_users():
    """Retrieves a list of all users (Clients, Managers, etc.)."""
    users = User.query.all()
    users_data = []
    for user in users:
        users_data.append({
            "id": user.id,
            "supabase_user_id": user.supabase_user_id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "default_city_name": user.default_city_name,
        })
    return jsonify(users_data)

@management_bp.route('/users/<int:user_id>/assign-role', methods=['POST'])
@has_permission('can_manage_user_roles') # Only users with this permission can assign roles
def assign_role(user_id):
    """Assigns a new role to a user."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()
    new_role = data.get('role')

    valid_roles = [Roles.SUPER_ADMIN, Roles.MANAGER, Roles.CLIENT]
    if not new_role or new_role not in valid_roles:
        return jsonify({"error": f"Invalid role. Must be one of {valid_roles}"}), 400

    # Prevent self-demotion from Super Admin
    if g.user.id == user.id and g.user.role == Roles.SUPER_ADMIN and new_role != Roles.SUPER_ADMIN:
        return jsonify({"error": "Super Admin cannot demote themselves."}), 400

    user.role = new_role
    try:
        db.session.commit()
        current_app.logger.info(f"User {user.email} (ID: {user.id}) role changed to {new_role} by {g.user.email}")
        return jsonify({"message": f"User role successfully updated to {new_role}"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error assigning role: {e}", exc_info=True)
        return jsonify({"error": "Failed to assign role due to a server error."}), 500

@management_bp.route('/users/<int:user_id>/permissions', methods=['GET'])
@has_permission('can_manage_user_permissions') # Only users with this permission can view/manage user permissions
def get_user_permissions(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Get all available permissions
    all_permissions = Permission.query.all()
    all_permissions_names = {p.name: p.id for p in all_permissions}

    # Get user's current active permissions (role-based + overrides)
    user_active_permissions = g.user_permissions # This is the caller's permissions, not the target user's
    # We need to load the target user's permissions
    target_user_permissions = g.user_permissions # Placeholder, needs actual loading logic
    # For now, let's just return the user's explicit overrides
    explicit_overrides = UserPermission.query.filter_by(user_id=user_id).all()
    explicit_perms_status = {Permission.query.get(up.permission_id).name: up.has_permission for up in explicit_overrides}

    return jsonify({
        "user_id": user.id,
        "user_email": user.email,
        "role": user.role,
        "explicit_permissions": explicit_perms_status,
        "all_available_permissions": list(all_permissions_names.keys())
    })

@management_bp.route('/users/<int:user_id>/permissions', methods=['POST'])
@has_permission('can_manage_user_permissions') # Only users with this permission can assign/revoke user permissions
def assign_user_permissions(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    data = request.get_json()
    if not data or not isinstance(data, list):
        return jsonify({"error": "Invalid data format. Expected a list of permission objects."}), 400

    # Clear existing user-specific overrides for simplicity, then re-add
    UserPermission.query.filter_by(user_id=user_id).delete()
    db.session.flush() # Ensure delete is processed before adding new ones

    for perm_data in data:
        perm_name = perm_data.get('name')
        has_permission_status = perm_data.get('has_permission', True)

        permission_obj = Permission.query.filter_by(name=perm_name).first()
        if not permission_obj:
            # Create permission if it doesn't exist
            permission_obj = Permission(name=perm_name, description=f"Permission to {perm_name.replace('_', ' ')}")
            db.session.add(permission_obj)
            db.session.flush() # Get ID for new permission

        user_perm = UserPermission(user_id=user.id, permission_id=permission_obj.id, has_permission=has_permission_status)
        db.session.add(user_perm)
    
    try:
        db.session.commit()
        return jsonify({"message": "User permissions updated successfully."}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating user permissions for {user_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to update user permissions."}), 500

# --- App Settings Management ---

@management_bp.route('/app-settings', methods=['GET'])
@has_permission('can_view_app_settings')
def get_app_settings():
    settings = AppSettings.query.first()
    if not settings:
        settings = AppSettings()
        db.session.add(settings)
        db.session.commit()
    return jsonify({
        "welcome_message": settings.welcome_message,
        "is_new_feature_enabled": settings.is_new_feature_enabled
    })

@management_bp.route('/app-settings', methods=['PATCH'])
@has_permission('can_manage_app_settings')
def update_app_settings():
    settings = AppSettings.query.first()
    if not settings:
        settings = AppSettings()
        db.session.add(settings)
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    for key, value in data.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    db.session.commit()
    return jsonify({"message": "App settings updated successfully."})

# --- Popup Management ---

@management_bp.route('/popups', methods=['GET'])
@has_permission('can_view_popups')
def get_popups():
    popups = Popup.query.order_by(Popup.display_order).all()
    return jsonify([{"id": p.id, "name": p.name, "content": p.content, "is_active": p.is_active} for p in popups])

@management_bp.route('/popups', methods=['POST'])
@has_permission('can_create_popups')
def create_popup():
    data = request.get_json()
    if not data or not data.get('name') or not data.get('content'):
        return jsonify({"error": "Name and content are required"}), 400
    
    new_popup = Popup(name=data['name'], content=data['content'], is_active=data.get('is_active', True))
    db.session.add(new_popup)
    db.session.commit()
    return jsonify({"message": "Popup created successfully", "id": new_popup.id}), 201

@management_bp.route('/popups/<int:popup_id>', methods=['PATCH'])
@has_permission('can_update_popups')
def update_popup(popup_id):
    popup = Popup.query.get_or_404(popup_id)
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    for key, value in data.items():
        if hasattr(popup, key):
            setattr(popup, key, value)
    db.session.commit()
    return jsonify({"message": "Popup updated successfully."})

@management_bp.route('/popups/<int:popup_id>', methods=['DELETE'])
@has_permission('can_delete_popups')
def delete_popup(popup_id):
    popup = Popup.query.get_or_404(popup_id)
    db.session.delete(popup)
    db.session.commit()
    return jsonify({"message": "Popup deleted successfully."})

# --- Push Notification ---

@management_bp.route('/notifications/send', methods=['POST'])
@has_permission('can_send_notifications')
def send_notification():
    data = request.get_json()
    if not data or not data.get('message'):
        return jsonify({"error": "Message is required"}), 400
    
    result = notification_service.send_push_notification(
        message=data.get('message'),
        recipient_type=data.get('recipient_type', 'all'),
        recipient_value=data.get('recipient_value')
    )
    return jsonify(result)

# --- Permission Management APIs (Super Admin Only) ---

@management_bp.route('/permissions', methods=['GET'])
@has_permission('can_manage_user_permissions') # This permission itself is needed to view permissions
def get_all_permissions():
    """Lists all available permissions in the system."""
    permissions = Permission.query.all()
    return jsonify([{"name": p.name, "description": p.description} for p in permissions])

@management_bp.route('/roles/<string:role_name>/permissions', methods=['GET'])
@has_permission('can_manage_user_permissions')
def get_role_permissions(role_name):
    """Gets all permissions assigned to a specific role."""
    if role_name not in [Roles.SUPER_ADMIN, Roles.MANAGER, Roles.CLIENT]:
        return jsonify({"error": "Invalid role name."}), 400
    
    role_perms = db.session.query(Permission.name, Permission.description).join(RolePermission).filter(RolePermission.role_name == role_name).all()
    return jsonify([{"name": p.name, "description": p.description} for p in role_perms])

@management_bp.route('/roles/<string:role_name>/permissions', methods=['POST'])
@has_permission('can_manage_user_permissions')
def assign_role_permissions(role_name):
    """Assigns a list of permissions to a specific role. Overwrites existing role permissions."""
    if role_name not in [Roles.SUPER_ADMIN, Roles.MANAGER, Roles.CLIENT]:
        return jsonify({"error": "Invalid role name."}), 400
    
    data = request.get_json()
    if not data or not isinstance(data, list):
        return jsonify({"error": "Invalid data format. Expected a list of permission names."}), 400

    # Clear existing role permissions
    RolePermission.query.filter_by(role_name=role_name).delete()
    db.session.flush()

    for perm_name in data:
        permission_obj = Permission.query.filter_by(name=perm_name).first()
        if not permission_obj:
            # Create permission if it doesn't exist
            permission_obj = Permission(name=perm_name, description=f"Permission to {perm_name.replace('_', ' ')}")
            db.session.add(permission_obj)
            db.session.flush()
        
        role_perm = RolePermission(role_name=role_name, permission_id=permission_obj.id)
        db.session.add(role_perm)
    
    try:
        db.session.commit()
        return jsonify({"message": f"Permissions for role {role_name} updated successfully."}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating role permissions for {role_name}: {e}", exc_info=True)
        return jsonify({"error": "Failed to update role permissions."}), 500
