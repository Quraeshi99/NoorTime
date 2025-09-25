# backend/project/routes/management_routes.py

from flask import jsonify, request, current_app, g
from flask_smorest import Blueprint, abort
from webargs import fields
from webargs.flaskparser import use_args

from .. import db
from ..models import User, UserSettings, AppSettings, Popup, Permission, RolePermission, UserPermission
from ..utils.auth import has_permission # Import the new permission decorator
from ..utils.constants import Roles
# from ..services.notification_service import notification_service
from ..schemas import MessageSchema # Assuming MessageSchema for success/error messages

# Renamed from admin_bp to management_bp to reflect its broader purpose
management_bp = Blueprint('Management', __name__, url_prefix='/api/management')

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
@management_bp.response(200, MessageSchema)
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
    return users_data # Return dict for Smorest

@management_bp.route('/users/<int:user_id>/assign-role', methods=['POST'])
@has_permission('can_manage_user_roles') # Only users with this permission can assign roles
@use_args({'role': fields.String(required=True)}, location='json')
@management_bp.response(200, MessageSchema)
@management_bp.response(400, MessageSchema)
@management_bp.response(404, MessageSchema)
@management_bp.response(500, MessageSchema)
def assign_role(args, user_id):
    """Assigns a new role to a user."""
    user = User.query.get(user_id)
    if not user:
        abort(404, message="User not found")

    new_role = args.get('role')

    valid_roles = [Roles.SUPER_ADMIN, Roles.MANAGER, Roles.CLIENT]
    if not new_role or new_role not in valid_roles:
        abort(400, message=f"Invalid role. Must be one of {valid_roles}")

    # Prevent self-demotion from Super Admin
    if g.user.id == user.id and g.user.role == Roles.SUPER_ADMIN and new_role != Roles.SUPER_ADMIN:
        abort(400, message="Super Admin cannot demote themselves.")

    user.role = new_role
    try:
        db.session.commit()
        current_app.logger.info(f"User {user.email} (ID: {user.id}) role changed to {new_role} by {g.user.email}")
        return {"message": f"User role successfully updated to {new_role}"} # Return dict for Smorest
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error assigning role: {e}", exc_info=True)
        abort(500, message="Failed to assign role due to a server error.")

@management_bp.route('/users/<int:user_id>/permissions', methods=['GET'])
@has_permission('can_manage_user_permissions') # Only users with this permission can view/manage user permissions
@management_bp.response(200, MessageSchema)
@management_bp.response(404, MessageSchema)
def get_user_permissions(user_id):
    user = User.query.get(user_id)
    if not user:
        abort(404, message="User not found")
    
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

    return {
        "user_id": user.id,
        "user_email": user.email,
        "role": user.role,
        "explicit_permissions": explicit_perms_status,
        "all_available_permissions": list(all_permissions_names.keys())
    } # Return dict for Smorest

@management_bp.route('/users/<int:user_id>/permissions', methods=['POST'])
@has_permission('can_manage_user_permissions') # Only users with this permission can assign/revoke user permissions
@use_args({'permissions': fields.List(fields.Dict(), required=True)}, location='json')
@management_bp.response(200, MessageSchema)
@management_bp.response(400, MessageSchema)
@management_bp.response(404, MessageSchema)
@management_bp.response(500, MessageSchema)
def assign_user_permissions(args, user_id):
    user = User.query.get(user_id)
    if not user:
        abort(404, message="User not found")
    
    data = args.get('permissions')
    if not data or not isinstance(data, list):
        abort(400, message="Invalid data format. Expected a list of permission objects.")

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
        return {"message": "User permissions updated successfully."} # Return dict for Smorest
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating user permissions for {user_id}: {e}", exc_info=True)
        abort(500, message="Failed to update user permissions.")

# --- App Settings Management ---

@management_bp.route('/app-settings', methods=['GET'])
@has_permission('can_view_app_settings')
@management_bp.response(200, MessageSchema)
def get_app_settings():
    settings = AppSettings.query.first()
    if not settings:
        settings = AppSettings()
        db.session.add(settings)
        db.session.commit()
    return {
        "welcome_message": settings.welcome_message,
        "is_new_feature_enabled": settings.is_new_feature_enabled
    } # Return dict for Smorest

@management_bp.route('/app-settings', methods=['PATCH'])
@has_permission('can_manage_app_settings')
@use_args({'welcome_message': fields.String(),'is_new_feature_enabled': fields.Boolean()}, location='json')
@management_bp.response(200, MessageSchema)
@management_bp.response(400, MessageSchema)
@management_bp.response(500, MessageSchema)
def update_app_settings(args):
    settings = AppSettings.query.first()
    if not settings:
        settings = AppSettings()
        db.session.add(settings)
    data = args # Use args from webargs
    if not data:
        abort(400, message="No data provided")
    
    for key, value in data.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    db.session.commit()
    return {"message": "App settings updated successfully."} # Return dict for Smorest

# --- Popup Management ---

