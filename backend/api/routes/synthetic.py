"""
Synthetic Data Generation Routes

Provides endpoints for generating test/demo sensor data.
"""

import logging

import numpy as np
from backend.models import SyntheticRequest
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/synthetic", tags=["Synthetic Data"])


@router.post("/generate")
async def generate_synthetic(request: SyntheticRequest):
    """
    Generate synthetic sensor data for testing.
    
    Supported types:
    - Normal: Clean sinusoidal signal with low noise
    - Drifting: Signal with linear drift (degradation)
    - Noisy: High noise level
    - Oscillation: High-frequency oscillations
    
    Args:
        request: Synthetic data generation parameters
        
    Returns:
        dict: Generated data and timestamps
    """
    try:
        t = np.linspace(0, 10, request.length)
        base_signal = np.sin(t) * 10

        if request.type == "Normal":
            noise = np.random.normal(0, 0.5, request.length)
            data = base_signal + noise

        elif request.type == "Drifting":
            noise = np.random.normal(0, 0.5, request.length)
            drift = np.linspace(0, 5, request.length)
            data = base_signal + noise + drift

        elif request.type == "Noisy":
            noise = np.random.normal(0, 3.0, request.length)
            data = base_signal + noise

        elif request.type == "Oscillation":
            oscillation = np.sin(t * 10) * 5
            noise = np.random.normal(0, 0.2, request.length)
            data = base_signal + oscillation + noise
        else:
            raise HTTPException(status_code=400, detail=f"Invalid type: {request.type}")

        logger.info(f"Generated {request.type} synthetic data: {request.length} points")
        return {
            "data": data.tolist(),
            "timestamps": t.tolist(),
            "type": request.type,
            "length": request.length
        }
    except Exception as e:
        logger.error(f"Synthetic data generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
