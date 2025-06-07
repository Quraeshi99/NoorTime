from flask import Blueprint, request, jsonify
from flask_mail import Message
from .. import mail

test_mail_bp = Blueprint('test_mail', __name__)

@test_mail_bp.route('/send-test-mail', methods=['POST'])
def send_test_mail():
    data = request.get_json()
    recipient = data.get('email')

    if not recipient:
        return jsonify({"error": "Email address is required"}), 400

    try:
        msg = Message(subject="🚀 OTP Verification Test",
                      recipients=[recipient],
                      body="यह एक टेस्ट OTP मैसेज है। यदि आप इसे देख रहे हैं, तो Email भेजना सफल है।")

        mail.send(msg)
        return jsonify({"message": f"Test email sent to {recipient}"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
