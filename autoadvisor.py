# fastapi-service/auto_advisor.py
# AutoAdvisor that pauses and waits for PIN from API

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import Dict, Any, Optional
import logging
import time

logger = logging.getLogger(__name__)


class AutoAdvisor:
    """
    AutoAdvisor that integrates with API for two-step authentication
    
    This version is designed to work with the FastAPI two-step flow:
    1. Start with username/password
    2. Pause when PIN is needed
    3. Resume when PIN is provided via API
    """
    
    def __init__(self):
        self.driver = None
        self.state = "initialized"
        self.username = None
        self.password = None
        self.pin = None
    
    def fetch_transcript(self, username: str, password: str, pin: str) -> Dict[str, Any]:
        """
        Complete flow: Login with username/password, enter PIN, fetch transcript
        
        This is called by the API after receiving the PIN from the user
        
        Args:
            username: VSU email/username
            password: VSU password
            pin: 4-digit PIN for 2FA
        
        Returns:
            Transcript data as JSON dictionary
        """
        self.username = username
        self.password = password
        self.pin = pin
        
        try:
            logger.info("Starting transcript fetch process")
            
            # Step 1: Initialize browser
            self._initialize_browser()
            
            # Step 2: Navigate to portal
            self._navigate_to_portal()
            
            # Step 3: Login with username/password
            self._login(username, password)
            
            # Step 4: Handle 2FA (PIN entry)
            self._enter_pin(pin)
            
            # Step 5: Navigate to transcript page
            self._navigate_to_transcript()
            
            # Step 6: Download/extract transcript data
            transcript_data = self._extract_transcript()
            
            # Step 7: Parse transcript into JSON
            json_data = self._parse_transcript(transcript_data)
            
            logger.info("Transcript fetched successfully")
            return json_data
        
        except Exception as e:
            logger.error(f"Error fetching transcript: {str(e)}")
            raise
        
        finally:
            # Clean up browser
            if self.driver:
                self.driver.quit()
    
    def _initialize_browser(self):
        """Initialize Chrome browser with Selenium"""
        logger.info("Initializing browser")
        
        options = webdriver.ChromeOptions()
        # options.add_argument('--headless')  # Run without GUI
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        self.driver = webdriver.Chrome(options=options)
        self.state = "browser_ready"
    
    def _navigate_to_portal(self):
        """Navigate to VSU portal"""
        logger.info("Navigating to VSU portal")
        
        portal_url = "https://portal.vsu.edu"  # Replace with actual URL
        self.driver.get(portal_url)
        self.state = "at_portal"
        
        # Wait for page to load
        time.sleep(2)
    
    def _login(self, username: str, password: str):
        """Login with username and password"""
        logger.info(f"Logging in as: {username}")
        
        try:
            # Wait for username field
            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            username_field.send_keys(username)
            
            # Enter password
            password_field = self.driver.find_element(By.ID, "password")
            password_field.send_keys(password)
            
            # Click login button
            login_button = self.driver.find_element(By.ID, "submit")
            login_button.click()
            
            self.state = "logged_in"
            logger.info("Login successful")
            
            # Wait for next page
            time.sleep(3)
        
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            raise Exception("Login failed - check credentials")
    
    def _enter_pin(self, pin: str):
        """
        Enter 4-digit PIN for 2FA
        
        This is where AutoAdvisor was "paused" waiting for user to provide PIN
        Now the API has provided the PIN, so we can continue
        """
        logger.info("Entering PIN for 2FA")
        
        try:
            # Wait for PIN field to appear
            pin_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "pin"))
            )
            pin_field.send_keys(pin)
            
            # Click submit
            submit_button = self.driver.find_element(By.ID, "pin-submit")
            submit_button.click()
            
            self.state = "pin_entered"
            logger.info("PIN entered successfully")
            
            # Wait for authentication
            time.sleep(3)
        
        except Exception as e:
            logger.error(f"PIN entry failed: {str(e)}")
            raise Exception("PIN entry failed - invalid PIN or timeout")
    
    def _navigate_to_transcript(self):
        """Navigate to transcript page"""
        logger.info("Navigating to transcript")
        
        try:
            # Find and click transcript link
            transcript_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Transcript"))
            )
            transcript_link.click()
            
            self.state = "at_transcript"
            logger.info("At transcript page")
            
            # Wait for page to load
            time.sleep(3)
        
        except Exception as e:
            logger.error(f"Navigation failed: {str(e)}")
            raise Exception("Could not navigate to transcript")
    
    def _extract_transcript(self) -> str:
        """Extract transcript HTML/text from page"""
        logger.info("Extracting transcript data")
        
        try:
            # Wait for transcript content
            transcript_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "transcript-content"))
            )
            
            # Get transcript HTML
            transcript_html = transcript_element.get_attribute('innerHTML')
            
            self.state = "transcript_extracted"
            logger.info("Transcript extracted successfully")
            
            return transcript_html
        
        except Exception as e:
            logger.error(f"Extraction failed: {str(e)}")
            raise Exception("Could not extract transcript data")
    
    def _parse_transcript(self, html: str) -> Dict[str, Any]:
        """
        Parse HTML transcript into structured JSON
        
        This is where you'd parse the actual transcript HTML/PDF
        into the structured format needed
        """
        logger.info("Parsing transcript into JSON")
        
        # In real implementation, parse HTML here
        # For now, return structured data
        
        transcript_json = {
            "student_id": "V123456789",
            "name": self.username.split('@')[0].title(),  # Extract from email
            "advisor": "Dr. Smith",
            "gpa": 3.75,
            "total_credits": 115,
            "transcript": {
                "freshman_1": [
                    {
                        "name": "Intro to CS Profession",
                        "course_code": "CSCI 101",
                        "grade": "A",
                        "credits": 2.0,
                        "semester": "FA22",
                        "notes": None
                    },
                    {
                        "name": "Programming Fundamentals",
                        "course_code": "CSCI 112",
                        "grade": "B",
                        "credits": 3.0,
                        "semester": "FA22",
                        "notes": None
                    }
                ],
                "freshman_2": [
                    {
                        "name": "Data Structures",
                        "course_code": "CSCI 211",
                        "grade": "A",
                        "credits": 3.0,
                        "semester": "SP23",
                        "notes": None
                    }
                ],
                "sophomore_1": [],
                "sophomore_2": [],
                "junior_1": [],
                "junior_2": [],
                "senior_1": [],
                "senior_2": []
            }
        }
        
        self.state = "completed"
        logger.info("Parsing complete")
        
        return transcript_json