@management_bp.route('/popups', methods=['GET'])
@has_permission('can_view_popups')
@management_bp.response(200, MessageSchema)
def get_popups():
    popups = Popup.query.order_by(Popup.display_order).all()
    return [{
        "id": p.id,
        "name": p.name,
        "content": p.content,
        "is_active": p.is_active
    } for p in popups] # Return list of dicts for Smorest

@management_bp.route('/popups', methods=['POST'])
@has_permission('can_create_popups')
@use_args({'name': fields.String(required=True),'content': fields.String(required=True),'is_active': fields.Boolean()}, location='json')
@management_bp.response(201, MessageSchema)
@management_bp.response(400, MessageSchema)
def create_popup(args):
    data = args # Use args from webargs
    if not data or not data.get('name') or not data.get('content'):
        abort(400, message="Name and content are required")
    
    new_popup = Popup(name=data['name'], content=data['content'], is_active=data.get('is_active', True))
    db.session.add(new_popup)
    db.session.commit()
    return {"message": "Popup created successfully", "id": new_popup.id} # Return dict for Smorest

@management_bp.route('/popups/<int:popup_id>', methods=['PATCH'])
@has_permission('can_update_popups')
@use_args({'name': fields.String(),'content': fields.String(),'is_active': fields.Boolean()}, location='json')
@management_bp.response(200, MessageSchema)
@management_bp.response(400, MessageSchema)
@management_bp.response(404, MessageSchema)
def update_popup(args, popup_id):
    popup = Popup.query.get_or_404(popup_id)
    data = args # Use args from webargs
    if not data:
        abort(400, message="No data provided")
    for key, value in data.items():
        if hasattr(popup, key):
            setattr(popup, key, value)
    db.session.commit()
    return {"message": "Popup updated successfully."} # Return dict for Smorest

@management_bp.route('/popups/<int:popup_id>', methods=['DELETE'])
@has_permission('can_delete_popups')
@management_bp.response(200, MessageSchema)
@management_bp.response(404, MessageSchema)
def delete_popup(popup_id):
    popup = Popup.query.get_or_404(popup_id)
    db.session.delete(popup)
    db.session.commit()
    return {"message": "Popup deleted successfully."} # Return dict for Smorest

# --- Push Notification ---

@management_bp.route('/notifications/send', methods=['POST'])
@has_permission('can_send_notifications')
@use_args({'message': fields.String(required=True),'recipient_type': fields.String(),'recipient_value': fields.String()}, location='json')
@management_bp.response(200, MessageSchema)
@management_bp.response(400, MessageSchema)
def send_notification(args):
    data = args # Use args from webargs
    if not data or not data.get('message'):
        abort(400, message="Message is required")
    
    # result = notification_service.send_push_notification(
    #     message=data.get('message'),
    #     recipient_type=data.get('recipient_type', 'all'),
    #     recipient_value=data.get('recipient_value')
    # )
    # return result # Return dict for Smorest
    return {"message": "Notification sending is currently disabled."}

# --- Permission Management APIs (Super Admin Only) ---

@management_bp.route('/permissions', methods=['GET'])
@has_permission('can_manage_user_permissions') # This permission itself is needed to view permissions
@management_bp.response(200, MessageSchema)
def get_all_permissions():
    """Lists all available permissions in the system."""
    permissions = Permission.query.all()
    return [{"name": p.name, "description": p.description} for p in permissions] # Return list of dicts for Smorest

@management_bp.route('/roles/<string:role_name>/permissions', methods=['GET'])
@has_permission('can_manage_user_permissions')
@management_bp.response(200, MessageSchema)
@management_bp.response(400, MessageSchema)
def get_role_permissions(role_name):
    """Gets all permissions assigned to a specific role."""
    if role_name not in [Roles.SUPER_ADMIN, Roles.MANAGER, Roles.CLIENT]:
        abort(400, message="Invalid role name.")
    
    role_perms = db.session.query(Permission.name, Permission.description).join(RolePermission).filter(RolePermission.role_name == role_name).all()
    return [{"name": p.name, "description": p.description} for p in role_perms] # Return list of dicts for Smorest

@management_bp.route('/roles/<string:role_name>/permissions', methods=['POST'])
@has_permission('can_manage_user_permissions')
@use_args({'permissions': fields.List(fields.String(), required=True)}, location='json')
@management_bp.response(200, MessageSchema)
@management_bp.response(400, MessageSchema)
@management_bp.response(500, MessageSchema)
def assign_role_permissions(args, role_name):
    """Assigns a list of permissions to a specific role. Overwrites existing role permissions."""
    if role_name not in [Roles.SUPER_ADMIN, Roles.MANAGER, Roles.CLIENT]:
        abort(400, message="Invalid role name.")
    
    data = args.get('permissions')
    if not data or not isinstance(data, list):
        abort(400, message="Invalid data format. Expected a list of permission names.")

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
        return {"message": f"Permissions for role {role_name} updated successfully."} # Return dict for Smorest
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating role permissions for {role_name}: {e}", exc_info=True)
        abort(500, message="Failed to update role permissions.")
