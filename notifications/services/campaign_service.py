"""
Campaign Service - Execution Engine for Notification Campaigns

This service handles:
- Campaign validation
- Audience preview
- Safe campaign execution
- Rate limiting
- Batch sending
- Error handling and logging
"""

import logging
import os
from typing import Dict, Any, Optional, List
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from notifications.models import Campaign, CampaignExecution, Notification, NotificationTemplate as NotificationTemplateModel
from notifications.services.rule_engine import RuleEngine, RuleEngineError
from notifications.services.dispatcher import PushNotificationDispatcher
from users.models import UserProfile
import re

logger = logging.getLogger(__name__)

# Global kill switch (can be set via environment variable)
CAMPAIGN_KILL_SWITCH = os.environ.get('DISABLE_CAMPAIGN_SYSTEM', 'False').lower() == 'true'

# Rate limiting constants
MAX_USERS_PER_CAMPAIGN = int(os.environ.get('MAX_CAMPAIGN_USERS', '10000'))
BATCH_SIZE = int(os.environ.get('CAMPAIGN_BATCH_SIZE', '100'))


class CampaignServiceError(ValidationError):
    """Custom exception for campaign service errors"""
    pass


class CampaignService:
    """
    Service for managing notification campaigns.
    
    Handles all campaign lifecycle operations with strict safety checks.
    """
    
    @staticmethod
    def validate_permissions(user: User) -> None:
        """Validate that user has permission to manage campaigns"""
        if not user.is_staff:
            raise CampaignServiceError("Only staff users can manage campaigns")
        
        if CAMPAIGN_KILL_SWITCH:
            raise CampaignServiceError("Campaign system is currently disabled (kill switch active)")
    
    @staticmethod
    def validate_template(template: NotificationTemplateModel) -> None:
        """Validate that template exists and is active"""
        if not template:
            raise CampaignServiceError("Template is required")
        
        if not template.is_active:
            raise CampaignServiceError(f"Template '{template.name}' is not active")
    
    @staticmethod
    def validate_template_variables(template: NotificationTemplateModel, variables: Dict[str, Any]) -> None:
        """Validate that all required template variables are provided"""
        if not template:
            raise CampaignServiceError("Template is required")
        
        required_vars = template.get_required_variables()
        missing_params = set(required_vars) - set(variables.keys())
        if missing_params:
            raise CampaignServiceError(
                f"Missing required template variables: {', '.join(missing_params)}. "
                f"Required: {', '.join(required_vars)}"
            )
    
    @staticmethod
    def render_template(template: NotificationTemplateModel, variables: Dict[str, Any]) -> Dict[str, str]:
        """Render notification template with variables"""
        if not template:
            raise CampaignServiceError("Template is required")
        
        # Extract all {{param}} placeholders
        title_vars = set(re.findall(r'\{\{(\w+)\}\}', template.title))
        body_vars = set(re.findall(r'\{\{(\w+)\}\}', template.body))
        all_required_vars = title_vars | body_vars
        
        # Validate all required variables are provided
        missing_params = all_required_vars - set(variables.keys())
        if missing_params:
            raise CampaignServiceError(
                f"Missing required template variables: {', '.join(missing_params)}"
            )
        
        # Render title and body
        rendered_title = template.title
        rendered_body = template.body
        
        for param, value in variables.items():
            placeholder = f"{{{{{param}}}}}"
            rendered_title = rendered_title.replace(placeholder, str(value))
            rendered_body = rendered_body.replace(placeholder, str(value))
        
        # Verify no unreplaced placeholders remain
        remaining_title = re.findall(r'\{\{(\w+)\}\}', rendered_title)
        remaining_body = re.findall(r'\{\{(\w+)\}\}', rendered_body)
        if remaining_title or remaining_body:
            raise CampaignServiceError(
                f"Template has unreplaced placeholders: "
                f"title={remaining_title}, body={remaining_body}"
            )
        
        return {
            'title': rendered_title,
            'body': rendered_body,
            'target_screen': template.target_screen,
            'type': template.notification_type,
        }
    
    @staticmethod
    def preview_campaign(
        campaign: Campaign,
        user: User
    ) -> Dict[str, Any]:
        """
        Preview campaign audience without sending notifications.
        
        This is MANDATORY before sending any campaign.
        """
        CampaignService.validate_permissions(user)
        
        try:
            # Validate template
            if not campaign.template:
                raise CampaignServiceError("Campaign must have a template selected")
            CampaignService.validate_template(campaign.template)
            CampaignService.validate_template_variables(
                campaign.template,
                campaign.template_variables
            )
            
            # Validate and preview audience
            preview_result = RuleEngine.preview_audience(campaign.audience_rules)
            
            # Update campaign with preview info
            campaign.preview_count = preview_result['count']
            campaign.preview_computed_at = timezone.now()
            campaign.status = 'previewed'
            campaign.save(update_fields=['preview_count', 'preview_computed_at', 'status', 'updated_at'])
            
            # Audit log
            try:
                from audit.models import AuditLog
                AuditLog.log_action(
                    user=user,
                    action='campaign_preview',
                    object_type='Campaign',
                    object_id=campaign.id,
                    payload={
                        'campaign_name': campaign.name,
                        'preview_count': preview_result['count'],
                        'audience_description': preview_result.get('human_readable', '')
                    },
                    severity='medium'
                )
            except Exception:
                pass  # Don't fail if audit logging fails
            
            return preview_result
            
        except RuleEngineError as e:
            raise CampaignServiceError(f"Invalid audience rules: {str(e)}")
        except Exception as e:
            logger.error(f"Error previewing campaign {campaign.id}: {str(e)}", exc_info=True)
            raise CampaignServiceError(f"Failed to preview campaign: {str(e)}")
    
    @staticmethod
    def execute_campaign(
        campaign: Campaign,
        user: User,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Execute a campaign - send notifications to all matching users.
        
        IDEMPOTENCY RULE:
        - Campaign can only be executed once
        - Uses atomic database transaction to transition status from draft/previewed/scheduled → sending
        - Fails loudly if campaign is already sent or sending (prevents duplicate sends)
        - Even if network retries occur or admin clicks twice, duplicate execution is prevented
        
        Args:
            campaign: Campaign to execute
            user: Admin user executing the campaign
            force: Skip validation (only for retries, not recommended)
            
        Returns:
            Dict with execution results
            
        Raises:
            CampaignServiceError: If campaign cannot be executed (already sent, invalid state, etc.)
        """
        CampaignService.validate_permissions(user)
        
        # IDEMPOTENCY CHECK: Fail loudly if already executed
        if campaign.status in ['sent', 'sending']:
            raise CampaignServiceError(
                f"Campaign has already been executed (status: {campaign.status}). "
                f"Campaigns can only be sent once. Campaign was sent at {campaign.sent_at}. "
                f"Create a new campaign if you need to send similar notifications."
            )
        
        # Validate campaign can be sent
        if not force and not campaign.can_be_executed:
            if campaign.preview_count is None:
                raise CampaignServiceError(
                    "Campaign must be previewed before sending. Please preview the campaign first."
                )
            raise CampaignServiceError(
                f"Cannot send campaign in status '{campaign.status}'. "
                f"Campaign must be in 'draft', 'previewed', or 'scheduled' status."
            )
        
        # Mandatory preview check
        if campaign.preview_count is None:
            raise CampaignServiceError(
                "Campaign must be previewed before sending. Please preview the campaign first."
            )
        
        # Rate limiting check
        if campaign.preview_count > MAX_USERS_PER_CAMPAIGN:
            raise CampaignServiceError(
                f"Campaign targets {campaign.preview_count} users, which exceeds "
                f"maximum of {MAX_USERS_PER_CAMPAIGN} users per campaign. "
                f"Please refine audience rules."
            )
        
        # Validate template
        if not campaign.template:
            raise CampaignServiceError("Campaign must have a template selected")
        CampaignService.validate_template(campaign.template)
        CampaignService.validate_template_variables(
            campaign.template,
            campaign.template_variables
        )
        
        # ATOMIC STATUS TRANSITION: Prevent duplicate execution
        # Use select_for_update to lock the row and ensure only one execution succeeds
        with transaction.atomic():
            # Re-fetch campaign with row lock to prevent concurrent execution
            locked_campaign = Campaign.objects.select_for_update().get(pk=campaign.pk)
            
            # Double-check idempotency after acquiring lock
            if locked_campaign.status in ['sent', 'sending']:
                raise CampaignServiceError(
                    f"Campaign is already being executed or has been executed (status: {locked_campaign.status}). "
                    f"Another process may have started execution. Duplicate execution prevented."
                )
            
            # Atomic transition to 'sending' status
            locked_campaign.status = 'sending'
            locked_campaign.sent_by = user
            locked_campaign.sent_at = timezone.now()
            locked_campaign.save(update_fields=['status', 'sent_by', 'sent_at', 'updated_at'])
        
        # Use the locked campaign instance for rest of execution
        campaign = locked_campaign
        
        # Get audience
        try:
            base_qs = UserProfile.objects.all()
            audience_qs = RuleEngine.apply_rules(base_qs, campaign.audience_rules)
            audience_count = audience_qs.count()
        except RuleEngineError as e:
            campaign.status = 'failed'
            campaign.execution_metadata = {'error': str(e)}
            campaign.save(update_fields=['status', 'execution_metadata', 'updated_at'])
            raise CampaignServiceError(f"Failed to apply audience rules: {str(e)}")
        
        # Execute campaign in batches
        total_sent = 0
        total_failed = 0
        errors = []
        
        try:
            # Render template
            rendered = CampaignService.render_template(
                campaign.template,
                campaign.template_variables
            )
            
            # Send in batches
            dispatcher = PushNotificationDispatcher()
            
            for offset in range(0, audience_count, BATCH_SIZE):
                batch_qs = audience_qs[offset:offset + BATCH_SIZE]
                
                for user_profile in batch_qs:
                    try:
                        with transaction.atomic():
                            # Prepare push data
                            push_data = {
                                'target_screen': rendered['target_screen'],
                                'campaign_id': str(campaign.uuid),
                                'template_key': campaign.template.key,
                                **campaign.template_variables
                            }
                            
                            # Send via push dispatcher (it will create notification record)
                            dispatch_result = dispatcher.send_notification(
                                recipient=user_profile,
                                notification_type=rendered['type'],
                                title=rendered['title'],
                                message=rendered['body'],
                                data=push_data,
                                reference_type='Campaign',
                                reference_id=campaign.id
                            )
                            
                            # Find the notification that dispatcher created and link to campaign
                            # The dispatcher saves notification with reference_type='Campaign', reference_id=campaign.id
                            notification = Notification.objects.filter(
                                recipient=user_profile,
                                type=rendered['type'],
                                reference_type='Campaign',
                                reference_id=campaign.id
                            ).order_by('-created_at').first()
                            
                            if notification:
                                # Update notification with campaign link
                                notification.campaign = campaign
                                notification.metadata.update(push_data)
                                notification.save(update_fields=['campaign', 'metadata', 'updated_at'])
                            else:
                                # Fallback: create notification if dispatcher didn't (shouldn't happen)
                                notification = Notification.objects.create(
                                    recipient=user_profile,
                                    type=rendered['type'],
                                    title=rendered['title'],
                                    message=rendered['body'],
                                    metadata=push_data,
                                    campaign=campaign,
                                    reference_type='Campaign',
                                    reference_id=campaign.id
                                )
                            
                            # Create execution record
                            sent_successfully = dispatch_result.get('push_sent', False) or dispatch_result.get('notification_saved', False)
                            CampaignExecution.objects.create(
                                campaign=campaign,
                                notification=notification,
                                user_profile=user_profile,
                                sent_successfully=sent_successfully,
                                delivered_at=timezone.now() if sent_successfully else None,
                                error_message='' if sent_successfully else '; '.join(dispatch_result.get('errors', []))
                            )
                            
                            total_sent += 1
                            
                    except Exception as e:
                        logger.error(
                            f"Error sending notification to user {user_profile.id} "
                            f"in campaign {campaign.id}: {str(e)}",
                            exc_info=True
                        )
                        
                        # Create failed execution record
                        try:
                            CampaignExecution.objects.create(
                                campaign=campaign,
                                user_profile=user_profile,
                                sent_successfully=False,
                                error_message=str(e)
                            )
                        except Exception:
                            pass  # Avoid double errors
                        
                        total_failed += 1
                        errors.append({
                            'user_id': user_profile.id,
                            'error': str(e)
                        })
                
                # Log batch progress
                logger.info(
                    f"Campaign {campaign.id} batch progress: "
                    f"{offset + len(batch_qs)}/{audience_count} processed"
                )
            
            # Update campaign with results
            campaign.status = 'sent'
            campaign.total_sent = total_sent
            campaign.total_failed = total_failed
            campaign.execution_metadata = {
                'errors': errors[:10],  # Keep first 10 errors
                'error_count': len(errors),
                'batch_size': BATCH_SIZE
            }
            campaign.save(update_fields=[
                'status', 'total_sent', 'total_failed', 'execution_metadata', 'updated_at'
            ])
            
            logger.info(
                f"Campaign {campaign.id} completed: "
                f"{total_sent} sent, {total_failed} failed"
            )
            
            # Audit log
            try:
                from audit.models import AuditLog
                AuditLog.log_action(
                    user=user,
                    action='campaign_execute',
                    object_type='Campaign',
                    object_id=campaign.id,
                    payload={
                        'campaign_name': campaign.name,
                        'total_sent': total_sent,
                        'total_failed': total_failed,
                        'audience_size': audience_count,
                        'error_count': len(errors)
                    },
                    severity='high',
                    is_successful=total_failed == 0
                )
            except Exception:
                pass  # Don't fail if audit logging fails
            
            return {
                'campaign_id': campaign.id,
                'total_sent': total_sent,
                'total_failed': total_failed,
                'errors': errors[:10] if errors else []
            }
            
        except Exception as e:
            logger.error(f"Campaign {campaign.id} execution failed: {str(e)}", exc_info=True)
            campaign.status = 'failed'
            campaign.execution_metadata = {'error': str(e)}
            campaign.save(update_fields=['status', 'execution_metadata', 'updated_at'])
            raise CampaignServiceError(f"Campaign execution failed: {str(e)}")
    
    @staticmethod
    def cancel_campaign(campaign: Campaign, user: User, reason: str = "") -> None:
        """Cancel a campaign if it hasn't been sent yet"""
        CampaignService.validate_permissions(user)
        
        if campaign.status in ['sent', 'sending']:
            raise CampaignServiceError("Cannot cancel campaign that is already sent or sending")
        
        if campaign.status == 'cancelled':
            raise CampaignServiceError("Campaign is already cancelled")
        
        campaign.cancel(user, reason)
        
        # Audit log
        try:
            from audit.models import AuditLog
            AuditLog.log_action(
                user=user,
                action='campaign_cancel',
                object_type='Campaign',
                object_id=campaign.id,
                payload={
                    'campaign_name': campaign.name,
                    'previous_status': campaign.status,
                    'reason': reason
                },
                severity='medium'
            )
        except Exception:
            pass  # Don't fail if audit logging fails