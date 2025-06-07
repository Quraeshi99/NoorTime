# scripts/env_cleaner_validator.py

import os
from dotenv import load_dotenv

REQUIRED_KEYS = [
    "FLASK_APP",
    "FLASK_ENV",
    "SECRET_KEY",
    "SQLALCHEMY_DATABASE_URI",
    "PRAYER_API_ADAPTER",
    "PRAYER_API_BASE_URL",
    "OPENWEATHERMAP_API_KEY"
]
def clean_env_file(source_path=".env.example", output_path=".env"):
    valid_lines = []
    with open(source_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            try:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if key and value:
                    valid_lines.append(f"{key}={value}")
            except Exception:
                continue

    with open(output_path, "w", encoding="utf-8") as out:
        out.write("\n".join(valid_lines))
    print(f"✅ '{output_path}' फाइल generate हो गई साफ़ डेटा के साथ.")

def validate_env(env_path=".env"):
    load_dotenv(dotenv_path=env_path)
    print("🔍 Validating .env file...\n")
    missing = []
    for key in REQUIRED_KEYS:
        if not os.getenv(key):
            missing.append(key)
    if missing:
        print("❌ Missing Keys:", ", ".join(missing))
    else:
        print("✅ All required keys present.")

if __name__ == "__main__":
    clean_env_file()
    validate_env()
