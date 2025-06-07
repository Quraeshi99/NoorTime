# Prayer Times Global Web Application - संस्करण 2.0

यह एक वैश्विक नमाज़ समय वेब एप्लीकेशन है जो उपयोगकर्ताओं को उनकी लोकेशन और पसंदीदा गणना विधि के आधार पर सटीक नमाज़ का समय प्रदान करता है। इसमें उपयोगकर्ता द्वारा अनुकूलन योग्य सेटिंग्स, अतिथि मोड और पंजीकृत उपयोगकर्ता मोड की सुविधाएँ हैं। यह Flask (Python) बैकएंड और Tailwind CSS के साथ HTML/JavaScript फ्रंटएंड का उपयोग करता है, और इसे एक प्रोफेशनल, मॉड्यूलर और लचीली संरचना के साथ बनाया गया है।

**मुख्य विशेषताएँ (Features - संस्करण 2.0):**

*   **यूजर अकाउंट सिस्टम:**
    *   ईमेल और पासवर्ड के साथ सुरक्षित रजिस्ट्रेशन और लॉगिन (Flask-Login, Flask-WTF)।
    *   पासवर्ड हैशिंग (pbkdf2:sha256)।
    *   लॉगिन प्रयासों पर रेट लिमिटिंग (Flask-Limiter)।
    *   CSRF सुरक्षा।
*   **अतिथि मोड:** बिना अकाउंट बनाए ऐप की मुख्य कार्यक्षमता का उपयोग करने की सुविधा।
*   **सेटिंग्स (पंजीकृत उपयोगकर्ताओं के लिए डेटाबेस में सेव, अतिथि के लिए `localStorage` में अस्थायी):**
    *   **होम लोकेशन:** लैटीट्यूड, लोंगिट्यूड और शहर का नाम सेट करने की सुविधा।
    *   **नमाज़ गणना विधि:** विभिन्न इस्लामिक स्कूलों ऑफ थॉट (शाफी, हनफी, मालिकी, हम्बली से मैप किए गए API मेथड्स) में से चुनने का विकल्प।
    *   **टाइम फॉर्मेट:** 12-घंटे (AM/PM) या 24-घंटे फॉर्मेट चुनने का टॉगल।
    *   **प्रत्येक नमाज़ के लिए (फज्र, ज़ुहर, असर, मगरिब, इशा, जुम्मा):**
        *   फिक्स टाइम मोड: सीधे अज़ान और जमात का समय सेट करें।
        *   अंतराल मोड: API के नमाज़ शुरू होने के समय से अज़ान का अंतराल और अज़ान से जमात का अंतराल मिनटों में सेट करें।
        *   चेकबॉक्स: "यदि API लोकेशन बदले तो क्या अज़ान/जमात अंतराल एडजस्ट होना चाहिए"।
*   **मुख्य डिस्प्ले:**
    *   लाइव घड़ी, वर्तमान दिन, ग्रेगोरियन और हिजरी तारीखें।
    *   अगली नमाज़ का नाम, अज़ान/जमात समय, शेष समय।
    *   जमात से 2 मिनट पहले काउंटडाउन और बीप साउंड।
    *   जमात के बाद 10 मिनट का काउंटडाउन।
    *   API आधारित वर्तमान नमाज़ पीरियड (स्टार्ट/एंड), ज़वाल, सूर्योदय, सूर्यास्त, सहर, इफ्तार।
    *   मुख्य नमाज़ टेबल (फज्र से इशा, जुम्मा) - अंग्रेजी और अरबी नामों के साथ।
    *   कल की फज्र।
    *   वर्तमान API लोकेशन का नाम और तापमान (OpenWeatherMap API से, यदि कॉन्फ़िगर किया गया हो)।
*   **"अपडेट API लोकेशन" बटन:** ब्राउज़र जियोलोकेशन या मैनुअल इनपुट (शहर का नाम/लैटीट्यूड/लोंगिट्यूड) द्वारा API लोकेशन अपडेट करने की सुविधा।
*   **API फ्लेक्सिबिलिटी:** API एडाप्टर पैटर्न का उपयोग (अभी AlAdhanAdapter के साथ)। API बेस URL `.env` से कॉन्फ़िगर करने योग्य।
*   **प्रोफेशनल कोड संरचना:** Flask ब्लूप्रिंट्स और मॉड्यूलर डिज़ाइन।
*   **बेहतरीन UI/UX:** Material Design 3 से प्रेरित, आधुनिक डार्क थीम, SVG आइकन्स, आकर्षक टाइल्स/कार्ड्स, और पूरी तरह से मोबाइल-फर्स्ट रिस्पॉन्सिव डिज़ाइन।
*   **PWA (Progressive Web App) क्षमताएँ:**
    *   सर्विस वर्कर द्वारा ऑफलाइन कैशिंग (ऐप शेल और अंतिम ज्ञात डेटा)।
    *   वेब ऐप मेनिफेस्ट (`manifest.json`) ताकि उपयोगकर्ता ऐप को होम स्क्रीन पर जोड़ सकें।
    *   UI में ऑफलाइन इंडिकेटर।
