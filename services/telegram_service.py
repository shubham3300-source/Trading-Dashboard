import os
import requests

def get_creds():
    """Get Telegram credentials from Streamlit secrets or environment variables"""
    try:
        # Try Streamlit secrets first (for cloud deployment)
        import streamlit as st
        if hasattr(st, 'secrets'):
            token = st.secrets.get("TELEGRAM_BOT_TOKEN")
            chat_id = st.secrets.get("TELEGRAM_CHAT_ID")
            if token and chat_id:
                return token, chat_id
    except Exception:
        pass
    
    # Fall back to environment variables (for local)
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    return token, chat_id

def send_message(text):
    """Send text message to Telegram"""
    token, chat_id = get_creds()
    
    if not token or not chat_id:
        return False, "❌ Telegram credentials not configured. Alerts disabled in public mode."
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    try:
        response = requests.post(
            url,
            data={"chat_id": chat_id, "text": text},
            timeout=30
        )
        
        if response.ok:
            return True, "✅ Alert sent successfully!"
        else:
            error_data = response.json()
            error_desc = error_data.get("description", "Unknown error")
            return False, f"❌ Telegram Error: {error_desc}"
            
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

def send_photo(photo_path, caption=""):
    """Send photo to Telegram"""
    token, chat_id = get_creds()
    
    if not token or not chat_id:
        return False, "❌ Telegram not configured"
    
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
        return False, f"❌ Error: {str(e)}"
