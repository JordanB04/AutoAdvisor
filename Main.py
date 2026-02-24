# fastapi-service/main.py
# Two-Step API Flow: AutoAdvisor pauses for PIN, then continues

from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
import uuid
import logging
from datetime import datetime

app = FastAPI(title="Auto Advisor API - Two-Step Flow")
logger = logging.getLogger(__name__)

# In-memory session storage (use Redis in production)
active_sessions = {}


# ============================================================
# MODELS
# ============================================================

class InitialRequest(BaseModel):
    """Step 1: Initial request to fetch transcript"""
    username: str
    password: str


class PinRequest(BaseModel):
    """Step 2: User provides PIN"""
    session_id: str
    pin: str


class SessionResponse(BaseModel):
    """Response when AutoAdvisor needs PIN"""
    session_id: str
    status: str
    message: str
    awaiting_pin: bool


class TranscriptResponse(BaseModel):
    """Final response with transcript data"""
    success: bool
    session_id: str
    transcript_data: Dict[str, Any]
    message: str


# ============================================================
# STEP 1: INITIAL REQUEST - USER REQUESTS TRANSCRIPT
# ============================================================

@app.post("/api/fetch-transcript", response_model=SessionResponse)
def fetch_transcript(request: InitialRequest):
    """
    Step 1: User requests transcript analysis
    
    Flow:
    1. User sends username/password
    2. API validates credentials
    3. API creates AutoAdvisor instance
    4. AutoAdvisor starts processing
    5. AutoAdvisor needs PIN (2FA)
    6. API pauses and returns session_id
    7. User must call /api/submit-pin with session_id
    
    Request:
    {
        "username": "jdoe@vsu.edu",
        "password": "SecurePass123"
    }
    
    Response:
    {
        "session_id": "abc123-def456",
        "status": "awaiting_pin",
        "message": "PIN required for 2FA",
        "awaiting_pin": true
    }
    """
    logger.info(f"Fetch transcript request from: {request.username}")
    
    try:
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        # Validate credentials (simplified)
        if not request.username or len(request.password) < 8:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Create session state
        session_state = {
            "session_id": session_id,
            "username": request.username,
            "password": request.password,
            "status": "awaiting_pin",
            "created_at": datetime.now().isoformat(),
            "autoadvisor_state": "initialized",
            "transcript_data": None
        }
        
        # Store session (in production, use Redis with expiration)
        active_sessions[session_id] = session_state
        
        logger.info(f"Session created: {session_id}, awaiting PIN")
        
        # Return session ID and request PIN
        return SessionResponse(
            session_id=session_id,
            status="awaiting_pin",
            message="Please provide your 4-digit PIN to continue",
            awaiting_pin=True
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# STEP 2: PIN SUBMISSION - USER PROVIDES PIN
# ============================================================

@app.post("/api/submit-pin", response_model=TranscriptResponse)
def submit_pin(request: PinRequest):
    """
    Step 2: User submits PIN to continue processing
    
    Flow:
    1. User sends session_id + PIN
    2. API retrieves session state
    3. API resumes AutoAdvisor with PIN
    4. AutoAdvisor completes transcript fetch
    5. AutoAdvisor returns JSON transcript
    6. API sends transcript to user
    
    Request:
    {
        "session_id": "abc123-def456",
        "pin": "1234"
    }
    
    Response:
    {
        "success": true,
        "session_id": "abc123-def456",
        "transcript_data": {
            "student_id": "V123456789",
            "name": "John Doe",
            "transcript": {...}
        },
        "message": "Transcript fetched successfully"
    }
    """
    logger.info(f"PIN submission for session: {request.session_id}")
    
    try:
        # Retrieve session
        if request.session_id not in active_sessions:
            raise HTTPException(
                status_code=404, 
                detail="Session not found or expired"
            )
        
        session = active_sessions[request.session_id]
        
        # Verify session is awaiting PIN
        if session["status"] != "awaiting_pin":
            raise HTTPException(
                status_code=400,
                detail=f"Session in invalid state: {session['status']}"
            )
        
        # Validate PIN (4 digits)
        if not request.pin.isdigit() or len(request.pin) != 4:
            raise HTTPException(status_code=400, detail="Invalid PIN format")
        
        logger.info("PIN validated, resuming AutoAdvisor processing")
        
        # Update session status
        session["status"] = "processing"
        session["pin"] = request.pin
        
        # Resume AutoAdvisor processing with PIN
        transcript_data = resume_autoadvisor(session)
        
        # Update session with results
        session["status"] = "completed"
        session["transcript_data"] = transcript_data
        
        logger.info("Transcript fetched successfully")
        
        # Return transcript data
        return TranscriptResponse(
            success=True,
            session_id=request.session_id,
            transcript_data=transcript_data,
            message="Transcript fetched successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing PIN: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# AUTOADVISOR INTEGRATION
# ============================================================

def resume_autoadvisor(session: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resume AutoAdvisor processing with PIN
    
    This function:
    1. Takes session state (username, password, PIN)
    2. Calls AutoAdvisor to fetch transcript
    3. Returns transcript JSON
    """
    logger.info("Calling AutoAdvisor with credentials and PIN")
    
    # Import AutoAdvisor (your actual implementation)
    # from auto_advisor import AutoAdvisor
    
    try:
        # Simulated AutoAdvisor call
        # In your actual code, this would:
        # 1. Use Selenium to log into portal with username/password
        # 2. Enter PIN when prompted (2FA)
        # 3. Download transcript
        # 4. Parse transcript into JSON
        # 5. Return structured data
        
        # advisor = AutoAdvisor()
        # transcript = advisor.fetch_transcript(
        #     username=session['username'],
        #     password=session['password'],
        #     pin=session['pin']
        # )
        
        # For now, return mock data
        transcript_data = {
            "student_id": "V123456789",
            "name": "John Doe",
            "advisor": "Dr. Smith",
            "gpa": 3.75,
            "total_credits": 115,
            "transcript": {
                "freshman_1": [
                    {
                        "name": "Intro to CS Profession",
                        "grade": "A",
                        "credits": 2.0,
                        "semester": "FA22"
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
        }
        
        return transcript_data
    
    except Exception as e:
        logger.error(f"AutoAdvisor error: {str(e)}")
        raise


# ============================================================
# SESSION MANAGEMENT
# ============================================================

@app.get("/api/session/{session_id}")
def get_session_status(session_id: str):
    """
    Check the status of a session
    
    Useful for:
    - Checking if session is still valid
    - Seeing what state AutoAdvisor is in
    - Debugging
    """
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    
    return {
        "session_id": session_id,
        "status": session["status"],
        "created_at": session["created_at"],
        "awaiting_pin": session["status"] == "awaiting_pin"
    }


@app.delete("/api/session/{session_id}")
def cancel_session(session_id: str):
    """
    Cancel/delete a session
    
    Use this if user wants to start over or abandon the process
    """
    if session_id in active_sessions:
        del active_sessions[session_id]
        return {"message": "Session cancelled", "session_id": session_id}
    
    raise HTTPException(status_code=404, detail="Session not found")


# ============================================================
# UTILITY ENDPOINTS
# ============================================================

@app.get("/")
def root():
    """Health check"""
    return {
        "status": "healthy",
        "service": "Auto Advisor API - Two-Step Flow",
        "active_sessions": len(active_sessions),
        "endpoints": {
            "step1": "POST /api/fetch-transcript",
            "step2": "POST /api/submit-pin",
            "status": "GET /api/session/{session_id}"
        }
    }


@app.get("/api/active-sessions")
def get_active_sessions():
    """
    Development endpoint: see all active sessions
    Remove this in production!
    """
    return {
        "count": len(active_sessions),
        "sessions": [
            {
                "session_id": sid,
                "status": session["status"],
                "username": session["username"]
            }
            for sid, session in active_sessions.items()
        ]
    }


# ============================================================
# COMPLETE FLOW EXAMPLE
# ============================================================

"""
COMPLETE API FLOW EXAMPLE:

Step 1: User requests transcript
──────────────────────────────────
POST /api/fetch-transcript
{
    "username": "jdoe@vsu.edu",
    "password": "SecurePass123"
}

Response:
{
    "session_id": "abc123-def456-789",
    "status": "awaiting_pin",
    "message": "Please provide your 4-digit PIN to continue",
    "awaiting_pin": true
}


Step 2: User provides PIN
──────────────────────────
POST /api/submit-pin
{
    "session_id": "abc123-def456-789",
    "pin": "1234"
}

Response:
{
    "success": true,
    "session_id": "abc123-def456-789",
    "transcript_data": {
        "student_id": "V123456789",
        "name": "John Doe",
        "gpa": 3.75,
        "total_credits": 115,
        "transcript": {
            "freshman_1": [...],
            "freshman_2": [...],
            ...
        }
    },
    "message": "Transcript fetched successfully"
}


TESTING WITH CURL:
──────────────────

# Step 1
curl -X POST http://localhost:8001/api/fetch-transcript \
  -H "Content-Type: application/json" \
  -d '{
    "username": "jdoe@vsu.edu",
    "password": "SecurePass123"
  }'

# Save the session_id from response

# Step 2
curl -X POST http://localhost:8001/api/submit-pin \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "YOUR_SESSION_ID_HERE",
    "pin": "1234"
  }'


TESTING IN PYTHON:
──────────────────

import requests

# Step 1: Request transcript
response1 = requests.post(
    "http://localhost:8001/api/fetch-transcript",
    json={
        "username": "jdoe@vsu.edu",
        "password": "SecurePass123"
    }
)

result1 = response1.json()
session_id = result1["session_id"]
print(f"Session ID: {session_id}")
print(f"Status: {result1['status']}")

# Step 2: Submit PIN
response2 = requests.post(
    "http://localhost:8001/api/submit-pin",
    json={
        "session_id": session_id,
        "pin": "1234"
    }
)

result2 = response2.json()
print(f"Success: {result2['success']}")
print(f"Transcript: {result2['transcript_data']}")
"""