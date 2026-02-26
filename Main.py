# fastapi-service/main.py
# Two-Step API Flow: AutoAdvisor pauses for PIN, then continues

import logging
import subprocess
import json
import os
import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Auto Advisor API - Two-Step Flow")

# In-memory session storage (use Redis in production)
active_sessions = {}

class FetchTranscriptRequest(BaseModel):
    username: str
    password: str
    config_path: Optional[str] = "./config.xlsx"
    advisor: Optional[str] = ""

class PinRequest(BaseModel):
    session_id: str
    pin: str

class TranscriptResponse(BaseModel):
    success: bool
    session_id: str
    transcript_data: Optional[Dict[str, Any]] = None
    message: str

@app.get("/")
def health_check():
    """Health check endpoint"""
    return {"status": "online", "version": "2.4.4-Student"}

@app.post("/api/fetch-transcript")
def fetch_transcript(request: FetchTranscriptRequest):
    """
    Step 1: User submits credentials to request transcript
    Returns a session_id to use for PIN submission
    """
    logger.info(f"Transcript request for user: {request.username}")
    
    # Create session
    session_id = f"session_{datetime.now().timestamp()}"
    active_sessions[session_id] = {
        "status": "awaiting_pin",
        "username": request.username,
        "password": request.password,
        "config_path": request.config_path or "./config.xlsx",
        "advisor": request.advisor or "",
        "created_at": datetime.now().isoformat()
    }
    
    logger.info(f"Session created: {session_id}")
    
    return {
        "success": True,
        "session_id": session_id,
        "message": "Session created. Submit PIN to continue."
    }

def run_autoadvisor(username: str, password: str, config_path: str, advisor: str) -> Optional[Dict[str, Any]]:
    """
    Call project.py as subprocess to fetch and parse transcript
    Returns the parsed note.json data
    """
    try:
        # Build command to run project.py
        project_py_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "autoadvisor-dev", "project.py"))
        
        cmd = [
            sys.executable,
            project_py_path,
            "--config", config_path,
            "--user", username,
            "--pass", password
        ]
        
        if advisor:
            cmd += ["--advisor", advisor]
        
        logger.info(f"Running: {' '.join(cmd)}")
        
        # Run project.py and capture output
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        # Print all output to terminal
        print("\n" + "="*100)
        print("AUTOADVISOR SUBPROCESS OUTPUT:")
        print("="*100)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        print("="*100 + "\n")
        
        # Try to extract JSON from stdout (it prints at the end between === markers)
        output = result.stdout
        if "FINAL STUDENT TRANSCRIPT DATA - note.json" in output:
            # Extract JSON between the === markers
            start_marker = "FINAL STUDENT TRANSCRIPT DATA - note.json"
            start_idx = output.find(start_marker)
            if start_idx != -1:
                # Find the first { after the marker
                json_start = output.find("{", start_idx)
                if json_start != -1:
                    # Find the last } in the output
                    json_end = output.rfind("}")
                    if json_end != -1 and json_end > json_start:
                        json_str = output[json_start:json_end+1]
                        try:
                            transcript_data = json.loads(json_str)
                            logger.info("Successfully extracted transcript JSON from output")
                            return transcript_data
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse JSON: {e}")
        
        logger.warning("Could not extract transcript data from subprocess output")
        return None
    
    except subprocess.TimeoutExpired:
        logger.error("AutoAdvisor process timed out after 10 minutes")
        raise HTTPException(status_code=504, detail="AutoAdvisor processing timed out")
    except Exception as e:
        logger.error(f"Error running AutoAdvisor: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AutoAdvisor error: {str(e)}")

@app.post("/api/submit-pin", response_model=TranscriptResponse)
def submit_pin(request: PinRequest):
    """
    Step 2: User submits PIN to continue processing
    Calls project.py to fetch and parse transcript
    """
    logger.info(f"PIN submission for session: {request.session_id}")
    
    try:
        # Retrieve session
        if request.session_id not in active_sessions:
            raise HTTPException(status_code=404, detail="Session not found or expired")
        
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
        
        logger.info("PIN validated, running AutoAdvisor processing")
        
        # Update session status
        session["status"] = "processing"
        session["pin"] = request.pin
        
        # Call project.py to fetch transcript
        transcript_data = run_autoadvisor(
            session["username"],
            session["password"],
            session["config_path"],
            session["advisor"]
        )
        
        # Update session with results
        session["status"] = "completed"
        session["transcript_data"] = transcript_data
        
        logger.info("Transcript fetched successfully")
        
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

@app.get("/api/session/{session_id}")
def get_session(session_id: str):
    """Check session status"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    return {
        "session_id": session_id,
        "status": session["status"],
        "created_at": session.get("created_at"),
        "transcript_data": session.get("transcript_data")
    }

@app.delete("/api/session/{session_id}")
def delete_session(session_id: str):
    """Cancel/delete a session"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    del active_sessions[session_id]
    return {"message": "Session deleted"}

@app.get("/api/active-sessions")
def list_active_sessions():
    """List all active sessions (dev only)"""
    return {
        "count": len(active_sessions),
        "sessions": list(active_sessions.keys())
    }

if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*100)
    print("AUTO ADVISOR API - TWO-STEP FLOW")
    print("="*100)
    print("\nAPI running on: http://localhost:8001")
    print("\nQUICK START:")
    print("-" * 100)
    print("\n1. Request transcript:")
    print("   POST /api/fetch-transcript")
    print("   Body: {\"username\": \"jdoe@vsu.edu\", \"password\": \"YourPass\"}")
    print("\n2. Submit PIN:")
    print("   POST /api/submit-pin")
    print("   Body: {\"session_id\": \"<from step 1>\", \"pin\": \"1234\"}")
    print("\n3. Check status:")
    print("   GET /api/session/{session_id}")
    print("\n" + "="*100)
    print("ENDPOINTS:")
    print("-" * 100)
    print("  POST   /api/fetch-transcript        - Step 1: Request transcript")
    print("  POST   /api/submit-pin              - Step 2: Submit PIN")
    print("  GET    /api/session/{session_id}    - Check session status")
    print("  DELETE /api/session/{session_id}    - Cancel session")
    print("  GET    /api/active-sessions         - View all active sessions (dev)")
    print("  GET    /                            - Health check")
    print("="*100 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8001)