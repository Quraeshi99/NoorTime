# NoorTime - Global Prayer Times & Islamic Companion App

NoorTime ek comprehensive web application hai jo Flask framework ka upyog karke banaya gaya hai. Iska uddeshya upyogkartaon ko sahi namaz ke samay, Qibla disha, aur anya mahatvapurna Islamic upyogitaen pradan karna hai. Yeh application user authentication, personalized prayer time adjustments, aur ek modern, responsive user interface ke saath aata hai.

## Features

*   **Sahi Namaz ke Samay:** Upyogkarta ke sthan aur chune gaye calculation method ke aadhar par namaz ke samay fetch karta hai.
*   **Personalized Settings:** Upyogkarta har namaz ke liye apne samay ke offsets ko adjust kar sakte hain aur fixed samay set kar sakte hain.
*   **User Authentication:** Surakshit user registration aur login functionality.
*   **Responsive Design:** Tailwind CSS ka upyog karke banaya gaya ek modern aur adaptive user interface.
*   **Geocoding:** Shahar ke naam ke aadhar par sthan ko automatically nirdharit karta hai.
*   **Email Notifications:** (Yadi lagu kiya gaya hai, jaise ki OTP verification ke liye)
*   **Sentry Integration:** Application error tracking aur performance monitoring ke liye.

## Technologies Used

**Backend:**
*   Python
*   Flask (Web Framework)
*   SQLAlchemy (ORM for database interaction)
*   Flask-Login (User session management)
*   Flask-Mail (Email sending)
*   Flask-Migrate (Database migrations)
*   Flask-Limiter (Rate limiting)
*   Sentry-SDK (Error tracking)
*   Requests (HTTP library for API calls)

**Frontend:**
*   HTML
*   CSS (Tailwind CSS)
*   JavaScript

**Database:**
*   SQLite (Development)
*   PostgreSQL (Production - configured via environment variables)

**APIs:**
*   AlAdhan API (Namaz ke samay ke liye)
*   OpenWeatherMap API (Geocoding ke liye)

## Setup Instructions

In steps ko follow karke aap NoorTime ko apne local development environment mein set up kar sakte hain:

### 1. Repository Clone Karein

```bash
git clone https://github.com/your-username/NoorTime.git
cd NoorTime
```

### 2. Virtual Environment Banayein aur Activate Karein

Python dependencies ko alag-alag rakhne ke liye ek virtual environment banana sifarish ki jaati hai.

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate  # Windows
```

### 3. Python Dependencies Install Karein

```bash
pip install -r requirements.txt
```

### 4. Node.js Dependencies Install Karein (Tailwind CSS ke liye)

Tailwind CSS ko compile karne ke liye Node.js aur npm ki zaroorat hogi.

```bash
npm install
```

### 5. Environment Variables Set Karein

Project `.env` file ka upyog karta hai configuration ke liye. `.env.example` file ko copy karke `.env` banayein aur zaroori variables ko update karein.

```bash
cp .env.example .env
```

`.env` file mein nimnalikhit variables ko update karein (ya naye add karein):

```
SECRET_KEY="your_super_secret_key_here"
FLASK_CONFIG="development" # ya "production", "testing"
SQLALCHEMY_DATABASE_URI="sqlite:///instance/database.db" # Development ke liye
# Production ke liye: SQLALCHEMY_DATABASE_URI="postgresql://user:password@host:port/database"

MAIL_SERVER="smtp.gmail.com"
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME="your_email@example.com"
MAIL_PASSWORD="your_email_password" # Ya app-specific password
MAIL_DEFAULT_SENDER="NoorTime <noreply@example.com>"

PRAYER_API_ADAPTER="AlAdhanAdapter"
PRAYER_API_BASE_URL="http://api.aladhan.com/v1"
PRAYER_API_KEY="" # AlAdhan API key (agar zaroori ho)

OPENWEATHERMAP_API_KEY="your_openweathermap_api_key"

SENTRY_DSN="" # Sentry DSN URL (agar upyog kar rahe hain)
```

### 6. Database Initialize aur Migrate Karein

```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 7. Development Server Chalayein

Tailwind CSS watcher aur Flask application ko ek saath chalane ke liye `start_dev.sh` script ka upyog karein.

```bash
bash start_dev.sh
```

Application ab `http://0.0.0.0:5000` par chalna chahiye (ya jo bhi port aapne `.env` mein configure kiya hai).

## Project Structure

```
/data/data/com.termux/files/home/NoorTime/
├── .env
├── .env.example
├── .flaskenv
├── .gitignore
├── config.py
├── manifest.json
├── package-lock.json
├── package.json
├── postcss.config.js
├── README.md
├── requirements.txt
├── run.py
├── service-worker.js
├── start_dev.sh
├── tailwind.config.js
├── __pycache__/
├── instance/
│   └── database.db
├── node_modules/
│   └── ... (Node.js dependencies)
├── project/
│   ├── __init__.py
│   ├── forms.py
│   ├── models.py
│   ├── extensions.py
│   ├── __pycache__/
│   │   └── ...
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── api_routes.py
│   │   ├── auth_routes.py
│   │   ├── main_routes.py
│   │   ├── test_mail.py
│   │   └── __pycache__/
│   │       └── ...
│   ├── services/
│   │   ├── __init__.py
│   │   ├── prayer_time_service.py
│   │   ├── api_adapters/
│   │   │   ├── __init__.py
│   │   │   ├── aladhan_adapter.py
│   │   │   └── base_adapter.py
│   │   │   └── __pycache__/
│   │   │       └── ...
│   │   └── __pycache__/
│   │       └── ...
│   ├── static/
│   │   ├── css/
│   │   │   ├── dist/
│   │   │   │   ├── .gitkeep
│   │   │   │   └── style.css
│   │   │   └── src/
│   │   │       └── input.css
│   │   ├── fonts/
│   │   │   └── DS-DIGI.TTF
│   │   ├── images/
│   │   │   ├── allah.svg
│   │   │   ├── bismillah.svg
│   │   │   └── mosque_dome.svg
│   │   ├── js/
│   │   │   ├── main_script.js
│   │   │   └── settings_script.js
│   │   └── sounds/
│   │       └── beep.mp3
│   ├── templates/
│   │   ├── base_layout.html
│   │   ├── index.html
│   │   ├── login.html
│   │   ├── register.html
│   │   └── settings.html
│   └── utils/
│       ├── __init__.py
│       ├── email_utils.py
│       ├── mail_config.py
│       ├── prayer_display_helper.py
│       ├── template_helpers.py
│       └── time_utils.py
│       └── __pycache__/
│           └── ...
└── scripts/
    └── env_cleaner_validator.py
```

## Contributing

Contributions ka swagat hai! Kripya `CONTRIBUTING.md` file (agar maujood ho) dekhein ya pull request kholne se pehle issues section mein ek naya issue banayein.

## License

Yeh project MIT License ke antargat licensed hai. Adhik jaankari ke liye `LICENSE` file dekhein.
