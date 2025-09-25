"""
API Routes for Masjid Applications
---------------------------------
This blueprint handles all API endpoints related to the submission and management
of Masjid Applications.
"""

from flask import request, g
from flask_smorest import Blueprint, abort

from ..services import application_service
from ..models import MasjidApplication, User
from ..schemas import (
    MasjidApplicationSchema,
    MasjidApplicationAdminSchema,
    ApplicationActionSchema,
    MessageSchema
)
from ..utils.auth import jwt_required, has_permission

application_bp = Blueprint(
    'MasjidApplications',
    __name__,
    url_prefix='/api/masjid-applications',
    description="Operations for Masjid registration applications."
)

@application_bp.route('/', methods=['POST'])
@jwt_required
@application_bp.arguments(MasjidApplicationSchema)
@application_bp.response(201, MasjidApplicationSchema)
@application_bp.doc(security=[{"Bearer": []}])
def submit_masjid_application(data):
    """Submit a new application to become a Masjid."""
    user = g.user
    if user.role != 'Client':
        abort(403, message="Only users with the 'Client' role can apply.")

    new_application = application_service.submit_application(user, data)

    return new_application

# --- Admin Routes ---

@application_bp.route('/admin', methods=['GET'])
@jwt_required
@has_permission('can_manage_masjid_applications')
@application_bp.response(200, MasjidApplicationAdminSchema(many=True))
@application_bp.doc(security=[{"Bearer": []}])
def get_all_applications():
    """Get a list of all Masjid Applications (for Admins)."""
    return MasjidApplication.query.all()

@application_bp.route('/admin/<int:app_id>/approve', methods=['POST'])
@jwt_required
@has_permission('can_manage_masjid_applications')
@application_bp.response(200, MessageSchema)
@application_bp.doc(security=[{"Bearer": []}])
def approve_application_route(app_id):
    """Approve a Masjid Application."""
    application = MasjidApplication.query.get_or_404(app_id)
    admin_user = g.user
    application_service.approve_application(application, admin_user)
    return {"message": f"Application {app_id} approved."}

@application_bp.route('/admin/<int:app_id>/reject', methods=['POST'])
@jwt_required
@has_permission('can_manage_masjid_applications')
@application_bp.arguments(ApplicationActionSchema)
@application_bp.response(200, MessageSchema)
@application_bp.doc(security=[{"Bearer": []}])
def reject_application_route(data, app_id):
    """Reject a Masjid Application."""
    application = MasjidApplication.query.get_or_404(app_id)
    admin_user = g.user
    reason = data.get('reason', 'No reason provided.')
    application_service.reject_application(application, admin_user, reason)
    return {"message": f"Application {app_id} rejected."}

@application_bp.route('/admin/<int:app_id>/force-approve', methods=['POST'])
@jwt_required
@has_permission('can_force_approve_applications')
@application_bp.response(200, MessageSchema)
@application_bp.doc(security=[{"Bearer": []}])
def force_approve_application_route(app_id):
    """Force approve a rejected or pending application (Super Admin)."""
    application = MasjidApplication.query.get_or_404(app_id)
    admin_user = g.user
    application_service.approve_application(application, admin_user)
    return {"message": f"Application {app_id} has been force-approved."}