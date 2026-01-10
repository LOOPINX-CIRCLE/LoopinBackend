"""
Rule Engine for Campaign Audience Selection

This module safely translates JSON rule structures into Django ORM queries.
It prevents SQL injection and ensures only safe, predefined field/operator combinations are allowed.

Security Rules:
- No raw SQL
- No freeform Python execution
- Only whitelisted fields and operators
- All queries go through Django ORM
- Preview mode always available
"""

import logging
from typing import Dict, List, Any, Optional
from django.db.models import Q, QuerySet
from django.core.exceptions import ValidationError
from users.models import UserProfile

logger = logging.getLogger(__name__)


# Whitelist of allowed fields for rule engine
ALLOWED_FIELDS = {
    # Profile fields
    'profile_completed': {
        'type': 'boolean',
        'path': lambda qs: qs,  # Profile completion is computed, handled specially
        'operators': ['=', '!=']
    },
    'location': {
        'type': 'string',
        'path': lambda qs: qs,
        'operators': ['=', '!=', 'contains', 'icontains']
    },
    'is_verified': {
        'type': 'boolean',
        'path': lambda qs: qs,
        'operators': ['=', '!=']
    },
    'is_active': {
        'type': 'boolean',
        'path': lambda qs: qs,
        'operators': ['=', '!=']
    },
    # Interest fields
    'interest': {
        'type': 'many_to_many',
        'path': lambda qs: qs.filter(event_interests__isnull=False),
        'operators': ['contains', 'exact']
    },
    # Activity fields (computed)
    'has_attended_event': {
        'type': 'computed',
        'path': lambda qs: qs,  # Handled specially
        'operators': ['=', '!=']
    },
    'has_active_devices': {
        'type': 'computed',
        'path': lambda qs: qs.filter(devices__is_active=True).distinct(),
        'operators': ['=', '!=']
    },
}

ALLOWED_OPERATORS = {
    '=': lambda field, value: Q(**{field: value}),
    '!=': lambda field, value: ~Q(**{field: value}),
    'contains': lambda field, value: Q(**{f"{field}__contains": value}),
    'icontains': lambda field, value: Q(**{f"{field}__icontains": value}),
    'exact': lambda field, value: Q(**{f"{field}__exact": value}),
    'in': lambda field, value: Q(**{f"{field}__in": value}),
}


class RuleEngineError(ValidationError):
    """Custom exception for rule engine errors"""
    pass