# ============================================================
# INTEGRATION WITH FASTAPI
# ============================================================

def fetch_transcript_with_api(username: str, password: str, pin: str) -> Dict[str, Any]:
    """
    Wrapper function called by FastAPI endpoint
    
    This is what the API calls in resume_autoadvisor()
    
    Args:
        username: VSU username
        password: VSU password  
        pin: 4-digit PIN from user
    
    Returns:
        Transcript JSON data
    """
    advisor = AutoAdvisor()
    return advisor.fetch_transcript(username, password, pin)


# ============================================================
# EXAMPLE: HOW IT WORKS
# ============================================================

"""
COMPLETE FLOW EXAMPLE:

1. USER → API: "I want my transcript"
   POST /api/fetch-transcript
   {"username": "jdoe@vsu.edu", "password": "pass123"}

2. API → USER: "I need your PIN"
   Response: {"session_id": "abc123", "awaiting_pin": true}

3. USER → API: "Here's my PIN"
   POST /api/submit-pin
   {"session_id": "abc123", "pin": "1234"}

4. API → AUTOADVISOR: "Start with these credentials + PIN"
   fetch_transcript_with_api("jdoe@vsu.edu", "pass123", "1234")

5. AUTOADVISOR:
   - Opens browser
   - Goes to portal
   - Enters username/password
   - Enters PIN (NOW HAS IT FROM API!)
   - Downloads transcript
   - Parses into JSON
   - Returns data

6. API → USER: "Here's your transcript"
   Response: {"success": true, "transcript_data": {...}}


KEY POINT:
AutoAdvisor doesn't actually "pause" in the code.
Instead:
- First API call creates a session and returns
- Second API call (with PIN) starts AutoAdvisor fresh
- AutoAdvisor runs completely with all credentials at once
- This appears as a "pause and resume" to the user
"""