"""
FastAPI server for surprise scoring.

The scorer is the neural memory in titans.py (the Titans memory
architecture in this repository). This process is not itself a Titans agent.
"""

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict
import logging
from titans import SessionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Mnemosyne Brain",
    description="Surprise scoring for LLM traffic using the Titans neural memory in titans.py",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for demo purposes
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global session manager
session_manager = SessionManager()


class AnalysisRequest(BaseModel):
    """Request model for text analysis."""
    session_id: str
    text: str


class AnalysisResponse(BaseModel):
    """Response model for analysis results."""
    surprise_score: float
    is_anomaly: bool


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "active_sessions": session_manager.get_session_count()
    }


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_text(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """
    Score input text with the Titans neural memory (titans.py).

    Flow:
    1. Load the SecurityAgent stored under the fixed id global_demo_session
    2. Calculate the surprise score for the input text
    3. Compare that score with the default threshold in is_anomalous
    4. Schedule update_memory as a background task
    5. Return the score and the anomaly flag
    
    Args:
        request: Analysis request containing session_id and text
        background_tasks: FastAPI background tasks for async memory update
        
    Returns:
        Analysis response with surprise score and anomaly flag
    """
    try:
        # Get or create agent for this session
        # FORCE GLOBAL SESSION for demo purposes to allow shared learning and persistence
        # irrespective of what the proxy sends (which is hash-based and unique per query).
        effective_session_id = "global_demo_session"
        agent = session_manager.get_or_create_agent(effective_session_id)
        
        # Calculate surprise score
        surprise_score = agent.calculate_surprise(request.text)
        
        # Determine if anomalous
        is_anomaly = agent.is_anomalous(surprise_score)
        
        # Log the analysis
        logger.info(
            f"Session: {request.session_id[:8]}... | "
            f"Surprise: {surprise_score:.4f} | "
            f"Anomaly: {is_anomaly} | "
            f"Text length: {len(request.text)}"
        )
        
        if is_anomaly:
            logger.warning(
                f"ANOMALY DETECTED - Session: {request.session_id[:8]}... | "
                f"Score: {surprise_score:.4f} | "
                f"Text preview: {request.text[:100]}..."
            )
        
        # Schedule memory update in background (async learning)
        background_tasks.add_task(agent.update_memory, request.text)
        
        # Return immediate response
        return AnalysisResponse(
            surprise_score=surprise_score,
            is_anomaly=is_anomaly
        )
        
    except Exception as e:
        logger.error(f"Error analyzing text: {str(e)}", exc_info=True)
        # In case of error, fail safe to blocking
        return AnalysisResponse(
            surprise_score=999.0,  # High score to trigger blocking
            is_anomaly=True
        )


@app.get("/sessions")
async def get_sessions():
    """Get information about active sessions."""
    return {
        "active_sessions": session_manager.get_session_count(),
        "session_ids": list(session_manager.sessions.keys())
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=5000,
        log_level="info"
    )
