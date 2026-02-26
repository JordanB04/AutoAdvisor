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

def run_autoadvisor(username: str,
                    password: str,
                    config_path: str,
                    advisor: str) -> Optional[Dict[str, Any]]:
    """
    Invoke project.py as a subprocess and then load the resulting note.json
    from disk.  Print the subprocess output to the terminal for debugging.
    """
    project_py = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                               "autoadvisor-dev", "project.py"))
    cmd = [sys.executable, project_py,
           "--config", config_path,
           "--user", username,
           "--pass", password]
    if advisor:
        cmd += ["--advisor", advisor]

    logger.info(f"running: {' '.join(cmd)}")

    # PROMINENT AUTHENTICATION MESSAGE
    print("\n" + "!"*100)
    print("! AUTHENTICATION REQUIRED")
    print("!"*100)
    print("! A browser window will open momentarily.")
    print("! You will be taken to the Banner Student Services login page.")
    print("! After entering your credentials, you will be asked for a 4-digit PIN.")
    print("! ")
    print("! CHECK YOUR PHONE/AUTHENTICATOR APP FOR THE PIN CODE.")
    print("! Once you receive the PIN, use it in the next API call:")
    print("!   POST /api/submit-pin")
    print("!   Body: {\"session_id\": \"<your-session-id>\", \"pin\": \"<4-digit-code>\"}")
    print("! ")
    print("! Do NOT close the browser window until the script completes.")
    print("!"*100 + "\n")

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    # echo everything to the terminal
    print("\n" + "=" * 100)
    print("AUTOADVISOR SUBPROCESS OUTPUT")
    print("=" * 100)
    print(proc.stdout)
    if proc.stderr:
        print("STDERR:", proc.stderr)
    print("=" * 100 + "\n")

    # now load the note.json that project.py just wrote
    transcript_data = None
    # try both plausible locations
    possible_dirs = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "advisors")),
        os.path.abspath(os.path.join(os.path.dirname(__file__),
                                     "autoadvisor-dev", "advisors"))
    ]
    for advisors_dir in possible_dirs:
        if not os.path.exists(advisors_dir):
            continue
        timestamps = sorted([d for d in os.listdir(advisors_dir)
                             if os.path.isdir(os.path.join(advisors_dir, d))])
        if not timestamps:
            continue
        latest_ts = timestamps[-1]
        base = os.path.join(advisors_dir, latest_ts)
        print(f"\n[Info] Searching for transcript data in: {base}\n")
        for root, dirs, files in os.walk(base):
            if "note.json" in files:
                note_path = os.path.join(root, "note.json")
                try:
                    with open(note_path, "r", encoding="utf-8") as jf:
                        transcript_data = json.load(jf)
                    print("\n" + "="*100)
                    print("FINAL TRANSCRIPT DATA - LOADED FROM DISK")
                    print("="*100)
                    print(f"Location: {note_path}\n")
                    print(json.dumps(transcript_data, indent=2, ensure_ascii=False))
                    print("="*100 + "\n")
                    logger.info(f"loaded note.json from {note_path}")
                except Exception as e:
                    logger.error(f"failed to read {note_path}: {e}")
                break
        if transcript_data is not None:
            break

    if transcript_data is None:
        logger.warning("run_autoadvisor: note.json not found, returning None")
        print("\n[WARNING] Transcript data was not found on disk.\n")
    return transcript_data

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