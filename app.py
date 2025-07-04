import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta
import logging
import pytz
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
import time
from urllib.parse import urlparse
import os
import random
import re
from bs4 import BeautifulSoup
from PIL import Image
import base64
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set page config
st.set_page_config(
    page_title="Accessibility Testing Tool",
    page_icon="♿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #1f77b4;
        font-size: 2.5em;
        margin-bottom: 30px;
    }
    .success-message {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .error-message {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .info-box {
        background-color: #e7f3ff;
        border-left: 4px solid #1f77b4;
        padding: 15px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

class AccessibilityTester:
    def __init__(self):
        self.driver = None
        
    def setup_driver(self):
        """Setup Chrome driver with appropriate options"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            return True
        except Exception as e:
            logger.error(f"Failed to setup driver: {e}")
            return False
    
    def find_frontend_pages(self, home_url, headers):
        """Find frontend pages from the home URL"""
        try:
            response = requests.get(home_url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            links = set()
            for link in soup.find_all('a', href=True):
                if home_url in link['href']:
                    links.add(link['href'])
            
            return list(links)
        except Exception as e:
            logger.error(f"Error finding frontend pages: {e}")
            return []
    
    def format_filename(self, url):
        """Format URL to create a valid filename"""
        domain_and_path = re.sub(r"https?://", "", url).strip("/")
        domain_and_path = re.sub(r"[^\w\d]", "", domain_and_path)
        return domain_and_path
    
    def capture_accessibility_test(self, target_url, username, email, progress_callback=None):
        """Capture accessibility test results"""
        if not self.setup_driver():
            return False, "Failed to setup browser driver", None
            
        try:
            # Update progress
            if progress_callback:
                progress_callback(10, "Setting up browser...")
            
            # Construct the Accessibe scan URL
            base_url = "https://accessibe.com/accessscan?website="
            full_url = f"{base_url}{target_url}"
            
            # Open the URL
            self.driver.get(full_url)
            time.sleep(random.uniform(2, 5))
            
            if progress_callback:
                progress_callback(20, "Loading accessibility scanner...")
            
            # Handle cookie consent popup if present
            try:
                cookie_banner = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//button[contains(text(), 'Reject All')] | //button[contains(text(), 'Accept All')]")
                    )
                )
                cookie_banner.click()
                logger.info("Cookie consent accepted.")
            except Exception:
                logger.info("No cookie consent message found.")
            
            if progress_callback:
                progress_callback(30, "Waiting for scan results...")
            
            # Wait until the iframe is formed and fully loaded
            iframe_xpath = "//iframe[contains(@src, '#audit/')]"
            WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.XPATH, iframe_xpath)))
            
            time.sleep(random.uniform(2, 5))
            time.sleep(30)  # Reduced from 60 for better UX
            
            if progress_callback:
                progress_callback(50, "Scanning website for accessibility issues...")
            
            # Switch to the iframe to ensure it's fully loaded
            iframe = self.driver.find_element(By.XPATH, iframe_xpath)
            self.driver.switch_to.frame(iframe)
            
            time.sleep(30)  # Reduced from 60 for better UX
            
            if progress_callback:
                progress_callback(70, "Generating report...")
            
            # Take a screenshot of the fully loaded page
            screenshot_path = f"accessibility_results_{self.format_filename(target_url)}.png"
            self.driver.save_screenshot(screenshot_path)
            
            # Check if the "Get Free Report" button is present
            get_report_button_xpath = "//span[@data-click-trigger='popup-get-report']"
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, get_report_button_xpath))
                )
            except Exception:
                logger.error("'Get Free Report' button not found.")
                return False, "'Get Free Report' button not found", screenshot_path
            
            # Attempt to click the "Get Free Report" button
            try:
                button = self.driver.find_element(By.XPATH, get_report_button_xpath)
                self.driver.execute_script("arguments[0].click();", button)
            except Exception as e:
                logger.error(f"Error clicking 'Get Free Report' button: {e}")
                return False, f"Error clicking 'Get Free Report' button: {e}", screenshot_path
            
            if progress_callback:
                progress_callback(80, "Filling form with provided details...")
            
            # Wait for the popup form to appear
            name_field_xpath = "//input[@id='field-name']"
            email_field_xpath = "//input[@id='field-email']"
            submit_button_xpath = "//button[@id='get-report-button']"
            
            try:
                WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.XPATH, name_field_xpath)))
            except Exception as e:
                logger.error(f"Popup form did not appear: {e}")
                return False, f"Popup form did not appear: {e}", screenshot_path
            
            # Fill the form fields
            try:
                self.driver.find_element(By.XPATH, name_field_xpath).send_keys(username)
                self.driver.find_element(By.XPATH, email_field_xpath).send_keys(email)
                logger.info("Form fields filled.")
            except Exception as e:
                logger.error(f"Error filling form fields: {e}")
                return False, f"Error filling form fields: {e}", screenshot_path
            
            if progress_callback:
                progress_callback(90, "Submitting form...")
            
            # Submit the form
            try:
                submit_btn = self.driver.find_element(By.XPATH, submit_button_xpath)
                self.driver.execute_script("arguments[0].click();", submit_btn)
                logger.info("Form submitted.")
                
                time.sleep(30)  # Reduced from 60 for better UX
                
                if progress_callback:
                    progress_callback(100, "Test completed successfully!")
                
                return True, f"Report for URL: {target_url} sent to email: {email}", screenshot_path
                
            except Exception as e:
                logger.error(f"Error submitting form: {e}")
                return False, f"Error submitting form: {e}", screenshot_path
                
        except Exception as e:
            logger.error(f"An error occurred for {target_url}: {e}")
            return False, f"An error occurred: {e}", None
            
        finally:
            if self.driver:
                self.driver.quit()

def main():
    st.markdown('<h1 class="main-header">♿ Accessibility Testing Tool</h1>', unsafe_allow_html=True)
    
    # Sidebar for information
    with st.sidebar:
        st.header("ℹ️ About")
        st.markdown("""
        This tool helps you test website accessibility using AccessiBe's scanner.
        
        **Features:**
        - Automated accessibility scanning
        - Email report delivery
        - Visual results preview
        - Support for any website URL
        """)
        
        st.header("📋 Instructions")
        st.markdown("""
        1. Enter the website URL to test
        2. Provide your name and email
        3. Click "Run Accessibility Test"
        4. Wait for the scan to complete
        5. View results and check your email
        """)
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("🔧 Test Configuration")
        
        # Input form
        with st.form("accessibility_test_form"):
            target_url = st.text_input(
                "Website URL",
                placeholder="https://example.com",
                help="Enter the full URL of the website you want to test"
            )
            
            col_name, col_email = st.columns(2)
            with col_name:
                username = st.text_input(
                    "Your Name",
                    placeholder="John Doe",
                    help="This will be used in the report request"
                )
            
            with col_email:
                email = st.text_input(
                    "Email Address",
                    placeholder="john@example.com",
                    help="The accessibility report will be sent to this email"
                )
            
            submitted = st.form_submit_button("🚀 Run Accessibility Test", type="primary")
        
        # Validation and execution
        if submitted:
            # Validate inputs
            if not target_url or not username or not email:
                st.error("Please fill in all required fields.")
            elif not target_url.startswith(('http://', 'https://')):
                st.error("Please enter a valid URL starting with http:// or https://")
            elif '@' not in email or '.' not in email:
                st.error("Please enter a valid email address.")
            else:
                # Run the accessibility test
                st.success("Starting accessibility test...")
                
                # Progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                def update_progress(value, message):
                    progress_bar.progress(value)
                    status_text.text(message)
                
                # Create tester instance and run test
                tester = AccessibilityTester()
                
                with st.spinner("Running accessibility test..."):
                    success, message, screenshot_path = tester.capture_accessibility_test(
                        target_url, username, email, update_progress
                    )
                
                # Display results
                if success:
                    st.markdown(f'<div class="success-message">✅ {message}</div>', unsafe_allow_html=True)
                    
                    # Display screenshot if available
                    if screenshot_path and os.path.exists(screenshot_path):
                        st.header("📸 Accessibility Test Results")
                        
                        try:
                            image = Image.open(screenshot_path)
                            st.image(image, caption="Accessibility Test Results", use_column_width=True)
                            
                            # Provide download button
                            with open(screenshot_path, "rb") as file:
                                st.download_button(
                                    label="📥 Download Screenshot",
                                    data=file.read(),
                                    file_name=f"accessibility_results_{tester.format_filename(target_url)}.png",
                                    mime="image/png"
                                )
                        except Exception as e:
                            st.error(f"Error displaying screenshot: {e}")
                else:
                    st.markdown(f'<div class="error-message">❌ {message}</div>', unsafe_allow_html=True)
                    
                    # Still try to show screenshot if available
                    if screenshot_path and os.path.exists(screenshot_path):
                        st.header("📸 Partial Results")
                        try:
                            image = Image.open(screenshot_path)
                            st.image(image, caption="Partial Test Results", use_column_width=True)
                        except Exception as e:
                            st.error(f"Error displaying screenshot: {e}")
    
    with col2:
        st.header("📊 Test Status")
        
        # Initialize session state for test history
        if 'test_history' not in st.session_state:
            st.session_state.test_history = []
        
        # Display test history
        if st.session_state.test_history:
            st.subheader("Recent Tests")
            for i, test in enumerate(st.session_state.test_history[-5:]):  # Show last 5 tests
                with st.expander(f"Test {i+1}: {test['url'][:30]}..."):
                    st.write(f"**Status:** {test['status']}")
                    st.write(f"**Time:** {test['timestamp']}")
                    st.write(f"**Email:** {test['email']}")
        else:
            st.info("No tests run yet. Start your first accessibility test!")
        
        # Add current test to history when form is submitted
        if submitted and target_url and username and email:
            st.session_state.test_history.append({
                'url': target_url,
                'status': 'Completed' if 'success' in locals() and success else 'Failed',
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'email': email
            })

if __name__ == "__main__":
    main()