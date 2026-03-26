# Utilities Module - Complete Guide

## Overview

The utilities module enables tenants to manage and track their utility accounts (Electricity, Gas, Water, Internet) within the Kredhaus app.

---

## Architecture

### Three Core Models

#### 1. **Utility** (Master Record)
Represents utility types available in your system.
- `name`: Choice field (electricity, gas, water, internet)
- `display_name`: Custom name shown in UI (e.g., "EEDC Power")
- `icon_color`: Hex color for UI (e.g., #FDB913 for yellow)
- `description`: Additional info
- `is_active`: Enable/disable utilities

#### 2. **UtilityAccount** (Tenant's Account)
Represents a specific tenant's account for a utility at a unit.
- Linked to `Unit` and `Utility` (unique together)
- Account details: account number, provider, account name
- Financial: current balance, last bill amount, bill due date
- Status: active, pending, inactive, suspended
- Audit: who connected it, last updated by

#### 3. **UtilityBill** (Invoice Record)
Individual bills for tracking payment history.
- Linked to `UtilityAccount`
- Bill reference, amount, status
- Dates: bill date, due date, paid date
- Status: pending, due, overdue, paid

---

## Database Schema

```
Unit
  ├── UtilityAccount (electricty, gas, water, internet)
  │     └── UtilityBill (multiple bills per account)
  └── Property
        └── Owner (User)
```

**Key Constraint**: Each `Unit` can only have ONE account per `Utility` type (unique_together).

---

## API Endpoints

### List Available Utilities
```
GET /api/v1/utilities/utilities/
```
Returns active utilities for user selection.
**Response:**
```json
[
  {
    "id": 1,
    "name": "electricity",
    "display_name": "EEDC Power",
    "icon_color": "#FDB913",
    "description": "Electricity service"
  }
]
```

### List User's Utility Accounts
```
GET /api/v1/utilities/accounts/
```
Returns accounts for units user has access to (as tenant or owner).
**Response:**
```json
[
  {
    "id": 5,
    "utility": {
      "id": 1,
      "name": "electricity",
      "display_name": "EEDC Power",
      "icon_color": "#FDB913"
    },
    "account_number": "ELEC-123456",
    "account_name": "John Doe",
    "provider": "EEDC",
    "status": "active",
    "current_balance": 2450.00,
    "last_bill_amount": 5000.00,
    "bill_due_date": "2026-04-15",
    "is_overdue": false,
    "days_until_due": 19,
    "connected_at": "2026-03-20T10:30:00Z",
    "bills": [...]
  }
]
```

### Create Utility Account
```
POST /api/v1/utilities/accounts/

{
  "unit_id": 12,
  "utility_id": 1,
  "account_number": "ELEC-123456",
  "account_name": "John Doe",
  "provider": "EEDC",
  "status": "active",
  "current_balance": 2450.00,
  "last_bill_amount": 5000.00,
  "bill_due_date": "2026-04-15"
}
```

The `connected_by` field is automatically set to the logged-in user's name.

### Get Accounts for Specific Unit
```
GET /api/v1/utilities/accounts/by_unit/?unit_id=12
```

### Get Bills for Account
```
GET /api/v1/utilities/accounts/{account_id}/bills/
```
Returns all bills for the account with status (pending, due, overdue, paid).

### Update Account
```
PUT /api/v1/utilities/accounts/{account_id}/

{
  "utility_id": 1,
  "account_number": "ELEC-654321",
  "current_balance": 3000.00,
  "status": "active"
}
```

### Mark Bill as Paid
```
POST /api/v1/utilities/accounts/{account_id}/mark_bill_paid/?bill_id=42
```

---

## Permissions

**Rule**: Users can only access accounts for:
- **As Tenant**: Units where they have an active/pending lease
- **As Owner**: Any units in their properties

**Custom Permission Class**: `CanManageUtilityAccounts`
- Checks user role and lease status
- Enforced on all CRUD operations

---

## Admin Interface

Access at `/admin/utilities/`

### Utility Admin
- Manage utility types
- Enable/disable utilities
- Customize display names and colors

### Utility Account Admin
- List all accounts with filters (status, utility, date)
- Inline bill management
- View calculated fields (is_overdue, days_until_due)
- Audit trail (who connected, who last updated)

### Utility Bill Admin
- Track all bills
- Filter by status and date
- See overdue indicators

---

## Usage Examples

### Example 1: Tenant Connecting Electricity Account

**React/Frontend Code:**
```javascript
// 1. Get available utilities
const utilities = await fetch('/api/v1/utilities/utilities/').then(r => r.json());

// 2. Tenant selects electricity and fills form
const newAccount = {
  unit_id: 5,  // Their unit
  utility_id: 1,  // Electricity
  account_number: "ELEC-123456",
  account_name: "John Doe",
  provider: "EEDC",
  status: "active",
  current_balance: 2450,
  last_bill_amount: 5000,
  bill_due_date: "2026-04-15"
};

// 3. Create account (connected_by auto-filled)
await fetch('/api/v1/utilities/accounts/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(newAccount)
});
```

### Example 2: Get All Utilities for Display
```javascript
const unitId = 5;
const accounts = await fetch(
  `/api/v1/utilities/accounts/by_unit/?unit_id=${unitId}`
).then(r => r.json());

// Now have: [electricity, gas, water, internet] for the unit
```

### Example 3: Check Overdue Bills
```javascript
const accounts = await fetch('/api/v1/utilities/accounts/').then(r => r.json());

accounts.forEach(account => {
  if (account.is_overdue) {
    console.log(`${account.utility.display_name} is overdue!`);
    console.log(`Days until due: ${account.days_until_due}`);
  }
});
```

---

## Admin Database Setup

Seed initial utilities in Django shell:
```python
from utilities.models import Utility

Utility.objects.create(
    name='electricity',
    display_name='EEDC Power',
    icon_color='#FDB913'
)

Utility.objects.create(
    name='gas',
    display_name='Lagos State Gas',
    icon_color='#FF6B35'
)

Utility.objects.create(
    name='water',
    display_name='Lagos State Water',
    icon_color='#00A8E8'
)

Utility.objects.create(
    name='internet',
    display_name='Spectranet',
    icon_color='#9D4EDD'
)
```

---

## Testing

Run tests:
```bash
python manage.py test utilities
```

Tests cover:
- Model creation and constraints
- Permission enforcement
- Bill status calculations
- Overdue detection

---

## Files Created

```
utilities/
├── __init__.py
├── apps.py
├── models.py              # Utility, UtilityAccount, UtilityBill
├── serializers.py         # DRF serializers
├── views.py               # ViewSets (CRUD + custom actions)
├── permissions.py         # CanManageUtilityAccounts
├── admin.py               # Django admin classes
├── urls.py                # API routing
├── tests.py               # Test suite
├── services.py            # Processing pipeline
└── migrations/
    └── 0001_initial.py    # Database schema
    └── 0002_...py         # Consumption tracking schema
```

---

# 🔌 Consumption Tracking (Extension)

## Overview

The consumption tracking system provides **flexible data collection** for utilities:
- **Smart Meters**: Automatic data push via webhooks
- **Manual Input**: Tenants enter meter readings via app
- **Hybrid**: Smart meter with manual override capability

---

## 4 New Models

### 1. **UtilityRate** (Pricing Configuration)
Defines how to calculate bills from consumption.

```python
# Fields
utility           # Which utility (Electricity, Gas, etc)
unit              # Unit of measurement (kWh, liters, etc)
rate              # Cost per unit (₦50 per kWh)
fixed_charge      # Monthly fixed fee
effective_from    # When rate becomes active
effective_to      # When rate expires (null = ongoing)
is_active         # Enable/disable rate
```

**Example**: Electricity at ₦50/kWh + ₦500 fixed monthly charge

### 2. **UtilityMeterProvider** (Configuration)
Configures HOW data is captured for each account.

```python
# Fields
account           # Which utility account
method            # 'smart_meter', 'manual_reading', or 'hybrid'
reading_type      # 'consumption' (direct) or 'meter_difference' (previous vs current)
provider_name     # 'EEDC', 'Lagos Water', etc (for smart meters)
api_key           # API credentials (encrypted)
webhook_token     # Token to validate webhook requests
manual_frequency  # 'daily', 'weekly', 'monthly'
last_reading_date # When meter was last read
```

**Examples**:
- House A: `method='smart_meter'`, `provider_name='EEDC'`, `reading_type='meter_difference'`
- House B: `method='manual_reading'`, `manual_frequency='monthly'`
- House C: `method='hybrid'` (smart + can override)

### 3. **UtilityMeterReading** (Raw Data)
Captures raw meter data from ANY source.

```python
# OPTION 1: Meter Difference (subtract readings)
previous_reading  = 100
current_reading   = 145
# Consumption = 145 - 100 = 45 units

# OPTION 2: Direct Consumption
consumption       = 45
# Already the units consumed

# Both approaches work - reading type in MeterProvider determines which
# Other fields
account           # Which account
reading_date      # When meter was read
source            # 'smart_meter', 'manual', or 'import'
submitted_by      # User/system that submitted
is_processed      # Converted to usage record?
is_confirmed      # Locked in (for manual, tenant must confirm)
```

### 4. **UtilityUsageRecord** (Processed, Billable)
One-to-one with MeterReading. This is WHAT GETS BILLED.

```python
# Derived from MeterReading
meter_reading     # Link back to raw reading
consumption       # Final calculated units
unit              # kWh, liters, etc
period_start      # Billing period start
period_end        # Billing period end

# Cost calculation
unit_rate         # ₦50/kWh
variable_cost     # consumption * rate
fixed_charge      # ₦500/month
amount_due        # variable_cost + fixed_charge

# Status
is_billed         # Has a UtilityBill been created?
```

---

## Data Flow Comparison

### Smart Meter (Auto Push)

```
EEDC System
  ↓ POST /api/utilities/webhooks/meter-reading/
    {
      "account_number": "ELEC-123456",
      "current_reading": 145,
      "previous_reading": 100,
      "reading_timestamp": "2026-03-26T10:30:00Z",
      "webhook_token": "secret_token"
    }

UtilityMeterReading created (source='smart_meter', is_confirmed=true)
  ↓ process_meter_reading() signal
UtilityUsageRecord created (45 units × ₦50 = ₦2,250 + ₦500 fixed = ₦2,750)
  ↓
Tenant sees: "Consumed 45 kWh, Amount Due: ₦2,750"
```

### Manual Meter Reading

```
Tenant App Form
  ↓ POST /api/utilities/accounts/{id}/submit_meter_reading/
    {
      "previous_reading": 100,
      "current_reading": 145,
      "reading_date": "2026-03-26"
    }

UtilityMeterReading created (source='manual', is_confirmed=false)
  ↓ Return preview to tenant
    "Current: 145, Previous: 100"
    "Consumption: 45 kWh"
    "Estimated Bill: ₦2,250 (45 × ₦50) + ₦500 fixed = ₦2,750"

Tenant reviews and confirms
  ↓ POST /api/utilities/accounts/{id}/confirm_meter_reading/?reading_id=X
    (sets is_confirmed=true)

confirm_meter_reading() service
  ↓ process_meter_reading() converts to UtilityUsageRecord
  ↓
Locked in: "Amount Due: ₦2,750"
```

---

## API Endpoints

### Submit Manual Meter Reading
```
POST /api/utilities/accounts/{account_id}/submit_meter_reading/

{
  "previous_reading": 100,
  "current_reading": 145,
  "reading_date": "2026-03-26",
  "notes": "March meter reading"
}

Response (preview only, not final):
{
  "id": 123,
  "calculated_consumption": 45,
  "estimated_bill": {
    "consumption": 45,
    "unit_rate": "50.0000",
    "variable_cost": "2250.00",
    "fixed_charge": "500.00",
    "estimated_total": "2750.00"
  },
  "is_confirmed": false
}
```

### Confirm Manual Reading
```
POST /api/utilities/accounts/{account_id}/confirm_meter_reading/?reading_id=123

Response:
{
  "message": "Meter reading confirmed",
  "usage_record": {
    "id": 456,
    "consumption": 45,
    "amount_due": "2750.00",
    "is_billed": false,
    "cost_breakdown": {
      "consumption": 45,
      "unit": "kwh",
      "unit_rate": "50.0000",
      "variable_cost": "2250.00",
      "fixed_charge": "500.00",
      "total_amount_due": "2750.00"
    }
  }
}
```

### Get Consumption History
```
GET /api/utilities/accounts/{account_id}/consumption_history/?days=90

Response:
[
  {
    "id": 456,
    "consumption": 45,
    "unit": "kwh",
    "period_start": "2026-02-24",
    "period_end": "2026-03-26",
    "amount_due": "2750.00"
  },
  {
    "id": 455,
    "consumption": 42,
    "unit": "kwh",
    "period_start": "2026-01-25",
    "period_end": "2026-02-24",
    "amount_due": "2600.00"
  }
]
```

### Smart Meter Webhook
```
POST /api/utilities/webhooks/meter-reading/

{
  "account_number": "ELEC-123456",
  "current_reading": 145,
  "previous_reading": 100,
  "reading_timestamp": "2026-03-26T10:30:00Z",
  "webhook_token": "secret_token_for_verification",
  "provider_name": "EEDC"
}

Response:
{
  "status": "success",
  "reading_id": 123,
  "consumption": 45,
  "estimated_bill": {
    "consumption": 45,
    "unit_rate": "50.0000",
    "variable_cost": "2250.00",
    "fixed_charge": "500.00",
    "total_amount_due": "2750.00"
  }
}
```

---

## Admin Setup

### 1. Create Utility Rates
Go to `/admin/utilities/utilityrate/` and create:

```python
# Electricity
Utility: Electricity
Unit: kwh
Rate: 50.00  # ₦50 per kWh
Fixed Charge: 500.00  # ₦500/month
Effective From: 2026-01-01
Is Active: true

# Gas
Utility: Gas
Unit: units
Rate: 120.00  # ₦120 per unit
Fixed Charge: 200.00
Effective From: 2026-01-01
Is Active: true
```

### 2. Configure Meter Provider for Each Account
Go to `/admin/utilities/utilitymetermrovider/` and create:

```python
# Smart Meter Setup
Account: [select account]
Method: 'smart_meter'
Reading Type: 'meter_difference'
Provider Name: 'EEDC'
API Key: [your_eedc_api_key]
Webhook Token: [generate_random_token]
Is Active: true

# Manual Input Setup
Account: [select account]
Method: 'manual_reading'
Reading Type: 'meter_difference'
Manual Frequency: 'monthly'
Is Active: true
```

---

## Frontend Integration Example

### Smart Meter (Automatic)
```javascript
// Nothing needed! System automatically pulls data.
// Frontend just displays readings and consumption history:

const account = await fetch('/api/utilities/accounts/5/').then(r => r.json());
// Shows "Last reading: 145, Consumption: 45 kWh, Due: ₦2,750"
```

### Manual Input (Tenant)
```javascript
// 1. Show form to tenant
// Previous Reading: ___  Current Reading: ___  Date: ___

// 2. Submit reading (get preview)
const preview = await fetch('/api/utilities/accounts/5/submit_meter_reading/', {
  method: 'POST',
  body: JSON.stringify({
    previous_reading: 100,
    current_reading: 145,
    reading_date: '2026-03-26'
  })
}).then(r => r.json());

// Show: "You consumed 45 kWh, this will cost ₦2,750"

// 3. Tenant confirms
const confirmed = await fetch(
  `/api/utilities/accounts/5/confirm_meter_reading/?reading_id=${preview.id}`,
  { method: 'POST' }
).then(r => r.json());

// Locked in: ₦2,750 bill generated
```

---

## Service Layer (Processing Pipeline)

File: `utilities/services.py`

### `process_meter_reading(meter_reading)`
- Converts raw meter reading → consumption record
- Calculates cost using UtilityRate
- Creates UtilityUsageRecord
- Works for **both** smart meter and manual input

### `confirm_meter_reading(meter_reading)`
- Locks in manual reading (tenant confirmed)
- Calls `process_meter_reading()`
- Updates meter provider's `last_reading_date`

### `validate_meter_reading(meter_reading)`
- Checks consumption isn't negative
- Checks date isn't in future
- Checks no duplicate readings for same day
- Checks current >= previous

---

## Testing Consumption Tracking

### Test Smart Meter Webhook
```bash
curl -X POST http://localhost:8000/api/utilities/webhooks/meter-reading/ \
  -H "Content-Type: application/json" \
  -d '{
    "account_number": "ELEC-123456",
    "current_reading": 145,
    "previous_reading": 100,
    "reading_timestamp": "2026-03-26T10:30:00Z",
    "webhook_token": "your_webhook_token"
  }'
```

### Test Manual Reading in Django Shell
```python
from utilities.models import UtilityMeterReading
from utilities.services import confirm_meter_reading

# Simulate tenant submission
reading = UtilityMeterReading.objects.create(
    account_id=5,
    previous_reading=100,
    current_reading=145,
    reading_date='2026-03-26',
    source='manual',
    submitted_by='John Doe'
)

# Tenant confirms
usage_record = confirm_meter_reading(reading)
print(f"Amount due: ₦{usage_record.amount_due}")
```

---

## Key Design Decisions

✅ **Flexible Data Ingestion**: Smart meter AND manual input in same system  
✅ **Separation of Concerns**: Raw reading → processed usage → bill  
✅ **Extensible Rates**: Multiple rates per utility with effective dates  
✅ **Audit Trail**: Track who submitted readings and when  
✅ **No Auto-Billing**: Usage records created but bills must be generated separately  
✅ **Validation**: Check for negative consumption, duplicates, future dates  
✅ **Cost Breakdown**: Show tenants exactly what they're paying for  

---

## Next Steps

1. **Set up initial utilities and rates** in Django admin
2. **Configure meter providers** for first few accounts (test smart + manual)
3. **Test webhook** with smart meter provider (EEDC, etc)
4. **Build tenant frontend** for manual reading submission
5. **Integrate with billing system** to auto-generate UtilityBill from UsageRecord
6. **Add notifications** when readings are due or overdue
7. **Build consumption charts** for tenant dashboard

---

## Notes

- Consumption tracking is **decoupled from billing** — readings → usage records → bills (separate step)
- **No auto-bill generation** yet; that's a separate system to build
- **Rates are versioned** with effective dates for historical tracking
- **Webhook validation** uses token to prevent unauthorized submissions
- **Manual readings locked in** after confirmation to prevent accidental changes


