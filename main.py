#!/usr/bin/env python3
"""
Facebook Messenger Automation Bot - Streamlit Cloud Version
"""

import streamlit as st
import json
import time
import threading
import os
import queue 
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
import subprocess

# ============================================
# PAGE CONFIGURATION
# ============================================
st.set_page_config(
    page_title="FB Messenger Bot", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================
# GLOBAL THREAD-SAFE QUEUE
# ============================================
LOG_QUEUE = queue.Queue()

# ============================================
# CUSTOM CSS STYLING
# ============================================
st.markdown("""
<style>
    .stButton > button {
        background: linear-gradient(90deg, #6B5DD8 0%, #8B7DE8 100%);
        color: white;
        border: none;
        padding: 12px 24px;
        font-size: 16px;
        border-radius: 8px;
        width: 100%;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background: linear-gradient(90deg, #5B4DC8 0%, #7B6DD8 100%);
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(107, 93, 216, 0.3);
    }
    .stButton > button:disabled {
        background: #cccccc;
        cursor: not-allowed;
    }
    .log-container {
        background-color: #1a1a1a;
        color: #00ff00;
        padding: 20px;
        border-radius: 8px;
        font-family: 'Courier New', monospace;
        height: 400px;
        overflow-y: auto;
        margin-top: 20px;
        border: 1px solid #333;
    }
    .log-entry {
        margin: 4px 0;
        font-size: 14px;
        line-height: 1.4;
    }
    h1 {
        color: #6B5DD8;
        text-align: center;
        margin-bottom: 30px;
    }
    .status-running {
        color: #00ff00;
        font-weight: bold;
        font-size: 18px;
    }
    .status-stopped {
        color: #ff4444;
        font-weight: bold;
        font-size: 18px;
    }
    .config-section {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        border: 1px solid #e9ecef;
    }
    .port-info {
        background: linear-gradient(90deg, #6B5DD8 0%, #8B7DE8 100%);
        color: white;
        padding: 12px;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 20px;
        font-weight: bold;
        font-size: 16px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# SESSION STATE INITIALIZATION
# ============================================
def init_session_state():
    """Initialize all session state variables with default values"""
    if 'logs' not in st.session_state:
        st.session_state.logs = []
    if 'is_running' not in st.session_state:
        st.session_state.is_running = False
    if 'stop_requested' not in st.session_state:
        st.session_state.stop_requested = False
    if 'automation_thread' not in st.session_state:
        st.session_state.automation_thread = None

# Initialize session state at startup
init_session_state()

# ============================================
# HELPER FUNCTIONS
# ============================================

def add_log(message):
    """
    Thread-safe function to add a timestamped log entry.
    It puts the log into a global queue instead of updating st.session_state directly.
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] AUTO-1: {message}"
    LOG_QUEUE.put(log_entry)


def process_queue():
    """
    Function to be called by the main Streamlit thread to process 
    logs from the queue and update st.session_state.
    """
    has_new_logs = False
    while not LOG_QUEUE.empty():
        try:
            log_entry = LOG_QUEUE.get_nowait()
            st.session_state.logs.append(log_entry)
            has_new_logs = True
        except queue.Empty:
            break
    
    if len(st.session_state.logs) > 100:
        st.session_state.logs = st.session_state.logs[-100:]
        
    return has_new_logs


def install_chrome():
    """Install Chrome on Streamlit Cloud"""
    try:
        add_log("🔧 Installing Chrome...")
        # Note: These subprocess calls often rely on apt-get, which can be inconsistent in cloud environments.
        subprocess.run(['apt-get', 'update'], check=True, capture_output=True)
        subprocess.run(['apt-get', 'install', '-y', 'wget'], check=True, capture_output=True)
        subprocess.run([
            'wget', '-q', '-O', '/tmp/google-chrome.pub', 'https://dl-ssl.google.com/linux/linux_signing_key.pub'
        ], check=True, capture_output=True)
        subprocess.run([
            'wget', 'https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb'
        ], check=True, capture_output=True)
        subprocess.run([
            'dpkg', '-i', './google-chrome-stable_current_amd64.deb'
        ], check=False, capture_output=True) 
        subprocess.run(['apt-get', 'install', '-f', '-y'], check=False, capture_output=True)

        add_log("✅ Chrome installed successfully (or installation attempted)!")
        return True
    except Exception as e:
        add_log(f"❌ Chrome installation failed: {str(e)}")
        return False

def setup_chrome_driver():
    """Setup Chrome driver for Streamlit Cloud with robust path handling."""
    try:
        chrome_options = Options()
        # Essential options for Streamlit Cloud/headless environment
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Ensure Chrome binary path is correct for many cloud providers
        chrome_path = '/usr/bin/google-chrome'
        if os.path.exists(chrome_path):
            chrome_options.binary_location = chrome_path
        
        # Use WebDriver Manager reliably for the Service object
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service as ChromeService
        
        service = ChromeService(ChromeDriverManager().install())
        
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        add_log("✅ ChromeDriver setup completed and browser launched!")
        return driver
        
    except Exception as e:
        add_log(f"❌ ChromeDriver setup failed. Check Chrome binary/dependencies: {str(e)}")
        # If it fails, log the full path check for better diagnosis
        if not os.path.exists('/usr/bin/google-chrome'):
             add_log("⚠️ Critical: Chrome binary not found at expected path: /usr/bin/google-chrome")
        return None


def parse_cookies(cookie_string):
    """Parse cookies from various formats"""
    cookies = []
    try:
        # Try JSON format first
        if cookie_string.strip().startswith('[') or cookie_string.strip().startswith('{'):
            cookie_data = json.loads(cookie_string)
            return cookie_data if isinstance(cookie_data, list) else [cookie_data]
        
        # Parse different delimited formats
        cookie_pairs = []
        if ';' in cookie_string:
            cookie_pairs = cookie_string.split(';')
        elif '\n' in cookie_string or '\r' in cookie_string:
            cookie_pairs = cookie_string.replace('\r\n', '\n').split('\n')
        elif ',' in cookie_string and '=' in cookie_string:
            cookie_pairs = cookie_string.split(',')
        else:
            cookie_pairs = [cookie_string]
        
        for pair in cookie_pairs:
            pair = pair.strip()
            if '=' in pair and pair:
                key, value = pair.split('=', 1)
                cookies.append({
                    'name': key.strip(), 
                    'value': value.strip(), 
                    'domain': '.facebook.com'
                })
        return cookies
    except Exception as e:
        add_log(f"❌ Cookie parsing error: {str(e)}")
        return []

# ============================================
# AUTOMATION FUNCTION (Runs in background thread)
# ============================================

def run_automation(cookies_str, messages, thread_id, delay):
    """
    Main automation function.
    This runs inside a separate thread, so it MUST NOT directly call st.session_state.
    """
    is_stop_requested = False
    
    driver = None
    try:
        add_log("🚀 Starting automation...")
        add_log("⚙️ Setting up Chrome browser...")
        
        if st.session_state.stop_requested:
            add_log("⏹️ Automation cancelled before start by user.")
            return

        # Install Chrome if needed (This relies on external tools/permissions)
        if not os.path.exists('/usr/bin/google-chrome'):
            add_log("⚠️ Chrome not found. Attempting installation...")
            if not install_chrome():
                add_log("❌ Chrome installation failed. Cannot proceed.")
                return
        
        driver = setup_chrome_driver()
        if not driver:
            add_log("❌ Chrome setup failed. Check logs for details.")
            return
            
        add_log("✅ Chrome setup completed!")
        
        add_log("🌐 Navigating to Facebook...")
        driver.get("https://www.facebook.com")
        time.sleep(3)
        
        add_log(f"📄 Page loaded: {driver.title[:50]}")
        
        # Parse and add cookies
        cookies = parse_cookies(cookies_str)
        if not cookies:
            add_log("❌ Failed to parse cookies")
            return
        
        add_log(f"🍪 Adding {len(cookies)} cookies...")
        for cookie in cookies:
            try:
                # Add necessary attributes if missing for driver.add_cookie
                cookie_to_add = {
                    'name': cookie['name'],
                    'value': cookie['value'],
                    'domain': cookie.get('domain', '.facebook.com'),
                    'path': cookie.get('path', '/')
                }
                driver.add_cookie(cookie_to_add)
                add_log(f"✅ Cookie: {cookie['name'][:20]} added.")
            except Exception as e:
                add_log(f"⚠️ Cookie failed: {cookie.get('name', 'unknown')}. Error: {str(e)[:50]}")
        
        # Navigate to conversation
        thread_url = f"https://www.facebook.com/messages/t/{thread_id}"
        add_log(f"💬 Opening conversation: {thread_id}")
        driver.get(thread_url)
        time.sleep(5)
        
        add_log(f"🔗 Current URL: {driver.current_url}")
        if "login" in driver.current_url.lower():
            add_log("❌ Login page detected! Cookies are likely invalid or expired.")
            return
        
        # Process messages
        message_list = [msg.strip() for msg in messages.split('\n') if msg.strip()]
        add_log(f"📝 Messages to send: {len(message_list)}")
        
        selectors = [
            'div[contenteditable="true"][role="textbox"]',
            'div[aria-label*="message" i][contenteditable="true"]',
            'div[data-lexical-editor="true"]',
            'div.notranslate[contenteditable="true"]',
            'div[contenteditable="true"]',
            'textarea[placeholder*="message" i]',
            'div[role="textbox"]',
            'div[aria-label*="Type a message" i]'
        ]
        
        for idx, message in enumerate(message_list, 1):
            if st.session_state.stop_requested:
                add_log("⏹️ Stopped by user")
                is_stop_requested = True
                break
            
            try:
                add_log(f"🎯 Message {idx}/{len(message_list)}")
                
                # Find message input
                message_input = None
                for selector in selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            message_input = elements[0]
                            break
                    except:
                        continue
                
                if not message_input:
                    add_log("❌ Message input not found. Skipping message.")
                    continue
                
                # Type message
                message_input.click()
                time.sleep(1)
                
                # Use execute_script to ensure the element is focusable and clearable (robustness)
                driver.execute_script("arguments[0].textContent = '';", message_input)
                time.sleep(0.5)
                
                # Type new message
                message_input.send_keys(message)
                time.sleep(1)
                
                # Send (Keys.RETURN is the most reliable way in Messenger)
                add_log("📤 Sending...")
                message_input.send_keys(Keys.RETURN)
                
                add_log(f"✅ Message {idx} sent!")
                time.sleep(delay)
                
            except Exception as e:
                add_log(f"❌ Error during message send: {str(e)[:100]}")
                time.sleep(2)
                continue
        
        if not is_stop_requested:
            add_log("🎉 Automation completed!")
        
    except Exception as e:
        add_log(f"❌ Critical error during run: {str(e)[:100]}")
    
    finally:
        if driver:
            try:
                driver.quit()
                add_log("🔒 Browser closed")
            except:
                pass
        
        # Signal the main thread that the worker is finished
        LOG_QUEUE.put("---THREAD_FINISHED---") 


def start_automation_thread(cookies, messages, thread_id, delay):
    """Start automation in background thread"""
    def wrapper():
        run_automation(cookies, messages, thread_id, delay)
    
    st.session_state.is_running = True 
    st.session_state.stop_requested = False
    
    thread = threading.Thread(target=wrapper, daemon=True)
    thread.start()
    st.session_state.automation_thread = thread
    
    st.experimental_rerun() 

# ============================================
# MAIN UI
# ============================================

def main():
    
    rerun_needed = process_queue()
    
    if st.session_state.logs and st.session_state.logs[-1] == "---THREAD_FINISHED---":
        st.session_state.logs.pop() 
        st.session_state.is_running = False 
        st.experimental_rerun() 
        return
        
    
    st.title("🤖 Facebook Messenger Automation Bot")
    
    # Status display
    col1, col2 = st.columns(2)
    with col1:
        if st.session_state.is_running:
            st.markdown('<p class="status-running">🟢 RUNNING</p>', unsafe_allow_html=True)
        else:
            st.markdown('<p class="status-stopped">🔴 STOPPED</p>', unsafe_allow_html=True)
    
    with col2:
        if st.session_state.is_running:
            if st.button("⏹️ Stop Bot", key="stop_btn"):
                st.session_state.stop_requested = True
                st.session_state.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] AUTO-1: 🛑 Stop requested") 
                st.experimental_rerun()
    
    # Configuration
    st.markdown('<div class="config-section">', unsafe_allow_html=True)
    st.subheader("⚙️ Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        thread_id = st.text_input(
            "💬 Thread ID", 
            placeholder="1234567890",
            help="Find in URL: /messages/t/[THREAD_ID]",
            key="thread_id" 
        )
        
        delay = st.number_input(
            "⏰ Delay (seconds)", 
            min_value=1, 
            max_value=60, 
            value=3,
            key="delay" 
        )
    
    with col2:
        messages = st.text_area(
            "📝 Messages (one per line)",
            height=150,
            placeholder="Hello!\nHow are you?\nAutomated message",
            key="messages_input"
        )
    
    # Cookies (full width)
    cookies = st.text_area(
        "🍪 Facebook Cookies (All Formats Supported)", 
        height=100,
        placeholder="JSON: [{\"name\":\"c_user\",\"value\":\"123\",...}]\nSemicolon: c_user=123; xs=abc\nNewline: one per line",
        help="Supports: JSON, semicolon-delimited, newline-separated",
        key="cookies_input" 
    )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Start button
    if not st.session_state.is_running:
        if st.button("🚀 Start Automation", key="start_btn"):
            if not thread_id:
                st.error("❌ Enter Thread ID")
            elif not messages.strip():
                st.error("❌ Enter Messages")
            elif not cookies.strip():
                st.error("❌ Enter Cookies")
            else:
                st.session_state.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] AUTO-1: 🎬 Starting...")
                start_automation_thread(cookies, messages, thread_id, delay)
    
    # Logs
    st.subheader("📊 Live Logs")
    
    if st.session_state.is_running:
        time.sleep(1)
        st.experimental_rerun()
    elif rerun_needed:
         st.experimental_rerun()

    
    if st.session_state.logs:
        log_html = '<div class="log-container">'
        for log in reversed(st.session_state.logs[-50:]):
            log_html += f'<div class="log-entry">{log}</div>'
        log_html += '</div>'
        st.markdown(log_html, unsafe_allow_html=True)
    else:
        st.info("📝 Logs will appear here...")
    
    # Clear logs
    if st.session_state.logs:
        if st.button("🗑️ Clear Logs"):
            st.session_state.logs = []
            st.experimental_rerun()
    
    # Instructions (No changes here)
    with st.expander("📖 Instructions"):
        st.markdown("""
        ### How to Use:
        
        1. **Get Cookies:**
           - Login to Facebook
           - F12 > Application > Cookies > facebook.com
           - Copy all cookies (especially `c_user` and `xs`)
        
        2. **Find Thread ID:**
           - Open Messenger conversation
           - Copy ID from URL: `/messages/t/[ID]`
        
        3. **Configure:**
           - Paste cookies (any format)
           - Enter messages (one per line)
           - Set delay (3-5 sec recommended)
        
        4. **Start:**
           - Click "Start Automation"
           - Monitor logs closely.
        
        ### Note:
        If messages still fail, check the logs for:
        - **"❌ Login page detected!"**: Cookies are bad.
        - **"❌ Message input not found"**: Facebook's layout changed.
        """)

if __name__ == "__main__":
    main()
