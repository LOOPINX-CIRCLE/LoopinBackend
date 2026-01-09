"""
OneSignal REST API client for sending push notifications.

This is a low-level client with NO business logic.
Handles HTTP communication with OneSignal API only.
"""
import os
import logging
import httpx
from typing import List, Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class OneSignalClient:
    """
    Low-level OneSignal REST API client.
    
    Responsibilities:
    - Send push notifications via OneSignal REST API
    - Handle HTTP errors gracefully
    - Never raise fatal exceptions
    - NO business logic
    """
    
    ONESIGNAL_API_URL = "https://onesignal.com/api/v1/notifications"
    
    def __init__(self):
        """Initialize OneSignal client with credentials from environment."""
        self.app_id = os.getenv('ONESIGNAL_APP_ID')
        self.rest_api_key = os.getenv('ONESIGNAL_REST_API_KEY')
        
        if not self.app_id or not self.rest_api_key:
            logger.warning(
                "OneSignal credentials not configured. "
                "ONESIGNAL_APP_ID and ONESIGNAL_REST_API_KEY must be set."
            )
            self.app_id = None
            self.rest_api_key = None
    
    def send_push(
        self,
        player_ids: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Send push notification to multiple player IDs.
        
        Args:
            player_ids: List of OneSignal player IDs (devices)
            title: Notification title
            body: Notification message body
            data: Optional payload data dict
            
        Returns:
            Dict with 'success' (bool), 'response' (dict if success), 
            'errors' (list if failed), 'invalid_player_ids' (list)
            
        Never raises exceptions - returns error dict on failure.
        """
        if not self.app_id or not self.rest_api_key:
            logger.warning("OneSignal credentials not configured. Skipping push notification.")
            return {
                'success': False,
                'errors': ['OneSignal credentials not configured'],
                'invalid_player_ids': [],
            }
        
        if not player_ids:
            logger.debug("No player IDs provided. Skipping push notification.")
            return {
                'success': True,
                'response': {'recipients': 0},
                'invalid_player_ids': [],
            }
        
        payload = {
            'app_id': self.app_id,
            'include_player_ids': player_ids,
            'headings': {'en': title},
            'contents': {'en': body},
        }
        
        if data:
            payload['data'] = data
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Basic {self.rest_api_key}',
        }
        
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    self.ONESIGNAL_API_URL,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                response_data = response.json()
                
                logger.info(
                    f"OneSignal push sent successfully. "
                    f"Recipients: {response_data.get('recipients', 0)}, "
                    f"Player IDs: {len(player_ids)}"
                )
                
                # Extract invalid player IDs from response
                invalid_player_ids = response_data.get('errors', {}).get('invalid_player_ids', [])
                
                return {
                    'success': True,
                    'response': response_data,
                    'invalid_player_ids': invalid_player_ids,
                }
                
        except httpx.HTTPStatusError as e:
            error_detail = f"HTTP {e.response.status_code}"
            try:
                error_body = e.response.json()
                error_detail += f": {error_body}"
            except Exception:
                error_detail += f": {e.response.text[:200]}"
            
            logger.error(f"OneSignal API HTTP error: {error_detail}")
            
            return {
                'success': False,
                'errors': [error_detail],
                'invalid_player_ids': [],
            }
            
        except httpx.RequestError as e:
            logger.error(f"OneSignal API request error: {str(e)}")
            return {
                'success': False,
                'errors': [f"Request error: {str(e)}"],
                'invalid_player_ids': [],
            }
            
        except Exception as e:
            logger.error(f"Unexpected error sending OneSignal push: {str(e)}", exc_info=True)
            return {
                'success': False,
                'errors': [f"Unexpected error: {str(e)}"],
                'invalid_player_ids': [],
            }