*   **विस्तृत लॉगिंग:** एप्लीकेशन घटनाओं और त्रुटियों के लिए।
*   **डेटाबेस:** SQLite (स्थानीय और Replit के लिए आसान सेटअप)।

## फ़ोल्डर संरचना (Folder Structure)

PrayerTimesGlobal/ (आपके Repl का नाम)
├── run.py # Flask एप्लीकेशन को चलाने के लिए मुख्य स्क्रिप्ट
├── config.py # Flask कॉन्फ़िगरेशन सेटिंग्स
├── project/ # मुख्य एप्लीकेशन पैकेज
│ ├── init.py # ऐप फैक्ट्री, एक्सटेंशन इनिशियलाइज़ेशन
│ ├── models.py # SQLAlchemy डेटाबेस मॉडल्स (User, UserSettings)
│ ├── forms.py # Flask-WTF फॉर्म्स (LoginForm, RegistrationForm, SettingsForm)
│ ├── routes/ # ब्लूप्रिंट्स के लिए फ़ोल्डर
│ │ ├── init.py
│ │ ├── main_routes.py # मुख्य रूट्स (जैसे /, /settings)
│ │ ├── auth_routes.py # ऑथेंटिकेशन रूट्स (/login, /register, /logout)
│ │ └── api_routes.py # सभी API एंडपॉइंट्स
│ ├── services/ # व्यावसायिक लॉजिक और बाहरी सेवाओं के लिए
│ │ ├── init.py
│ │ ├── prayer_time_service.py # नमाज़ समय गणना, API कॉल लॉजिक
│ │ └── api_adapters/ # API एडाप्टर्स के लिए फ़ोल्डर
│ │ ├── init.py
│ │ ├── base_adapter.py # बेस API एडाप्टर क्लास
│ │ └── aladhan_adapter.py # AlAdhan API के लिए विशिष्ट एडाप्टर
│ ├── static/
│ │ ├── css/
│ │ │ ├── src/input.css
│ │ │ └── dist/style.css (Tailwind द्वारा जेनरेटेड)
│ │ ├── js/
│ │ │ ├── main_script.js (मुख्य डिस्प्ले के लिए)
│ │ │ ├── settings_script.js (सेटिंग्स पेज के लिए)
│ │ │ └── auth_script.js (लॉगिन/रजिस्ट्रेशन के लिए, यदि आवश्यक हो)
│ │ ├── fonts/ (जैसे DS-DIGI.TTF या Orbitron.ttf)
│ │ ├── images/ (जैसे आइकन्स, मस्जिद डोम प्लेसहोल्डर)
│ │ └── sounds/ (जैसे beep.mp3)
│ └── templates/
│ ├── base_layout.html (सभी पेजों के लिए बेस लेआउट)
│ ├── index.html (मुख्य डिस्प्ले)
│ ├── login.html
│ ├── register.html
│ └── settings.html
├── database.db (SQLite डेटाबेस - flask create-db से बनेगा)
├── requirements.txt (Python निर्भरताएँ)
├── package.json (Node.js निर्भरताएँ और स्क्रिप्ट्स)
├── tailwind.config.js (Tailwind CSS कॉन्फ़िगरेशन)
├── postcss.config.js (PostCSS कॉन्फ़िगरेशन)
├── .env.example (एनवायरनमेंट वेरिएबल का उदाहरण)
├── manifest.json (PWA मेनिफेस्ट फ़ाइल)
├── service-worker.js (PWA सर्विस वर्कर - static या रूट में हो सकता है)
├── start_dev.sh (Replit पर डेवलपमेंट सर्वर चलाने के लिए स्क्रिप्ट)
└── README.md (यह फ़ाइल)
## नया अपडेट करने के बाद का फोल्डर का स्ट्रक्चर कुछ इस प्रकार है हो सकता है इसमें पिछले वाले से कोई एक फाइल मिसिंग ही तो कोर्स चेक अवश्य कर ले
# फोल्डर स्ट्रक्चर देखने के लिए पहले इसको ही प्रफेंस दे 