class RuleEngine:
    """
    Safe rule engine that translates JSON rules to Django ORM queries.
    
    Rule Structure:
    {
        "all": [  # AND logic
            {"field": "profile_completed", "op": "=", "value": false},
            {"field": "location", "op": "=", "value": "Bangalore"}
        ],
        "any": [  # OR logic (optional)
            {"field": "interest", "op": "contains", "value": "music"}
        ]
    }
    """
    
    @staticmethod
    def validate_rule_structure(rules: Dict[str, Any]) -> None:
        """Validate that rule structure is well-formed"""
        if not isinstance(rules, dict):
            raise RuleEngineError("Rules must be a JSON object")
        
        if 'all' not in rules and 'any' not in rules:
            raise RuleEngineError("Rules must contain 'all' or 'any' key")
        
        for key in ['all', 'any']:
            if key in rules:
                if not isinstance(rules[key], list):
                    raise RuleEngineError(f"'{key}' must be a list")
                for rule in rules[key]:
                    if not isinstance(rule, dict):
                        raise RuleEngineError(f"Each rule in '{key}' must be an object")
                    if not all(k in rule for k in ['field', 'op', 'value']):
                        raise RuleEngineError(f"Rule must contain 'field', 'op', and 'value'")
    
    @staticmethod
    def validate_field_and_operator(field: str, operator: str) -> None:
        """Validate that field and operator are in whitelist"""
        if field not in ALLOWED_FIELDS:
            raise RuleEngineError(
                f"Field '{field}' is not allowed. Allowed fields: {', '.join(ALLOWED_FIELDS.keys())}"
            )
        
        if operator not in ALLOWED_FIELDS[field]['operators']:
            raise RuleEngineError(
                f"Operator '{operator}' is not allowed for field '{field}'. "
                f"Allowed operators: {', '.join(ALLOWED_FIELDS[field]['operators'])}"
            )
    
    @staticmethod
    def compute_profile_completion(user_profile: UserProfile) -> bool:
        """Compute if profile is completed (has all required fields)"""
        required_fields = ['name', 'location', 'gender', 'birth_date', 'profile_pictures']
        for field in required_fields:
            value = getattr(user_profile, field, None)
            if field == 'profile_pictures':
                if not value or len(value) < 1:  # MIN_PROFILE_PICTURES
                    return False
            elif not value:
                return False
        
        # Check interests (1-5 required)
        interest_count = user_profile.event_interests.count()
        if interest_count < 1 or interest_count > 5:
            return False
        
        return True
    
    @staticmethod
    def build_query_for_rule(rule: Dict[str, Any], queryset: QuerySet) -> QuerySet:
        """Build Django ORM query for a single rule"""
        field = rule['field']
        operator = rule['op']
        value = rule['value']
        
        # Validate field and operator
        RuleEngine.validate_field_and_operator(field, operator)
        
        field_config = ALLOWED_FIELDS[field]
        
        # Handle computed fields
        if field == 'profile_completed':
            # This requires filtering after fetching, handled in apply_rules
            return queryset
        
        if field == 'has_attended_event':
            # Check if user has any attendance records
            if operator == '=' and value is True:
                from attendances.models import AttendanceRecord
                user_ids_with_attendance = AttendanceRecord.objects.values_list('user_profile_id', flat=True).distinct()
                return queryset.filter(id__in=user_ids_with_attendance)
            elif operator == '=' and value is False:
                from attendances.models import AttendanceRecord
                user_ids_with_attendance = AttendanceRecord.objects.values_list('user_profile_id', flat=True).distinct()
                return queryset.exclude(id__in=user_ids_with_attendance)
        
        if field == 'interest':
            # Many-to-many relationship
            if operator == 'contains' or operator == 'exact':
                return queryset.filter(event_interests__name__icontains=value).distinct()
            elif operator == '!=':
                return queryset.exclude(event_interests__name__icontains=value).distinct()
        
        # Handle boolean fields
        if field_config['type'] == 'boolean':
            if isinstance(value, str):
                value = value.lower() in ('true', '1', 'yes')
            elif not isinstance(value, bool):
                value = bool(value)
        
        # Standard field query
        if operator not in ALLOWED_OPERATORS:
            raise RuleEngineError(f"Unsupported operator: {operator}")
        
        query_func = ALLOWED_OPERATORS[operator]
        q_obj = query_func(field, value)
        
        return queryset.filter(q_obj)
    
    @staticmethod
    def apply_rules(queryset: QuerySet, rules: Dict[str, Any]) -> QuerySet:
        """
        Apply audience rules to a queryset and return filtered queryset.
        
        AUDIENCE LOGIC EXPLICIT RULES:
        - ALL rules use AND logic (user must match ALL conditions)
        - ANY rules use OR logic (user must match ANY of the conditions)
        - Final result: (ALL conditions) AND (ANY conditions)
        - Example: (profile_completed=true AND location=Bangalore) AND (interest=Music OR interest=Dance)
        - Event interests always use OR logic (users with ANY selected interest)
        - Other filters always use AND logic
        
        Args:
            queryset: Base queryset (typically UserProfile.objects.all())
            rules: Rule structure with 'all' and/or 'any' keys
            
        Returns:
            Filtered queryset matching all rules
        """
        RuleEngine.validate_rule_structure(rules)
        
        # Start with base queryset
        result_qs = queryset
        
        # Apply 'all' rules (AND logic)
        # All conditions in 'all' must be true (profile_completed=true AND is_verified=true AND location=Bangalore, etc.)
        if 'all' in rules and rules['all']:
            for rule in rules['all']:
                result_qs = RuleEngine.build_query_for_rule(rule, result_qs)
        
        # Apply 'any' rules (OR logic) - combine with AND of 'all' rules
        # Users must match ANY of the conditions in 'any' (interest=Music OR interest=Dance OR interest=Sports)
        # Final: (ALL conditions) AND (ANY of the 'any' conditions)
        if 'any' in rules and rules['any']:
            or_queries = []
            for rule in rules['any']:
                rule_qs = RuleEngine.build_query_for_rule(rule, queryset)
                or_queries.append(rule_qs)
            
            if or_queries:
                # Combine OR queries
                from django.db.models import Q
                combined_q = Q()
                for q in or_queries:
                    combined_q |= Q(pk__in=q.values_list('pk', flat=True))
                result_qs = result_qs.filter(combined_q)
        
        # Handle computed fields that require post-filtering
        # Profile completion check
        if any(rule.get('field') == 'profile_completed' for rule in rules.get('all', [])):
            profile_completed_rule = next(
                (r for r in rules.get('all', []) if r.get('field') == 'profile_completed'),
                None
            )
            if profile_completed_rule:
                target_value = profile_completed_rule['value']
                if isinstance(target_value, str):
                    target_value = target_value.lower() in ('true', '1', 'yes')
                
                # Filter in Python (unavoidable for computed fields)
                matching_ids = [
                    profile.id for profile in result_qs
                    if RuleEngine.compute_profile_completion(profile) == target_value
                ]
                result_qs = result_qs.filter(id__in=matching_ids)
        
        # Only include users with active devices (for push notifications)
        result_qs = result_qs.filter(devices__is_active=True).distinct()
        
        return result_qs
    
    @staticmethod
    def preview_audience(rules: Dict[str, Any], limit: int = 100) -> Dict[str, Any]:
        """
        Preview audience matching rules without sending notifications.
        
        Returns:
            Dict with 'count', 'sample_user_ids', 'human_readable'
        """
        try:
            base_qs = UserProfile.objects.all()
            filtered_qs = RuleEngine.apply_rules(base_qs, rules)
            
            total_count = filtered_qs.count()
            sample_ids = list(filtered_qs[:limit].values_list('id', flat=True))
            
            # Generate human-readable description
            human_readable = RuleEngine.generate_human_readable_description(rules)
            
            return {
                'count': total_count,
                'sample_user_ids': sample_ids,
                'human_readable': human_readable,
                'has_more': total_count > limit
            }
        except Exception as e:
            logger.error(f"Error previewing audience: {str(e)}", exc_info=True)
            raise RuleEngineError(f"Failed to preview audience: {str(e)}")
    
    @staticmethod
    def generate_human_readable_description(rules: Dict[str, Any]) -> str:
        """Generate human-readable description of audience rules"""
        descriptions = []
        
        if 'all' in rules and rules['all']:
            all_descriptions = []
            for rule in rules['all']:
                field = rule['field']
                op = rule['op']
                value = rule['value']
                
                if field == 'profile_completed':
                    all_descriptions.append("incomplete profile" if not value else "complete profile")
                elif field == 'location':
                    all_descriptions.append(f"location = {value}")
                elif field == 'interest':
                    all_descriptions.append(f"interested in '{value}'")
                elif field == 'has_attended_event':
                    all_descriptions.append("has attended events" if value else "has not attended events")
                elif field == 'is_verified':
                    all_descriptions.append("verified users" if value else "unverified users")
                else:
                    all_descriptions.append(f"{field} {op} {value}")
            
            if all_descriptions:
                descriptions.append("Users with " + " AND ".join(all_descriptions))
        
        if 'any' in rules and rules['any']:
            any_descriptions = []
            for rule in rules['any']:
                field = rule['field']
                value = rule['value']
                if field == 'interest':
                    any_descriptions.append(f"'{value}'")
            
            if any_descriptions:
                descriptions.append(" AND interested in (" + " OR ".join(any_descriptions) + ")")
        
        return " ".join(descriptions) if descriptions else "All users with active devices"