#!/usr/bin/env python3
"""
Facebook Messenger Automation Bot - Streamlit Cloud Version
"""

import streamlit as st
import json
import time
import threading
import os
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
# >>> बदलाव 1: यहां 'key' को initialize किया गया है ताकि पिछली AttributeError ठीक हो जाए। <<<
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
    # अनपेक्षित 'key' एरर को संभालने के लिए
    if 'key' not in st.session_state: 
        st.session_state.key = None 

# Initialize session state at startup
init_session_state()

# ============================================
# HELPER FUNCTIONS
# ============================================

def add_log(message):
    """Add a timestamped log entry"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] AUTO-1: {message}"
    st.session_state.logs.append(log_entry)
    if len(st.session_state.logs) > 100:
        st.session_state.logs = st.session_state.logs[-100:]

def install_chrome():
    """Install Chrome on Streamlit Cloud"""
    try:
        add_log("🔧 Installing Chrome...")
        # Install Chrome (Streamlit Cloud-specific steps)
        # Note: In newer versions, Streamlit Cloud often pre-installs Chrome/Chromium.
        # This function might still be needed for older environments or specific needs.
        subprocess.run(['apt-get', 'update'], check=True, capture_output=True)
        subprocess.run(['apt-get', 'install', '-y', 'wget'], check=True, capture_output=True)
        
        # Download and install Chrome
        subprocess.run([
            'wget', '-q', '-O', '/tmp/google-chrome.pub', 'https://dl-ssl.google.com/linux/linux_signing_key.pub'
        ], check=True, capture_output=True)
        
        subprocess.run([
            'wget', 'https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb'
        ], check=True, capture_output=True)
        
        subprocess.run([
            'dpkg', '-i', './google-chrome-stable_current_amd64.deb'
        ], check=False, capture_output=True) # Use dpkg -i for better error handling on dependencies
        
        # Fixing potential broken dependencies
        subprocess.run(['apt-get', 'install', '-f', '-y'], check=False, capture_output=True)

        add_log("✅ Chrome installed successfully (or installation attempted)!")
        return True
    except Exception as e:
        add_log(f"❌ Chrome installation failed: {str(e)}")
        return False

def setup_chrome_driver():
    """Setup Chrome driver for Streamlit Cloud"""
    try:
        # Chrome options for cloud environment
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Use system Chrome
        chrome_options.binary_location = '/usr/bin/google-chrome'
        
        # Setup service
        # Using a more robust check for chromedriver location
        driver_path = '/usr/bin/chromedriver'
        if not os.path.exists(driver_path):
             add_log("⚠️ ChromeDriver not found at default location. Trying webdriver-manager...")
             from webdriver_manager.chrome import ChromeDriverManager
             from selenium.webdriver.chrome.service import Service as ChromeService
             service = ChromeService(ChromeDriverManager().install())
        else:
             service = Service(executable_path=driver_path)

        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        add_log("✅ ChromeDriver setup completed!")
        return driver
        
    except Exception as e:
        add_log(f"❌ ChromeDriver setup failed: {str(e)}")
        return None

def parse_cookies(cookie_string):
    """Parse cookies from various formats - JSON, semicolon, newline"""
    # (आपका पुराना फ़ंक्शन)
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
# AUTOMATION FUNCTION
# ============================================

def run_automation(cookies_str, messages, thread_id, delay):
    """Main automation function"""
    # >>> बदलाव 2: Threds के अंदर st.session_state को केवल तभी अपडेट करें जब ज़रूरी हो. <<<
    # is_running को wrapper में सेट किया गया है, लेकिन यहां भी सेट किया जा सकता है.
    st.session_state.stop_requested = False
    
    driver = None
    try:
        # ... (rest of your run_automation function remains the same) ...
        add_log("🚀 Starting automation...")
        add_log("⚙️ Setting up Chrome browser...")
        
        # Install Chrome if needed
        if not os.path.exists('/usr/bin/google-chrome'):
            if not install_chrome():
                add_log("❌ Chrome installation required but failed")
                return
        
        driver = setup_chrome_driver()
        if not driver:
            add_log("❌ Chrome setup failed")
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
                driver.add_cookie(cookie)
                add_log(f"✅ Cookie: {cookie['name'][:20]}")
            except Exception as e:
                add_log(f"⚠️ Cookie failed: {cookie.get('name', 'unknown')}")
        
        # Navigate to conversation
        thread_url = f"https://www.facebook.com/messages/t/{thread_id}"
        add_log(f"💬 Opening conversation: {thread_id}")
        driver.get(thread_url)
        time.sleep(5)
        
        add_log(f"🔗 URL: {driver.current_url}")
        
        # Process messages
        message_list = [msg.strip() for msg in messages.split('\n') if msg.strip()]
        add_log(f"📝 Messages to send: {len(message_list)}")
        
        # Enhanced selectors
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
                break
            
            try:
                add_log(f"🎯 Message {idx}/{len(message_list)}")
                
                # Find message input
                message_input = None
                for sel_idx, selector in enumerate(selectors, 1):
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            add_log(f'✅ Selector {sel_idx}: {len(elements)} found')
                            message_input = elements[0]
                            break
                    except:
                        continue
                
                if not message_input:
                    add_log("❌ Message input not found")
                    continue
                
                # Type message
                add_log(f"⌨️ Typing: {message[:50]}...")
                message_input.click()
                time.sleep(1)
                
                # Clear existing
                message_input.send_keys(Keys.CONTROL + "a")
                time.sleep(0.5)
                message_input.send_keys(Keys.DELETE)
                time.sleep(0.5)
                
                # Type new message
                message_input.send_keys(message)
                time.sleep(1)
                
                # Send
                add_log("📤 Sending...")
                message_input.send_keys(Keys.RETURN)
                
                add_log(f"✅ Message {idx} sent!")
                time.sleep(delay)
                
            except Exception as e:
                add_log(f"❌ Error: {str(e)[:100]}")
                time.sleep(2)
                continue
        
        add_log("🎉 Automation completed!")
        
    except Exception as e:
        add_log(f"❌ Critical error: {str(e)[:100]}")
    
    finally:
        if driver:
            try:
                driver.quit()
                add_log("🔒 Browser closed")
            except:
                pass
        # >>> बदलाव 3: Automation खत्म होने पर is_running को False सेट करें <<<
        st.session_state.is_running = False
        st.experimental_rerun() # काम पूरा होने पर UI को एक बार अपडेट करें


def start_automation_thread(cookies, messages, thread_id, delay):
    """Start automation in background thread"""
    def wrapper():
        st.session_state.is_running = True # Automation शुरू होने पर True सेट करें
        run_automation(cookies, messages, thread_id, delay)
    
    thread = threading.Thread(target=wrapper, daemon=True)
    thread.start()
    st.session_state.automation_thread = thread
    # thread शुरू करने के बाद ही UI को अपडेट करने के लिए rerun करें
    st.experimental_rerun() 

# ============================================
# MAIN UI
# ============================================

def main():
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
                add_log("🛑 Stop requested")
                # Stop request के बाद rerun ज़रूरी नहीं है, क्योंकि thread खुद रुक जाएगा
    
    # Configuration
    st.markdown('<div class="config-section">', unsafe_allow_html=True)
    st.subheader("⚙️ Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # >>> बदलाव 4: Text Input Widgets में key="thread_id" और key="delay" जोड़ा गया है। <<<
        # यह सुनिश्चित करता है कि ये Widgets Session State में सही से ट्रैक किए जा सकें।
        thread_id = st.text_input(
            "💬 Thread ID", 
            placeholder="1234567890",
            help="Find in URL: /messages/t/[THREAD_ID]",
            key="thread_id" # Key added
        )
        
        delay = st.number_input(
            "⏰ Delay (seconds)", 
            min_value=1, 
            max_value=60, 
            value=3,
            key="delay" # Key added
        )
    
    with col2:
        # >>> बदलाव 5: Text Area Widget में key="messages_input" जोड़ा गया है। <<<
        messages = st.text_area(
            "📝 Messages (one per line)",
            height=150,
            placeholder="Hello!\nHow are you?\nAutomated message",
            key="messages_input" # Key added
        )
    
    # Cookies (full width)
    # >>> बदलाव 6: Cookies Widget में key="cookies_input" जोड़ा गया है। <<<
    cookies = st.text_area(
        "🍪 Facebook Cookies (All Formats Supported)", 
        height=100,
        placeholder="JSON: [{\"name\":\"c_user\",\"value\":\"123\",...}]\nSemicolon: c_user=123; xs=abc\nNewline: one per line",
        help="Supports: JSON, semicolon-delimited, newline-separated",
        key="cookies_input" # Key added
    )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Start button
    if not st.session_state.is_running:
        if st.button("🚀 Start Automation", key="start_btn"):
            # Validation using the widget values
            if not thread_id:
                st.error("❌ Enter Thread ID")
            elif not messages.strip():
                st.error("❌ Enter Messages")
            elif not cookies.strip():
                st.error("❌ Enter Cookies")
            else:
                add_log("🎬 Starting...")
                # Start the thread
                start_automation_thread(cookies, messages, thread_id, delay)
                # start_automation_thread के अंदर st.experimental_rerun() जोड़ा गया है
    
    # Logs
    st.subheader("📊 Live Logs")
    
    # >>> बदलाव 7: Live Log अपडेट के लिए st.rerun() को सरल बनाया गया है <<<
    # Automation के दौरान logs को हर 1 सेकंड में अपडेट करने के लिए
    if st.session_state.is_running:
        # UI को हर 1 सेकंड में अपडेट करने के लिए
        time.sleep(1)
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
    
    # Instructions
    with st.expander("📖 Instructions"):
        st.markdown("""
        ### How to Use:
        
        1. **Get Cookies:**
           - Login to Facebook
           - F12 > Application > Cookies > facebook.com
           - Copy all cookies
        
        2. **Find Thread ID:**
           - Open Messenger conversation
           - Copy ID from URL: `/messages/t/[ID]`
        
        3. **Configure:**
           - Paste cookies (any format)
           - Enter messages (one per line)
           - Set delay (3-5 sec recommended)
        
        4. **Start:**
           - Click "Start Automation"
           - Monitor logs
        
        ### Supported Cookie Formats:
        - **JSON:** `[{"name":"c_user","value":"123","domain":".facebook.com"}]`
        - **Semicolon:** `c_user=123; xs=abc; datr=xyz`
        - **Newline:** One cookie per line
        
        ### Note:
        First run may take longer as Chrome gets installed automatically.
        """)

if __name__ == "__main__":
    # >>> बदलाव 8: Streamlit Cloud पर subprocess/apt-get errors से बचने के लिए <<<
    # install_chrome() को main() के बाहर कॉल करने से बचें.
    main()
