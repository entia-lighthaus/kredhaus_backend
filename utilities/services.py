"""
Service layer for utilities processing pipeline.
Handles conversion of raw meter readings → usage records → bills.
"""

from datetime import timedelta
from django.utils import timezone
from .models import UtilityMeterReading, UtilityUsageRecord, UtilityRate


def process_meter_reading(meter_reading):
    """
    Convert raw meter reading → consumption record → bill.
    Works for BOTH smart meter and manual input.
    
    Args:
        meter_reading: UtilityMeterReading instance
    
    Returns:
        UtilityUsageRecord if successful, None if failed
    """
    try:
        account = meter_reading.account
        consumption = meter_reading.calculated_consumption
        
        # Determine appropriate rate from tariff band selection
        rate = None

        # 1) Explicit tariff band selected on the reading
        if meter_reading.tariff_band:
            rate = UtilityRate.objects.filter(
                utility=account.utility,
                band=meter_reading.tariff_band,
                is_active=True,
                effective_from__lte=timezone.now().date()
            ).order_by('-effective_from').first()

        # 2) Account-level provider tariff band
        if not rate and hasattr(account, 'meter_provider') and account.meter_provider.tariff_band:
            rate = UtilityRate.objects.filter(
                utility=account.utility,
                band=account.meter_provider.tariff_band,
                is_active=True,
                effective_from__lte=timezone.now().date()
            ).order_by('-effective_from').first()

        # 3) Automatic matching by consumption range
        if not rate:
            candidates = UtilityRate.objects.filter(
                utility=account.utility,
                is_active=True,
                effective_from__lte=timezone.now().date()
            ).order_by('-effective_from')
            for candidate in candidates:
                if candidate.contains_consumption(consumption):
                    rate = candidate
                    break
            if not rate and candidates.exists():
                rate = candidates.first()

        if not rate:
            raise ValueError(f"No active rate found for {account.utility.display_name}")

        # Calculate costs
        variable_cost = consumption * rate.rate
        amount_due = variable_cost + rate.fixed_charge
        
        # Determine billing period (typically last 30 days)
        period_end = meter_reading.reading_date
        period_start = period_end - timedelta(days=30)
        
        # Create usage record
        usage_record = UtilityUsageRecord.objects.create(
            meter_reading=meter_reading,
            account=account,
            consumption=consumption,
            unit=rate.unit,
            period_start=period_start,
            period_end=period_end,
            unit_rate=rate.rate,
            variable_cost=variable_cost,
            fixed_charge=rate.fixed_charge,
            amount_due=amount_due,
            is_billed=False
        )
        
        # Mark meter reading as processed
        meter_reading.is_processed = True
        meter_reading.save(update_fields=['is_processed'])
        
        return usage_record
    
    except Exception as e:
        print(f"Error processing meter reading {meter_reading.id}: {str(e)}")
        return None


def confirm_meter_reading(meter_reading):
    """
    Confirm a manual meter reading (e.g., after tenant review).
    This locks in the consumption and triggers bill generation.
    
    Args:
        meter_reading: UtilityMeterReading instance to confirm
    
    Returns:
        UtilityUsageRecord if successful
    """
    if meter_reading.source != 'manual':
        raise ValueError("Only manual readings need confirmation")
    
    # Process the reading
    usage_record = process_meter_reading(meter_reading)
    
    if usage_record:
        # Mark as confirmed
        meter_reading.is_confirmed = True
        meter_reading.save(update_fields=['is_confirmed'])
        
        # Update last reading date on meter provider
        meter_reading.account.meter_provider.last_reading_date = meter_reading.reading_date
        meter_reading.account.meter_provider.save(update_fields=['last_reading_date'])
    
    return usage_record


def validate_meter_reading(meter_reading):
    """
    Validate a meter reading for anomalies.
    
    Returns:
        tuple: (is_valid: bool, errors: list)
    """
    errors = []
    
    # Check consumption is not negative
    if meter_reading.calculated_consumption < 0:
        errors.append("Consumption cannot be negative")
    
    # Check if reading date is in the future
    if meter_reading.reading_date > timezone.now().date():
        errors.append("Reading date cannot be in the future")
    
    # Check for duplicate readings (same day)
    existing = UtilityMeterReading.objects.filter(
        account=meter_reading.account,
        reading_date=meter_reading.reading_date
    ).exclude(id=meter_reading.id)
    
    if existing.exists():
        errors.append("A reading already exists for this date")
    
    # Check meter reading consistency (current >= previous)
    if (meter_reading.current_reading is not None and 
        meter_reading.previous_reading is not None):
        if meter_reading.current_reading < meter_reading.previous_reading:
            errors.append("Current reading cannot be less than previous reading")
    
    return (len(errors) == 0, errors)
