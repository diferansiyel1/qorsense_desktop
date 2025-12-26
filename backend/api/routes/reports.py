"""
Report Generation Routes

Handles PDF report generation for analysis results.
Protected with JWT authentication - requires valid access token in production.
"""

import logging

from backend.api.deps import DevUser
from backend.models import ReportRequest
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("/generate")
async def generate_report(
    request: ReportRequest,
    current_user: DevUser = None,
):
    """
    Generate a PDF report for sensor analysis.
    
    **Authentication**: Required in production, optional in development.
    
    Args:
        request: Report generation parameters including metrics and diagnosis
        current_user: Authenticated user (optional in development)
        
    Returns:
        FileResponse: PDF file download
    """
    try:
        from backend.report_gen import create_pdf

        # Prepare raw data
        raw_data = request.data if request.data else []

        # Prepare metrics
        metrics_data = request.metrics.dict() if hasattr(request.metrics, 'dict') else request.metrics.model_dump()
        metrics_data["sensor_id"] = request.sensor_id
        metrics_data["flags"] = request.flags
        metrics_data["recommendation"] = request.recommendation

        # Generate PDF
        pdf_path = create_pdf(
            metrics=metrics_data,
            raw_data=raw_data,
            diagnosis=request.diagnosis,
            health_score=request.health_score
        )

        user_info = current_user.username if current_user else "anonymous (dev mode)"
        logger.info(f"Generated report for sensor {request.sensor_id} by user: {user_info}")
        return FileResponse(
            pdf_path,
            media_type='application/pdf',
            filename=f"report_{request.sensor_id}.pdf"
        )
    except Exception as e:
        logger.error(f"Report generation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

