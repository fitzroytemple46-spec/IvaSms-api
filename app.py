from flask import Flask, jsonify, request
import requests
import json
import time
import threading
from datetime import datetime
import telegram  # pip install python-telegram-bot

app = Flask(__name__)

# ====================== CONFIGURATION ======================
# ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←

TELEGRAM_BOT_TOKEN = "8699000605:AAFNu66RxuzOXu7vN-VkdafBge2TS6FbSr4"      # Get from @BotFather
TELEGRAM_GROUP_CHAT_ID = -1003773578007                   # Your group ID (negative for groups)

# iVASMS settings
IVASMS_BASE_URL = "https://panel.ivasms.com"              # Change if your panel URL is different
COOKIES_FILE = "cookies.json"

POLL_INTERVAL = 15  # seconds between checks

# Global variables
last_check_time = None
client_session = requests.Session()

# ===========================================================

def load_cookies():
    try:
        with open(COOKIES_FILE, 'r') as f:
            data = json.load(f)
        # Support both array and dict formats
        cookies = data.get('cookies', data)
        for cookie in cookies:
            client_session.cookies.set(cookie.get('name'), cookie.get('value'))
        print("✅ Cookies loaded successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to load cookies: {e}")
        return False

def send_to_telegram(message):
    try:
        bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
        bot.send_message(chat_id=TELEGRAM_GROUP_CHAT_ID, text=message, parse_mode='HTML')
        print(f"📤 Sent to Telegram: {message[:100]}...")
    except Exception as e:
        print(f"❌ Telegram error: {e}")

def fetch_new_otps():
    global last_check_time
    try:
        # Example endpoint - adjust based on your panel's actual API
        url = f"{IVASMS_BASE_URL}/sms"   # or /api/otps, /api/messages etc.
        
        params = {
            'date': datetime.now().strftime('%d/%m/%Y'),
            'limit': 20
        }
        
        response = client_session.get(url, params=params, timeout=20)
        
        if response.status_code == 200:
            data = response.json()
            otp_messages = data.get('otp_messages', []) if isinstance(data, dict) else []
            
            for msg in otp_messages:
                # Customize formatting as needed
                text = f"🔐 <b>New OTP Received</b>\n\n" \
                       f"📱 Number: <code>{msg.get('phone_number', 'N/A')}</code>\n" \
                       f"💬 Message: <code>{msg.get('otp_message', msg.get('message', 'N/A'))}</code>\n" \
                       f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}"
                
                send_to_telegram(text)
            
            last_check_time = datetime.now()
            return len(otp_messages)
        else:
            print(f"⚠️ iVASMS returned {response.status_code}")
            return 0
    except Exception as e:
        print(f"❌ Fetch error: {e}")
        return 0

def polling_loop():
    print("🚀 Starting iVASMS polling...")
    while True:
        try:
            count = fetch_new_otps()
            if count > 0:
                print(f"✅ Found {count} new message(s)")
        except:
            pass
        time.sleep(POLL_INTERVAL)

@app.route('/')
def home():
    status = "Running" if last_check_time else "Starting..."
    return jsonify({
        "status": "online",
        "last_check": last_check_time.strftime("%Y-%m-%d %H:%M:%S") if last_check_time else "Never",
        "message": "iVASMS → Telegram Forwarder is active"
    })

@app.route('/check')
def manual_check():
    count = fetch_new_otps()
    return jsonify({"status": "success", "new_messages": count})

if __name__ == '__main__':
    print("=== iVASMS to Telegram Forwarder ===")
    
    if not load_cookies():
        print("❌ Please fix cookies.json and restart")
        exit(1)
    
    # Start polling in background thread
    thread = threading.Thread(target=polling_loop, daemon=True)
    thread.start()
    
    # Run Flask server
    app.run(host='0.0.0.0', port=5000, debug=False)
