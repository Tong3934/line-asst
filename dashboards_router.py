import logging
import os
from collections import Counter
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from constants import ALL_STATUSES, VALID_TRANSITIONS, DATA_DIR
from storage import claim_store, document_store

logger = logging.getLogger(__name__)

router = APIRouter(tags=["dashboards"])
templates = Jinja2Templates(directory="dashboards")

# --- REVIEWER DASHBOARD ---

@router.get("/reviewer", response_class=HTMLResponse)
async def reviewer_dashboard(
    request: Request,
    status: Optional[str] = Query(None),
    claim_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    claims = claim_store.list_all_claims(
        status_filter=status, type_filter=claim_type, date_from=date_from, date_to=date_to
    )
    # Sort claims by creation date descending
    claims.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    for c in claims:
        c["extracted_data"] = claim_store.get_extracted_data(c.get("claim_id"))
    
    return templates.TemplateResponse(
        "reviewer.html",
        {
            "request": request,
            "claims": claims,
            "all_statuses": ALL_STATUSES,
            "valid_transitions": VALID_TRANSITIONS,
            "selected_status": status,
            "selected_type": claim_type,
            "date_from": date_from,
            "date_to": date_to,
        },
    )

@router.get("/reviewer/document")
async def reviewer_get_document(claim_id: str, filename: str):
    """Serve image bytes for a claim document."""
    try:
        content = document_store.get_document_bytes(claim_id, filename)
        # simplistic mime type logic
        media_type = "image/jpeg"
        if filename.lower().endswith(".png"):
            media_type = "image/png"
        elif filename.lower().endswith(".pdf"):
            media_type = "application/pdf"
            
        return Response(content=content, media_type=media_type)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found")

class UsefulPayload(BaseModel):
    claim_id: str
    filename: str
    useful: bool

@router.post("/reviewer/useful")
async def reviewer_mark_useful(payload: UsefulPayload):
    claim_store.mark_document_useful(payload.claim_id, payload.filename, payload.useful)
    return JSONResponse({"ok": True})

class StatusPayload(BaseModel):
    claim_id: str
    status: str
    memo: Optional[str] = None
    paid_amount: Optional[float] = None

@router.post("/reviewer/status")
async def reviewer_update_status(payload: StatusPayload):
    current = claim_store.get_claim_status(payload.claim_id)
    if not current:
        return JSONResponse({"ok": False, "detail": "Claim not found"}, status_code=404)
        
    allowed = VALID_TRANSITIONS.get(current.get("status"), [])
    if payload.status not in allowed:
        return JSONResponse({"ok": False, "detail": f"Invalid transition from {current.get('status')} to {payload.status}"}, status_code=400)
    
    claim_store.update_claim_status(
        payload.claim_id,
        status=payload.status,
        memo=payload.memo,
        paid_amount=payload.paid_amount,
    )
    return JSONResponse({"ok": True, "new_status": payload.status})


# --- MANAGER DASHBOARD ---

@router.get("/manager", response_class=HTMLResponse)
async def manager_dashboard(request: Request):
    return templates.TemplateResponse("manager.html", {"request": request})

@router.get("/manager/data")
async def manager_data(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    claim_type: Optional[str] = Query(None),
):
    claims = claim_store.list_all_claims(date_from=date_from, date_to=date_to, type_filter=claim_type)
    
    status_counts = Counter(c.get("status", "Unknown") for c in claims)
    type_counts = Counter(c.get("claim_type", "Unknown") for c in claims)
    
    daily_counts = Counter()
    total_response_time = 0
    response_time_count = 0
    total_paid_amount = 0
    
    for c in claims:
        created = c.get("created_at", "")[:10]
        if created:
            daily_counts[created] += 1
            
        metrics = c.get("metrics", {})
        times = metrics.get("response_times_ms", [])
        if times:
            total_response_time += sum(times)
            response_time_count += len(times)
            
        paid = metrics.get("total_paid_amount")
        if paid is not None:
            total_paid_amount += paid
            
    # Calculate averages
    avg_response_time = int(total_response_time / response_time_count) if response_time_count > 0 else 0
    
    return JSONResponse({
        "total": len(claims),
        "status_counts": dict(status_counts),
        "type_counts": dict(type_counts),
        "daily_counts": dict(sorted(daily_counts.items())),
        "avg_response_time_ms": avg_response_time,
        "total_paid_amount": total_paid_amount,
        "claims_list": [
            {
                "claim_id": c.get("claim_id"),
                "claim_type": c.get("claim_type"),
                "status": c.get("status"),
                "created_at": c.get("created_at"),
                "paid_amount": c.get("metrics", {}).get("total_paid_amount"),
                "avg_resp": sum(c.get("metrics", {}).get("response_times_ms", [])) / len(c.get("metrics", {}).get("response_times_ms", [])) if c.get("metrics", {}).get("response_times_ms") else 0
            } for c in sorted(claims, key=lambda x: x.get("created_at", ""), reverse=True)
        ]
    })


# --- ADMIN DASHBOARD ---

@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    # Just a placeholder for Admin Dashboard
    return templates.TemplateResponse("admin.html", {"request": request})

class LoglevelPayload(BaseModel):
    level: str

@router.post("/admin/loglevel")
async def admin_set_loglevel(payload: LoglevelPayload):
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR
    }
    if payload.level not in level_map:
        raise HTTPException(status_code=400, detail="Invalid log level")
        
    logger.setLevel(level_map[payload.level])
    return JSONResponse({"ok": True, "new_level": payload.level})

@router.get("/admin/tokens")
async def admin_get_tokens():
    # Return mockup token stats
    return JSONResponse({"tokens_used": {"CD": 12500, "H": 4200}})
