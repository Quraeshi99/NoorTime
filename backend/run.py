import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import os
from project import create_app, db
from flask_migrate import Migrate
from config import config_by_name

# Step 1: Determine the config name
config_name = os.environ.get('FLASK_CONFIG') or 'default'
if config_name not in config_by_name:
    print(f"Warning: Config name '{config_name}' not found. Using 'default' config.")
    config_name = 'default'

# Step 2: Create the app
app = create_app(config_name)

# Step 3: Initialize Flask-Migrate
migrate = Migrate(app, db)

# Step 4: Database Migrations
# Database tables are now managed exclusively via Flask-Migrate.
# To create or update tables, use the following commands in your terminal:
# 1. flask db migrate -m "Your migration message"
# 2. flask db upgrade
# The old db.create_all() has been removed to rely on this better system.


# Step 5: Run the app
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.logger.info(f"Starting application with '{config_name}' configuration...")
    app.logger.info(f"Debug mode is: {'ON' if app.config.get('DEBUG') else 'OFF'}")
    app.logger.info(f"Application will run on host 0.0.0.0 and port {port}")
    app.run(host='0.0.0.0', port=port)