├── README.md
├── config.py
├── manifest.json
├── package.json
├── postcss.config.js
├── project
│   ├── __init__.py
│   ├── extensions.py
│   ├── forms.py
│   ├── models.py
│   ├── routes
│   │   ├── __init__.py
│   │   ├── api_routes.py
│   │   ├── auth_routes.py
│   │   ├── main_routes.py
│   │   └── test_mail.py
│   ├── services
│   │   ├── __init__.py
│   │   ├── api_adapters
│   │   │   ├── __init__.py
│   │   │   ├── aladhan_adapter.py
│   │   │   └── base_adapter.py
│   │   └── prayer_time_service.py
│   ├── static
│   │   ├── css
│   │   │   ├── dist
│   │   │   └── src
│   │   │       └── input.css
│   │   ├── fonts
│   │   │   └── DS-DIGI.TTF
│   │   ├── js
│   │   │   ├── main_script.js
│   │   │   └── settings_script.js
│   │   └── sounds
│   │       └── beep.mp3
│   ├── templates
│   │   ├── base_layout.html
│   │   ├── index.html
│   │   ├── login.html
│   │   ├── register.html
│   │   └── settings.html
│   └── utils
│       ├── email_utils.py
│       └── mail_config.py
├── requirements.txt
├── run.py
├── scripts
│   └── env_cleaner_validator.py
├── service-worker.js
├── start_dev.sh
└── tailwind.config.js

**15 directories, 37 files



## सेटअप और रन करने के निर्देश (Setup and Run Instructions)

### पूर्वापेक्षाएँ (Prerequisites)
*   Python 3.8+
*   Node.js 14+ और npm

### Replit पर सेटअप
1.  **नया Python Repl बनाएँ।** `main.py` का नाम बदलकर `run.py` करें।
2.  **फ़ोल्डर और फाइलें बनाएँ:** ऊपर दी गई "फ़ोल्डर संरचना" के अनुसार सभी फाइलें और फ़ोल्डर Replit में बनाएँ।
3.  **`.replit` फ़ाइल कॉन्फ़िगर करें:** (कंटेंट पहले दिया जा चुका है, `run = "bash start_dev.sh"` सुनिश्चित करें)।
4.  **`start_dev.sh` शेल स्क्रिप्ट बनाएँ (रूट में) और एग्जीक्यूटेबल करें:** (कंटेंट पहले दिया जा चुका है)। `chmod +x start_dev.sh` चलाएँ।
5.  **Replit Secrets (ENV वेरिएबल्स) सेट करें:**
    *   `SECRET_KEY`: एक मजबूत रैंडम स्ट्रिंग।
    *   `OPENWEATHERMAP_API_KEY`: OpenWeatherMap से आपकी API की (जियोकोडिंग और तापमान के लिए)।
    *   `PRAYER_API_BASE_URL`: (वैकल्पिक, डिफ़ॉल्ट AlAdhan है)
    *   (अन्य जैसे `FLASK_ENV`, `FLASK_DEBUG` भी यहाँ सेट किए जा सकते हैं)।
6.  **Replit शेल में कमांड्स चलाएँ:**
    ```bash
    pip install -r requirements.txt
    npm install
    npm run build:css 
    flask create-db 
    ```
7.  **एप्लीकेशन चलाएँ:** Replit का हरा "Run" बटन दबाएँ।

### स्थानीय मशीन पर सेटअप
1.  प्रोजेक्ट फ़ोल्डर में जाएँ।
2.  Python वर्चुअल एनवायरनमेंट बनाएँ और सक्रिय करें।
3.  `pip install -r requirements.txt` चलाएँ।
4.  `npm install` चलाएँ।
5.  `.env.example` को `.env` में कॉपी करें और `SECRET_KEY` और `OPENWEATHERMAP_API_KEY` सेट करें।
6.  `flask create-db` चलाएँ।
7.  एक टर्मिनल में `npm run watch:css` चलाएँ।
8.  दूसरे टर्मिनल में `python run.py` (या `flask run`) चलाएँ।
9.  ब्राउज़र में `http://127.0.0.1:5000/` खोलें।

## एसेट्स (Assets)
*   **फॉन्ट:** `static/fonts/` में (जैसे Orbitron या Share Tech Mono)।
*   **इमेजेज:** `static/images/` में (SVG आइकन्स, प्लेसहोल्डर्स)।
*   **साउंड:** `static/sounds/beep.mp3`।
*   इन सभी के लिए `input.css` और HTML टेम्पलेट्स में पाथ सही होने चाहिए।

