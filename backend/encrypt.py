import os
from cryptography.fernet import Fernet

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")

# Generate encryption key in .env if not exists
def init_encryption_key():
    if not os.path.exists(ENV_PATH):
        key = Fernet.generate_key().decode()
        with open(ENV_PATH, "w") as f:
            f.write(f"ENCRYPTION_KEY={key}\n")
        return key
    
    # Read existing .env
    with open(ENV_PATH, "r") as f:
        for line in f:
            if line.startswith("ENCRYPTION_KEY="):
                return line.split("=", 1)[1].strip()
            
    # Key not found in existing .env, append it
    key = Fernet.generate_key().decode()
    with open(ENV_PATH, "a") as f:
        f.write(f"ENCRYPTION_KEY={key}\n")
    return key

# Load key
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    ENCRYPTION_KEY = init_encryption_key()

cipher_suite = Fernet(ENCRYPTION_KEY.encode())

def encrypt_val(val: str) -> str:
    if not val:
        return ""
    return cipher_suite.encrypt(val.encode()).decode()

def decrypt_val(val: str) -> str:
    if not val:
        return ""
    try:
        return cipher_suite.decrypt(val.encode()).decode()
    except Exception:
        return ""  # Return empty if decryption fails (e.g. invalid key)
