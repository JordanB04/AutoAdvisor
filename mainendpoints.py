# fastapi-service/main.py
# FastAPI with Username/Password Authentication

from fastapi import FastAPI, HTTPException, Depends, Body, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, EmailStr, Field
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import secrets

from auto_advisor import AutoAdvisor

app = FastAPI(title="AutoAdvisor API with Authentication")
logger = logging.getLogger(__name__)

# HTTP Basic Auth setup
security = HTTPBasic()


# ============================================================
# AUTHENTICATION MODELS
# ============================================================

class LoginRequest(BaseModel):
    """Login with username and password"""
    username: str = Field(..., example="john.doe@vsu.edu")
    password: str = Field(..., example="SecurePass123!")


class LoginResponse(BaseModel):
    """Login response"""
    success: bool
    message: str
    username: str
    token: Optional[str] = None


# ============================================================
# DATA MODELS
# ============================================================

class Course(BaseModel):
    name: str
    grade: str
    credits: float
    semester: str
    notes: Optional[str] = None


class Transcript(BaseModel):
    freshman_1: List[Course] = []
    freshman_2: List[Course] = []
    sophomore_1: List[Course] = []
    sophomore_2: List[Course] = []
    junior_1: List[Course] = []
    junior_2: List[Course] = []
    senior_1: List[Course] = []
    senior_2: List[Course] = []


class StudentData(BaseModel):
    name: str
    student_id: str
    advisor: str
    transcript: Transcript


# ============================================================
# REQUEST/RESPONSE MODELS
# ============================================================

class AnalyzeRequest(BaseModel):
    """Request with username/password authentication"""
    username: str = Field(..., example="john.doe@vsu.edu")
    password: str = Field(..., example="SecurePass123!")
    pin: Optional[str] = Field(None, example="1234", description="Optional 4-digit PIN")
    student_data: StudentData
    additional_data: Optional[Dict[str, Any]] = Field(None, description="Optional JSON object for any extra data")
    prompt: Optional[str] = None


class AnalyzeResponse(BaseModel):
    success: bool
    message: str
    username: str
    gpa: float
    total_credits: float
    academic_standing: str
    recommendations: List[str]
    timestamp: str


# ============================================================
# AUTHENTICATION FUNCTIONS
# ============================================================

def verify_credentials(username: str, password: str, pin: Optional[str] = None) -> bool:
    """
    Verify username, password, and optional PIN
    
    In production, this would check against a database
    For now, simple validation
    """
    # Example validation rules
    if not username or not password:
        return False
    
    if len(password) < 8:
        return False
    
    # Validate PIN if provided
    if pin is not None:
        # PIN should be 4 digits
        if not pin.isdigit() or len(pin) != 4:
            return False
    
    # TODO: Add your actual authentication logic here
    # For example, check against database:
    # user = database.get_user(username)
    # if pin:
    #     return check_password_hash(user.password_hash, password) and user.pin == pin
    # return check_password_hash(user.password_hash, password)
    
    return True  # For demo purposes


def authenticate_user(username: str, password: str, pin: Optional[str] = None) -> Dict[str, Any]:
    """
    Authenticate user and return user info
    """
    if not verify_credentials(username, password, pin):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username, password, or PIN",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return {
        "username": username,
        "authenticated": True,
        "pin_verified": pin is not None,
        "timestamp": datetime.now().isoformat()
    }


# ============================================================
# METHOD 1: Username/Password in JSON Body
# ============================================================

