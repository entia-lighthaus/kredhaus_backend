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
└── migrations/
    └── 0001_initial.py    # Database schema
```

---

## TODO / Next Steps

1. **Integrate with frontend**: Use the API endpoints to build the UI
2. **Add automation**: Create periodic tasks to update bill statuses
3. **Payment integration**: Connect to payment providers for bill payment
4. **Notifications**: Alert tenants when bills are due/overdue
5. **Reports**: Build dashboards for owners to track utility payments

---

## Notes

- All monetary fields use `DecimalField` for precision
- Bill due date tracking supports SLA calculations
- `connected_by` and `last_updated_by` are user-facing strings (not ForeignKey)
- Permissions are automatically enforced by DRF
- Serializers include all related data (nested utility info, bills)

