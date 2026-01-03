"""
Core models for system-wide configuration and shared functionality.
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP

from .base_models import TimeStampedModel


class PlatformFeeConfig(TimeStampedModel):
    """
    Singleton model for platform fee configuration.
    
    Only one instance should exist in the database. The platform fee
    is configurable by admins and affects all financial calculations.
    
    Business Logic:
    - Platform fee is a percentage (0-100) of the base ticket fare
    - Fee is added on top of base fare (buyer pays: base + fee)
    - Host earns full base fare (no deduction)
    - Platform collects the fee from buyers
    
    Example:
    - Base ticket fare: ₹100
    - Platform fee: 10%
    - Buyer pays: ₹110 (₹100 + ₹10)
    - Host earns: ₹100 (no deduction)
    - Platform collects: ₹10 per ticket
    """
    
    # Singleton identifier (always 1)
    id = models.IntegerField(primary_key=True, default=1, editable=False)
    
    fee_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('10.00'),
        help_text="Platform fee percentage (0.00 to 100.00). Example: 10.00 = 10%"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this platform fee configuration is currently active"
    )
    
    description = models.TextField(
        blank=True,
        max_length=500,
        help_text="Optional description or notes about this fee configuration"
    )
    
    updated_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='platform_fee_configs',
        help_text="User who last updated this configuration"
    )
    
    class Meta:
        verbose_name = "Platform Fee Configuration"
        verbose_name_plural = "Platform Fee Configuration"
        db_table = 'core_platform_fee_config'
    
    def __str__(self):
        return f"Platform Fee: {self.fee_percentage}%"
    
    def clean(self):
        """Validate platform fee percentage"""
        if self.fee_percentage < Decimal('0.00'):
            raise ValidationError({
                'fee_percentage': 'Platform fee cannot be negative.'
            })
        if self.fee_percentage > Decimal('100.00'):
            raise ValidationError({
                'fee_percentage': 'Platform fee cannot exceed 100%.'
            })
    
    def save(self, *args, **kwargs):
        """Override save to enforce singleton pattern and clear cache"""
        # Enforce singleton: only one instance with id=1
        self.id = 1
        
        # Validate before saving
        self.full_clean()
        
        # Clear cache when configuration changes
        cache.delete('platform_fee_percentage')
        cache.delete('platform_fee_decimal')
        
        super().save(*args, **kwargs)
    
    @classmethod
    def get_current_config(cls):
        """
        Get the current active platform fee configuration.
        Uses caching for performance.
        
        Returns:
            PlatformFeeConfig instance or None if not configured
        
        Raises:
            PlatformFeeConfig.DoesNotExist: If no configuration exists
        """
        # Try cache first
        cached = cache.get('platform_fee_config')
        if cached is not None:
            return cached
        
        # Get from database
        try:
            config = cls.objects.get(id=1, is_active=True)
        except cls.DoesNotExist:
            # Create default if doesn't exist
            config = cls.objects.create(
                id=1,
                fee_percentage=Decimal('10.00'),
                is_active=True,
                description="Default platform fee configuration"
            )
        
        # Cache for 1 hour
        cache.set('platform_fee_config', config, 3600)
        return config
    
    @classmethod
    def get_fee_percentage(cls) -> Decimal:
        """
        Get current platform fee percentage (0-100).
        
        Returns:
            Decimal: Fee percentage (e.g., Decimal('10.00') for 10%)
        
        Raises:
            RuntimeError: If configuration is not available
        """
        cache_key = 'platform_fee_percentage'
        cached = cache.get(cache_key)
        if cached is not None:
            return Decimal(str(cached))
        
        config = cls.get_current_config()
        percentage = config.fee_percentage
        
        # Cache for 1 hour
        cache.set(cache_key, float(percentage), 3600)
        return percentage
    
    @classmethod
    def get_fee_decimal(cls) -> Decimal:
        """
        Get current platform fee as decimal multiplier (0.00-1.00).
        Use this for calculations: base_fare * fee_decimal
        
        Returns:
            Decimal: Fee as decimal (e.g., Decimal('0.10') for 10%)
        
        Raises:
            RuntimeError: If configuration is not available
        """
        cache_key = 'platform_fee_decimal'
        cached = cache.get(cache_key)
        if cached is not None:
            return Decimal(str(cached))
        
        percentage = cls.get_fee_percentage()
        decimal_value = percentage / Decimal('100.00')
        
        # Cache for 1 hour
        cache.set(cache_key, float(decimal_value), 3600)
        return decimal_value
    
    @classmethod
    def calculate_platform_fee(cls, base_fare: Decimal, quantity: int = 1) -> Decimal:
        """
        Calculate platform fee amount for given base fare and quantity.
        
        Args:
            base_fare: Base ticket fare per unit
            quantity: Number of tickets/units (default: 1)
        
        Returns:
            Decimal: Total platform fee amount (rounded to 2 decimal places)
        
        Example:
            >>> config = PlatformFeeConfig.get_current_config()
            >>> fee = config.calculate_platform_fee(Decimal('100.00'), 5)
            >>> fee  # 10% of ₹100 × 5 = ₹50.00
            Decimal('50.00')
        """
        fee_decimal = cls.get_fee_decimal()
        total_fee = base_fare * fee_decimal * Decimal(quantity)
        
        # Round to 2 decimal places
        return total_fee.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @classmethod
    def calculate_final_price(cls, base_fare: Decimal) -> Decimal:
        """
        Calculate final price that buyer pays (base + platform fee).
        
        Args:
            base_fare: Base ticket fare
        
        Returns:
            Decimal: Final price including platform fee (rounded to 2 decimal places)
        
        Example:
            >>> config = PlatformFeeConfig.get_current_config()
            >>> final = config.calculate_final_price(Decimal('100.00'))
            >>> final  # ₹100 + 10% = ₹110.00
            Decimal('110.00')
        """
        fee_decimal = cls.get_fee_decimal()
        final_price = base_fare * (Decimal('1.00') + fee_decimal)
        
        # Round to 2 decimal places
        return final_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    def get_fee_percentage_display(self) -> str:
        """Get formatted fee percentage for display"""
        return f"{self.fee_percentage}%"
    
    def get_fee_decimal_display(self) -> str:
        """Get formatted fee decimal for display"""
        decimal_value = self.fee_percentage / Decimal('100.00')
        return f"{decimal_value:.4f}"

