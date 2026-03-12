from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional

from app.core.database import get_db
from app.services.report_service import ReportService

router = APIRouter(prefix="/api/reports", tags=["reports"])

@router.get("/summary")
def get_daily_summary(
    target_date: Optional[date] = Query(None, description="Date for the report (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    if not target_date:
        from datetime import datetime
        target_date = datetime.utcnow().date()
        
    service = ReportService(db)
    return service.get_summary_by_date(target_date)

@router.get("/device/{device_id}")
def get_device_report(
    device_id: str,
    target_date: Optional[date] = Query(None, description="Date for the report (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    if not target_date:
        from datetime import datetime
        target_date = datetime.utcnow().date()
        
    service = ReportService(db)
    report = service.get_device_detail_report(device_id, target_date)
    
    if not report:
        raise HTTPException(status_code=404, detail="Device not found")
        
    return report
