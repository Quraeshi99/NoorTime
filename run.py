import os
from project import create_app, db  # ✅ db import किया
from flask_migrate import Migrate   # ✅ Migrate import किया
from config import config_by_name   # ✅ config import किया

# 🧠 Step 1: config_name तय करो
config_name = os.environ.get('FLASK_CONFIG') or 'default'
if config_name not in config_by_name:
    print(f"Warning: Config name '{config_name}' not found. Using 'default' config.")
    config_name = 'default'

# ✅ Step 2: app बनाओ
app = create_app(config_by_name[config_name])

# ✅ Step 3: Flask-Migrate को initialize करो
migrate = Migrate(app, db)

# ✅ Step 4: App run करो
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000)) 
    app.logger.info(f"Starting application with '{config_name}' configuration...")
    app.logger.info(f"Debug mode is: {'ON' if app.config.get('DEBUG') else 'OFF'}")
    app.logger.info(f"Application will run on host 0.0.0.0 and port {port}")
    app.run(host='0.0.0.0', port=port)
