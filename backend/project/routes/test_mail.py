from flask import Blueprint, request, jsonify, abort
from flask_login import login_required, current_user
from flask_mail import Message
from .. import mail

test_mail_bp = Blueprint('test_mail', __name__)

@test_mail_bp.route('/send-test-mail', methods=['POST'])
@login_required
def send_test_mail():
    if not current_user.is_admin:
        abort(403)  # Forbidden

    data = request.get_json()
    recipient = data.get('email')

    if not recipient:
        return jsonify({"error": "Email address is required"}), 400

    try:
        msg = Message(subject="🚀 OTP Verification Test",
                      recipients=[recipient],
                      body="This is a test OTP message from NoorTime. If you are seeing this, email sending is successful.")

        mail.send(msg)
        return jsonify({"message": f"Test email sent to {recipient}"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
