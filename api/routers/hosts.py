"""
Production-grade Host Leads API Router.
Handles 'Become a Host' lead submission and management with WhatsApp notifications.
CTO-level implementation with proper error handling, separation of concerns, and maintainability.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from asgiref.sync import sync_to_async
import logging
from decouple import config

from .auth import get_current_user

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class HostLeadRequest(BaseModel):
    """Request model for submitting a host lead"""
    first_name: str = Field(..., min_length=1, max_length=100, description="First name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Last name")
    phone_number: str = Field(..., min_length=10, max_length=20, description="Phone number")
    message: Optional[str] = Field(None, max_length=1000, description="Optional message from the potential host")

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
    data: Optional[Dict[str, Any]] = None


# ============================================================================
# Configuration
# ============================================================================

class HostLeadConfig:
    """Configuration for host lead notifications"""
    
    @staticmethod
    def get_whatsapp_content_sid() -> Optional[str]:
        """Get WhatsApp content template SID from environment"""
        return config('TWILIO_WHATSAPP_CONTENT_SID', default=None)
    
    @staticmethod
    def get_whatsapp_enabled() -> bool:
        """Check if WhatsApp notifications are enabled"""
        return config('ENABLE_WHATSAPP_NOTIFICATIONS', default='true', cast=bool)


# ============================================================================
# Database Operations
# ============================================================================

@sync_to_async
def check_existing_lead(phone_number: str):
    """Check if a lead with the given phone number exists"""
    from users.models import HostLead
    try:
        return HostLead.objects.filter(phone_number=phone_number).first()
    except Exception as e:
        logger.error(f"Error checking existing lead for {phone_number}: {e}")
        raise


@sync_to_async
def create_lead(first_name: str, last_name: str, phone_number: str, message: Optional[str] = None):
    """Create a new host lead"""
    from users.models import HostLead
    try:
        return HostLead.objects.create(
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            message=message or ""
        )
    except Exception as e:
        logger.error(f"Error creating host lead: {e}")
        raise


@sync_to_async
def get_all_leads():
    """Get all host leads"""
    from users.models import HostLead
    try:
        return list(HostLead.objects.all().order_by('-created_at'))
    except Exception as e:
        logger.error(f"Error retrieving host leads: {e}")
        raise


# ============================================================================
# WhatsApp Notification Service
# ============================================================================

class WhatsAppNotificationService:
    """Service for sending WhatsApp notifications to host leads"""
    
    def __init__(self):
        self.content_sid = HostLeadConfig.get_whatsapp_content_sid()
        self.enabled = HostLeadConfig.get_whatsapp_enabled()
    
    async def send_host_lead_confirmation(
        self,
        first_name: str,
        phone_number: str,
        is_existing: bool = False
    ) -> bool:
        """
        Send WhatsApp confirmation message to host lead.
        
        Args:
            first_name: User's first name
            phone_number: User's phone number
            is_existing: Whether this is an existing lead
        
        Returns:
            True if message was sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("WhatsApp notifications are disabled")
            return False
        
        if not self.content_sid:
            logger.warning("WhatsApp content template SID not configured, skipping notification")
            return False
        
        try:
            from users.services import get_twilio_service
            
            twilio_service = get_twilio_service()
            
            # Prepare content variables for the template
            # Template: "Hello {{1}}, Your LoopinX Circle account setup is complete ✅ 
            #            To confirm you received this message, please reply with "YES"."
            content_variables = {
                "1": first_name  # Variable 1 is the user's first name
            }
            
            # Send WhatsApp message (fire and forget - don't fail API if WhatsApp fails)
            success, whatsapp_message = await sync_to_async(
                lambda: twilio_service.send_whatsapp_message(
                    phone_number=phone_number,
                    content_sid=self.content_sid,
                    content_variables=content_variables
                )
            )()
            
            if success:
                logger.info(f"WhatsApp confirmation sent to {phone_number} using template {self.content_sid}")
            else:
                logger.warning(f"Failed to send WhatsApp confirmation to {phone_number}: {whatsapp_message}")
            
            return success
                    
        except Exception as whatsapp_error:
            # Log error but don't fail the API call
            logger.error(f"Error sending WhatsApp confirmation to {phone_number}: {str(whatsapp_error)}", exc_info=True)
            return False


# ============================================================================
# Dependencies
# ============================================================================

async def get_admin_user(current_user=Depends(get_current_user)):
    """Dependency to check if user is admin"""
    if not current_user.is_staff or not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires admin privileges"
        )
    return current_user


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/become-a-host", response_model=HostLeadResponse)
async def submit_host_lead(request: HostLeadRequest):
    """
    Submit a lead for 'Become a Host' program.
    
    This endpoint:
    - Creates or retrieves a host lead
    - Sends WhatsApp confirmation notification
    - Returns lead information
    
    - **first_name**: First name of the potential host
    - **last_name**: Last name of the potential host  
    - **phone_number**: Phone number of the potential host
    - **message**: Optional message from the potential host
    """
    try:
        # Check for existing lead
        existing_lead = await check_existing_lead(request.phone_number)
        
        # Initialize WhatsApp notification service
        whatsapp_service = WhatsAppNotificationService()
        
        if existing_lead:
            # Send WhatsApp confirmation for existing lead
            await whatsapp_service.send_host_lead_confirmation(
                first_name=request.first_name,
                phone_number=request.phone_number,
                is_existing=True
            )
            
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
        
        # Create new lead
        host_lead = await create_lead(
            first_name=request.first_name,
            last_name=request.last_name,
            phone_number=request.phone_number,
            message=request.message
        )
        
        # Send WhatsApp confirmation for new lead
        await whatsapp_service.send_host_lead_confirmation(
            first_name=request.first_name,
            phone_number=request.phone_number,
            is_existing=False
        )
        
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
        logger.error(f"Unexpected error in submit_host_lead: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while submitting your information. Please try again later."
        )


@router.get("/host-leads", response_model=HostLeadResponse)
async def get_all_host_leads(current_user=Depends(get_admin_user)):
    """
    Get all host leads (admin only - for internal use).
    
    Requires admin authentication via JWT token.
    Returns list of all host leads with their status and metadata.
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
        logger.error(f"Error retrieving host leads: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving host leads. Please try again later."
        )
