import os
import requests

def get_creds():
    """Get Telegram credentials from environment variables"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    return token, chat_id

def send_message(text):
    """Send text message to Telegram
    
    Args:
        text (str): Message to send
        
    Returns:
        tuple: (success: bool, response: str)
    """
    token, chat_id = get_creds()
    
    if not token or not chat_id:
        return False, "❌ Telegram credentials not set. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables."
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    try:
        response = requests.post(
            url,
            data={
                "chat_id": chat_id,
                "text": text
            },
            timeout=30
        )
        
        if response.ok:
            return True, "✅ Alert sent successfully!"
        else:
            error_data = response.json()
            error_desc = error_data.get("description", "Unknown error")
            error_code = error_data.get("error_code", 0)
            
            # Handle specific errors
            if error_code == 403:
                return False, f"❌ Bot blocked. Open Telegram, search for your bot, and send /start"
            elif error_code == 400 and "chat not found" in error_desc:
                return False, f"❌ Invalid Chat ID. Get your ID from @userinfobot"
            else:
                return False, f"❌ Telegram Error ({error_code}): {error_desc}"
            
    except requests.exceptions.Timeout:
        return False, "❌ Request timeout. Check internet connection."
    
    except requests.exceptions.ConnectionError:
        return False, "❌ Connection error. Check internet connection."
    
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

def send_photo(photo_path, caption=""):
    """Send photo to Telegram"""
    token, chat_id = get_creds()
    
    if not token or not chat_id:
        return False, "❌ Telegram credentials not set."
    
    if not os.path.exists(photo_path):
        return False, f"❌ Photo not found: {photo_path}"
    
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    
    try:
        with open(photo_path, "rb") as photo:
            response = requests.post(
                url,
                data={"chat_id": chat_id, "caption": caption},
                files={"photo": photo},
                timeout=60
            )
        
        if response.ok:
            return True, "✅ Photo sent!"
        else:
            error = response.json()
            return False, f"❌ Error: {error.get('description', 'Unknown')}"
            
    except Exception as e:
        return False, f"❌ Error: {str(e)}"