@app.post("/api/login", response_model=LoginResponse)
def login(request: LoginRequest):
    """
    Login endpoint - accepts username and password in JSON
    
    Send this JSON:
    {
        "username": "john.doe@vsu.edu",
        "password": "SecurePass123!"
    }
    """
    logger.info(f"Login attempt for: {request.username}")
    
    try:
        # Authenticate
        user_info = authenticate_user(request.username, request.password)
        
        # Generate session token (simplified)
        token = secrets.token_urlsafe(32)
        
        return LoginResponse(
            success=True,
            message="Login successful",
            username=request.username,
            token=token
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze_with_auth(request: AnalyzeRequest):
    """
    Main endpoint - Username/Password/PIN included in request
    
    Send this JSON:
    {
        "username": "john.doe@vsu.edu",
        "password": "SecurePass123!",
        "pin": "1234",
        "student_data": {
            "name": "John Doe",
            "student_id": "V123456789",
            "advisor": "Dr. Smith",
            "transcript": {
                "freshman_1": [
                    {
                        "name": "Intro to CS",
                        "grade": "A",
                        "credits": 3.0,
                        "semester": "FA22",
                        "notes": null
                    }
                ],
                "freshman_2": [],
                "sophomore_1": [],
                "sophomore_2": [],
                "junior_1": [],
                "junior_2": [],
                "senior_1": [],
                "senior_2": []
            }
        },
        "additional_data": {
            "custom_field1": "value1",
            "custom_field2": 123,
            "nested_object": {
                "key": "value"
            }
        },
        "prompt": "What courses should I take?"
    }
    
    PIN is optional - omit it if not needed
    additional_data is optional - can contain any JSON structure
    """
    logger.info(f"Analyze request from: {request.username}")
    
    try:
        # Step 1: Authenticate (with optional PIN)
        auth_info = authenticate_user(request.username, request.password, request.pin)
        logger.info(f"Authentication successful. PIN verified: {auth_info['pin_verified']}")
        
        # Step 2: Process additional_data if provided
        if request.additional_data:
            logger.info(f"Additional data received: {list(request.additional_data.keys())}")
            # You can access any field in additional_data
            # Example: request.additional_data.get('custom_field1')
        
        # Step 3: Process through AutoAdvisor
        advisor = AutoAdvisor()
        student_dict = request.student_data.dict()
        analysis = advisor.analyze_transcript(student_dict)
        
        # Step 4: You can pass additional_data to your processing if needed
        if request.additional_data:
            # Process custom data here
            # For example: analysis['custom_info'] = request.additional_data
            pass
        
        # Step 5: Return results
        return AnalyzeResponse(
            success=True,
            message="Analysis completed successfully",
            username=request.username,
            gpa=analysis['gpa'],
            total_credits=analysis['total_credits'],
            academic_standing=analysis['academic_standing'],
            recommendations=analysis['recommendations'],
            timestamp=datetime.now().isoformat()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# METHOD 2: Separate Username/Password Parameters
# ============================================================

@app.post("/api/analyze-separate")
def analyze_separate_auth(
    username: str = Body(..., example="john.doe@vsu.edu"),
    password: str = Body(..., example="SecurePass123!"),
    student_data: StudentData = Body(...)
):
    """
    Alternative: Username and password as separate fields
    
    Send this JSON:
    {
        "username": "john.doe@vsu.edu",
        "password": "SecurePass123!",
        "student_data": {
            "name": "John Doe",
            "student_id": "V123456789",
            "advisor": "Dr. Smith",
            "transcript": {...}
        }
    }
    """
    # Authenticate
    authenticate_user(username, password)
    
    # Process
    advisor = AutoAdvisor()
    analysis = advisor.analyze_transcript(student_data.dict())
    
    return {
        "success": True,
        "username": username,
        "gpa": analysis['gpa'],
        "recommendations": analysis['recommendations']
    }


# ============================================================
# METHOD 3: HTTP Basic Authentication
# ============================================================

def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    """
    Dependency for HTTP Basic Auth
    Username and password sent in HTTP headers
    """
    # Check credentials
    if not verify_credentials(credentials.username, credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@app.post("/api/analyze-basic-auth")
def analyze_basic_auth(
    student_data: StudentData,
    username: str = Depends(get_current_user)
):
    """
    Using HTTP Basic Authentication
    
    Username/password sent in HTTP Authorization header
    
    To test with curl:
    curl -X POST http://localhost:8001/api/analyze-basic-auth \
      -u "username:password" \
      -H "Content-Type: application/json" \
      -d '{"name": "John Doe", ...}'
    
    In code:
    requests.post(url, json=data, auth=('username', 'password'))
    """
    logger.info(f"Basic auth request from: {username}")
    
    advisor = AutoAdvisor()
    analysis = advisor.analyze_transcript(student_data.dict())
    
    return {
        "success": True,
        "username": username,
        "gpa": analysis['gpa']
    }


# ============================================================
# METHOD 4: Email + Password (Common pattern)
# ============================================================

class EmailPasswordRequest(BaseModel):
    """Email and password authentication"""
    email: EmailStr = Field(..., example="john.doe@vsu.edu")
    password: str = Field(..., example="SecurePass123!")
    student_data: StudentData


@app.post("/api/analyze-email")
def analyze_email_auth(request: EmailPasswordRequest):
    """
    Authentication using email and password
    
    Send this JSON:
    {
        "email": "john.doe@vsu.edu",
        "password": "SecurePass123!",
        "student_data": {...}
    }
    """
    # Authenticate with email as username
    authenticate_user(request.email, request.password)
    
    # Process
    advisor = AutoAdvisor()
    analysis = advisor.analyze_transcript(request.student_data.dict())
    
    return {
        "success": True,
        "email": request.email,
        "gpa": analysis['gpa'],
        "total_credits": analysis['total_credits'],
        "recommendations": analysis['recommendations']
    }


@app.post("/api/process-json")
def process_generic_json(
    username: str = Body(...),
    password: str = Body(...),
    pin: Optional[str] = Body(None),
    data: Dict[str, Any] = Body(..., description="Any JSON object you want to send")
):
    """
    Generic endpoint - accepts ANY JSON structure
    
    Send ANY JSON structure in the 'data' field:
    {
        "username": "john.doe@vsu.edu",
        "password": "SecurePass123!",
        "pin": "1234",
        "data": {
            "anything": "you want",
            "numbers": [1, 2, 3],
            "nested": {
                "deeply": {
                    "nested": "values"
                }
            },
            "arrays": ["item1", "item2"],
            "mixed": {
                "strings": "text",
                "numbers": 123,
                "booleans": true,
                "nulls": null
            }
        }
    }
    """
    logger.info(f"Generic JSON request from: {username}")
    
    try:
        # Authenticate
        authenticate_user(username, password, pin)
        
        # Process the generic JSON data
        # You can access any field:
        # - data.get('anything')
        # - data['nested']['deeply']['nested']
        # - data['arrays'][0]
        
        logger.info(f"Received data keys: {list(data.keys())}")
        
        return {
            "success": True,
            "message": "JSON processed successfully",
            "username": username,
            "data_received": data,
            "data_keys": list(data.keys()),
            "data_type": type(data).__name__,
            "timestamp": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing JSON: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/flexible-analyze")
def flexible_analyze(
    username: str = Body(...),
    password: str = Body(...),
    pin: Optional[str] = Body(None),
    transcript_data: Optional[Dict[str, Any]] = Body(None),
    custom_data: Optional[Dict[str, Any]] = Body(None)
):
    """
    Flexible endpoint - accepts multiple optional JSON objects
    
    You can send:
    - Just transcript_data
    - Just custom_data  
    - Both
    - Or other fields you add
    
    Example:
    {
        "username": "john.doe@vsu.edu",
        "password": "SecurePass123!",
        "pin": "1234",
        "transcript_data": {
            "name": "John Doe",
            "courses": [...]
        },
        "custom_data": {
            "preferences": {
                "notification_email": true,
                "theme": "dark"
            },
            "metadata": {
                "source": "mobile_app",
                "version": "2.1.0"
            }
        }
    }
    """
    try:
        # Authenticate
        authenticate_user(username, password, pin)
        
        results = {
            "success": True,
            "username": username,
            "pin_provided": pin is not None
        }
        
        # Process transcript_data if provided
        if transcript_data:
            logger.info("Processing transcript data")
            results["transcript_processed"] = True
            results["transcript_keys"] = list(transcript_data.keys())
            # Add your transcript processing logic here
        
        # Process custom_data if provided
        if custom_data:
            logger.info("Processing custom data")
            results["custom_data_processed"] = True
            results["custom_data_keys"] = list(custom_data.keys())
            # Add your custom data processing logic here
        
        return results
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# UTILITY ENDPOINTS
# ============================================================

@app.get("/")
def root():
    """Health check"""
    return {
        "status": "healthy",
        "service": "AutoAdvisor API",
        "authentication": "Username/Password required",
        "endpoints": {
            "login": "/api/login",
            "analyze": "/api/analyze",
            "docs": "/docs"
        }
    }


@app.post("/api/validate-credentials")
def validate_credentials_endpoint(
    username: str = Body(...),
    password: str = Body(...)
):
    """
    Test if credentials are valid
    
    JSON:
    {
        "username": "john.doe@vsu.edu",
        "password": "SecurePass123!"
    }
    """
    try:
        authenticate_user(username, password)
        return {
            "valid": True,
            "message": "Credentials are valid"
        }
    except HTTPException:
        return {
            "valid": False,
            "message": "Invalid credentials"
        }


@app.get("/api/example-request")
def get_example_request():
    """
    Get example JSON with username/password/PIN and additional data
    """
    return {
        "username": "john.doe@vsu.edu",
        "password": "SecurePass123!",
        "pin": "1234",
        "student_data": {
            "name": "John Doe",
            "student_id": "V123456789",
            "advisor": "Dr. Smith",
            "transcript": {
                "freshman_1": [
                    {
                        "name": "Intro to CS Profession",
                        "grade": "A",
                        "credits": 2.0,
                        "semester": "FA22",
                        "notes": None
                    }
                ],
                "freshman_2": [],
                "sophomore_1": [],
                "sophomore_2": [],
                "junior_1": [],
                "junior_2": [],
                "senior_1": [],
                "senior_2": []
            }
        },
        "additional_data": {
            "preferences": {
                "email_notifications": True,
                "theme": "dark"
            },
            "metadata": {
                "app_version": "2.1.0",
                "platform": "web"
            },
            "custom_fields": {
                "field1": "value1",
                "field2": 123,
                "field3": [1, 2, 3]
            }
        },
        "prompt": "What courses should I take next?"
    }


# ============================================================
# TESTING EXAMPLES
# ============================================================

"""
HOW TO TEST WITH USERNAME/PASSWORD:

1. Using FastAPI Docs:
   - Go to: http://localhost:8001/docs
   - Click on /api/analyze endpoint
   - Click "Try it out"
   - Fill in username and password in the JSON
   - Click "Execute"

2. Using curl:

   # Login
   curl -X POST http://localhost:8001/api/login \
     -H "Content-Type: application/json" \
     -d '{
       "username": "john.doe@vsu.edu",
       "password": "SecurePass123!"
     }'
   
   # Analyze with username/password
   curl -X POST http://localhost:8001/api/analyze \
     -H "Content-Type: application/json" \
     -d '{
       "username": "john.doe@vsu.edu",
       "password": "SecurePass123!",
       "student_data": {
         "name": "John Doe",
         "student_id": "V123456789",
         "advisor": "Dr. Smith",
         "transcript": {
           "freshman_1": [{"name": "CS101", "grade": "A", "credits": 3.0, "semester": "FA22"}],
           "freshman_2": [],
           "sophomore_1": [],
           "sophomore_2": [],
           "junior_1": [],
           "junior_2": [],
           "senior_1": [],
           "senior_2": []
         }
       }
     }'
   
   # Using HTTP Basic Auth
   curl -X POST http://localhost:8001/api/analyze-basic-auth \
     -u "username:password" \
     -H "Content-Type: application/json" \
     -d @student_data.json

3. Using Python requests:

   import requests
   
   # Login
   login_data = {
       "username": "john.doe@vsu.edu",
       "password": "SecurePass123!"
   }
   response = requests.post("http://localhost:8001/api/login", json=login_data)
   print(response.json())
   
   # Analyze
   analyze_data = {
       "username": "john.doe@vsu.edu",
       "password": "SecurePass123!",
       "student_data": {...}
   }
   response = requests.post("http://localhost:8001/api/analyze", json=analyze_data)
   print(response.json())
   
   # Using Basic Auth
   response = requests.post(
       "http://localhost:8001/api/analyze-basic-auth",
       json={"student_data": {...}},
       auth=("username", "password")
   )

4. Using .http file:

   ### Login
   POST http://localhost:8001/api/login
   Content-Type: application/json
   
   {
     "username": "john.doe@vsu.edu",
     "password": "SecurePass123!"
   }
   
   ### Analyze with credentials
   POST http://localhost:8001/api/analyze
   Content-Type: application/json
   
   {
     "username": "john.doe@vsu.edu",
     "password": "SecurePass123!",
     "student_data": {
       "name": "John Doe",
       "student_id": "V123456789",
       "advisor": "Dr. Smith",
       "transcript": {
         "freshman_1": [],
         "freshman_2": [],
         "sophomore_1": [],
         "sophomore_2": [],
         "junior_1": [],
         "junior_2": [],
         "senior_1": [],
         "senior_2": []
       }
     }
   }
"""
