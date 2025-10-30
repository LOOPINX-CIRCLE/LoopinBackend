"""
Host Leads API Router
Handles 'Become a Host' lead submission and management.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from asgiref.sync import sync_to_async
from .auth import get_current_user

# Initialize router
router = APIRouter()


# Request/Response Models
class HostLeadRequest(BaseModel):
    """Request model for submitting a host lead"""
    first_name: str = Field(..., min_length=1, max_length=100, description="First name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Last name")
    phone_number: str = Field(..., min_length=10, max_length=20, description="Phone number")
    message: Optional[str] = Field(None, description="Optional message from the potential host")

    class Config:
        json_schema_extra = {
            "example": {
                "first_name": "John",
                "last_name": "Doe",
                "phone_number": "+1234567890",
                "message": "I would like to host events in my area"
            }
        }


class HostLeadResponse(BaseModel):
    """Response model for host lead"""
    success: bool
    message: str
    data: Optional[dict] = None


# Sync-to-async helper functions
@sync_to_async
def check_existing_lead(phone_number: str):
    """Check if a lead with the given phone number exists"""
    from users.models import HostLead
    return HostLead.objects.filter(phone_number=phone_number).first()


@sync_to_async
def create_lead(first_name: str, last_name: str, phone_number: str, message: Optional[str] = None):
    """Create a new host lead"""
    from users.models import HostLead
    return HostLead.objects.create(
        first_name=first_name,
        last_name=last_name,
        phone_number=phone_number,
        message=message or ""
    )


@sync_to_async
def get_all_leads():
    """Get all host leads"""
    from users.models import HostLead
    return list(HostLead.objects.all())


async def get_admin_user(current_user=Depends(get_current_user)):
    """Dependency to check if user is admin"""
    if not current_user.is_staff or not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires admin privileges"
        )
    return current_user


@router.post("/become-a-host", response_model=HostLeadResponse)
async def submit_host_lead(request: HostLeadRequest):
    """
    Submit a lead for 'Become a Host' program.
    
    - **first_name**: First name of the potential host
    - **last_name**: Last name of the potential host  
    - **phone_number**: Phone number of the potential host
    - **message**: Optional message from the potential host
    """
    try:
        existing_lead = await check_existing_lead(request.phone_number)
        
        if existing_lead:
            return HostLeadResponse(
                success=True,
                message="Thank you! We already have your information. We'll contact you soon!",
                data={
                    "first_name": existing_lead.first_name,
                    "last_name": existing_lead.last_name,
                    "phone_number": existing_lead.phone_number,
                    "submitted_at": existing_lead.created_at.isoformat()
                }
            )
        
        host_lead = await create_lead(request.first_name, request.last_name, request.phone_number, request.message)
        
        return HostLeadResponse(
            success=True,
            message="Thank you for your interest in becoming a host! We'll contact you soon.",
            data={
                "id": host_lead.id,
                "first_name": host_lead.first_name,
                "last_name": host_lead.last_name,
                "phone_number": host_lead.phone_number,
                "message": host_lead.message,
                "submitted_at": host_lead.created_at.isoformat()
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while submitting your information: {str(e)}"
        )


@router.get("/host-leads", response_model=HostLeadResponse)
async def get_all_host_leads(current_user=Depends(get_admin_user)):
    """
    Get all host leads (admin only - for internal use).
    
    Requires admin authentication via JWT token.
    """
    try:
        leads = await get_all_leads()
        
        leads_data = [
            {
                "id": lead.id,
                "first_name": lead.first_name,
                "last_name": lead.last_name,
                "phone_number": lead.phone_number,
                "message": lead.message,
                "is_contacted": lead.is_contacted,
                "is_converted": lead.is_converted,
                "created_at": lead.created_at.isoformat(),
                "updated_at": lead.updated_at.isoformat()
            }
            for lead in leads
        ]
        
        return HostLeadResponse(
            success=True,
            message=f"Retrieved {len(leads_data)} host leads",
            data={"leads": leads_data, "total": len(leads_data)}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while retrieving host leads: {str(e)}"
        )