## भविष्य की संभावनाएँ और स्केलिंग (Future Scope & Scaling)
*   **डेटाबेस अपग्रेड:** उत्पादन के लिए PostgreSQL/MySQL।
*   **मल्टी-यूजर एडमिन पैनल (यदि आवश्यक हो):** भूमिका-आधारित एक्सेस।
*   **उन्नत लॉगिंग/मॉनिटरिंग:** Sentry, ELK।
*   **कैशिंग:** Flask-Caching, Redis/Memcached।
*   **बैकग्राउंड टास्क क्यू:** Celery, RQ।
*   **कंटेनरीकरण:** Docker।
*   **क्लाउड डिप्लॉयमेंट:** AWS, Google Cloud, Azure, Heroku।
*   **मोबाइल ऐप इंटीग्रेशन:** वर्तमान Flask API का उपयोग करके फ़्लटर ऐप बनाना।
*   **और गणना विधियाँ/API एडाप्टर्स:** अन्य API या गणना तरीकों के लिए समर्थन जोड़ना।
*   **थीमिंग:** उपयोगकर्ता को लाइट/डार्क के अलावा और थीम चुनने का विकल्प देना।
*   **ईमेल वेरिफिकेशन:** रजिस्ट्रेशन के लिए।
*   **"पासवर्ड भूल गए" फंक्शनैलिटी।**

## मुख्य फंक्शनैलिटीज़ का कार्यप्रवाह
(यह सेक्शन `README.md` को और विस्तृत करेगा, जैसा हमने पहले डिस्कस किया था)
🧱 Advanced Setup Users: अगर आप database schema को manually manage नहीं करना चाहते, तो नीचे Flask-Migrate वाला सेक्शन ज़रूर पढ़ें।
---# STEP 1: Install Flask-Migrate (अगर पहले से नहीं किया)
pip install Flask-Migrate

# STEP 2: requirements.txt में यह लाइन ज़रूर हो:
# Flask-Migrate

# STEP 3: प्रोजेक्ट रूट में .flaskenv फाइल बनाएँ और इसमें ये डालें:
echo "FLASK_APP=run.py" >> .flaskenv
echo "FLASK_ENV=development" >> .flaskenv

# STEP 4: डेटाबेस के लिए migration फोल्डर इनिशियलाइज़ करें (सिर्फ पहली बार):
flask db init

# STEP 5: अपनी models.py पढ़कर migration script बनाएँ:
flask db migrate -m "initial migration"

# STEP 6: migration को डेटाबेस में लागू करें:
flask db upgrade

# 🔁 NOTE: भविष्य में models.py में बदलाव करें तो फिर ये दो चलाएँ:
# flask db migrate -m "explanation of changes"
# flask db upgrade


अद्यतन विशेषताएँ (New Features Added - v2.0.X onwards):

🔒 ईमेल OTP वेरिफिकेशन सिस्टम (Optional Activation Mode के साथ)

Flask-Mail के माध्यम से रजिस्ट्रेशन के समय ईमेल पर 6-digit OTP भेजा जाता है।

OTP की वैधता समय-सीमित होती है (जैसे 10 मिनट)।

Users जब तक ईमेल सत्यापित नहीं करते, लॉगिन नहीं कर सकते (unless guest mode)।

.env में SMTP कॉन्फ़िगरेशन:

MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com


📦 Flask-Migrate इंटीग्रेशन (डेटाबेस स्कीमा वर्ज़निंग)

अब डेटाबेस को मैन्युअली drop/create करने की ज़रूरत नहीं।

जब भी models.py बदले — बस चलाएँ:

flask db migrate -m "Added OTP field to User model"
flask db upgrade

Initial setup:

flask db init
flask db migrate -m "initial"
flask db upgrade


🛡️ User Model में OTP और Verification फ़ील्ड जोड़े गए:

otp_code, otp_expiry, is_verified जैसे फ़ील्ड models.py में जुड़े हैं।

इन्हें माईग्रेट करने के लिए Flask-Migrate को इस्तेमाल किया गया।


🔄 रजिस्ट्रेशन फ्लो में बदलाव:

register() व्यू में OTP जनरेशन, ईमेल भेजना, और OTP पेज पर रीडायरेक्ट शामिल है।

अलग verify_otp() व्यू जो OTP मिलान और वैधता चेक करता है।

OTP सफल होने पर user.is_verified = True


💌 ईमेल-सेंड फंक्शन (Reusable Service):

def send_otp_email(user_email, otp_code):
    msg = Message('आपका OTP कोड', recipients=[user_email])
    msg.body = f"आपका OTP कोड है: {otp_code}\nयह कोड 10 मिनट तक वैध है।"
    mail.send(msg)


    आने वाले फ़ीचर्स (Next Build Ideas)

🔓 पासवर्ड रीसेट लिंक/OTP फ़्लो

📊 यूज़र usage logs (किसने कब क्या बदला)

🕌 मस्जिद-एडमिन मोड (Display-only TV Screens के लिए)

🔈 अज़ान प्लेयर ऑटो-ट्रिगर (beep की जगह अज़ान.mp3)

🌐 Multi-language UI (उर्दू, अंग्रेज़ी, हिंदी)
