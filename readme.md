Kredhaus is a PropFinTech platform built with Django REST Framework. Kredhaus helps young Nigerians build credit history through rent payments, manage energy savings, track utility costs, and access property financing products.

----------------------------------------------------------------------------------

## Tech Stack

- **Backend:** Django 5.x + Django REST Framework
- **Authentication:** JWT via SimpleJWT
- **Database:** SQLite (development) → PostgreSQL (production)
- **Identity Verification:** Prembly / Smile Identity (mock in development)
- **SMS OTP:** Termii (console in development)
- **Language:** Python 3.12

---

## Project Structure

```
kredhaus_backend/          ← root folder
│
├── manage.py              ← Django CLI entry point
├── requirements.txt       ← Python dependencies
├── .env                   ← environment variables (never commit this)
├── .gitignore
│
├── kredhaus_backend/      ← project configuration
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
└── accounts/              ← Module 01: Identity & Onboarding
    ├── migrations/
    ├── models.py          ← User model, KYC logic
    ├── serializers.py     ← request/response shapes
    ├── views.py           ← API logic
    ├── urls.py            ← accounts routes
    ├── admin.py           ← Django admin config
    └── permissions.py     ← KYC tier permission classes
```

---

## LOCAL SETUP

### 1. Clone the repository

### 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

### 3. Install dependencies
pip install -r requirements.txt

### 4. Create environment file
cp .env.example .env

Open `.env` and set your values:

```
SECRET_KEY=your-secret-key-here
DEBUG=True
```

### 5. Run migrations
python manage.py makemigrations accounts
python manage.py migrate


### 6. Create superuser
python manage.py createsuperuser


### 7. Start development server
python manage.py runserver

Server runs at `http://127.0.0.1:8000`

Admin panel at `http://127.0.0.1:8000/admin`

------------------------------------------------------------------------------------------


## AUTHENTICATION

Kredhaus uses JWT (JSON Web Tokens) for authentication.

After login, you receive two tokens:

| Token | Lifetime | Purpose |
|---|---|---|
| `access` | 60 minutes | Sent with every protected request |
| `refresh` | 7 days | Used to get a new access token |

Include the access token in the Authorization header on every protected request:

```
Authorization: Bearer <access_token>
```

----------------------------------------------------------------------------------

## KYC TIER SYSTEM

Access to platform features is gated by KYC tier. Users register freely but must verify their identity to unlock features.

| Tier | Name       | Requirements         | Unlocks |
| 0    | Unverified | Phone + password     | Browse listings, view public profiles |
| 1    | Basic      | Phone verified + NIN | Maintenance requests, credit score, basic payments |
| 2    | Financial  | BVN + address        | Rent payments, savings pockets, credit building |
| 3    | Financing  | Income proof + NOK + employment | Rent-to-own, BNPL, premium financing |

-------------------------------------------------------------------------------------

## API ENDPOINTS

Base URL: `http://127.0.0.1:8000/api/v1`

All request bodies are JSON. All responses are JSON.


POST  /api/v1/accounts/register/       public    — create account
POST  /api/v1/accounts/login/          public    — returns JWT tokens
POST  /api/v1/accounts/token/refresh/  public    — refresh access token
POST  /api/v1/accounts/logout/         protected — blacklist token
GET   /api/v1/accounts/profile/        protected — current user data
POST  /api/v1/accounts/verify/nin/     protected — verify NIN
POST  /api/v1/accounts/verify/bvn/     protected — verify BVN
GET   /api/v1/accounts/kyc/status/     protected — current KYC state
POST  /api/v1/accounts/kyc/tier1/      protected — upgrade to Tier 1
POST  /api/v1/accounts/kyc/tier2/      protected — upgrade to Tier 2
POST  /api/v1/accounts/kyc/tier3/      protected — upgrade to Tier 3

----------------------------------------------------------------------------------

## REGISTRATION AND LOGIN

#### Register a new account
```
POST /accounts/register/
```
**Auth required:** No

**Request body:**
```json
{
    "phone": "08012345678",
    "first_name": "Amaka",
    "last_name": "Obi",
    "email": "amaka@example.com",
    "role": "tenant",
    "password": "testpass123",
    "confirm_password": "testpass123"
}
```

**Role options:** `tenant` `homeowner` `vendor` `admin`

**Response `201`:**
```json
{
    "message": "Account created successfully.",
    "user": {
        "phone": "+2348012345678",
        "first_name": "Amaka",
        "last_name": "Obi",
        "role": "tenant"
    }
}
```

----------------------------------------------------------------------------------

#### Login
```
POST /accounts/login/
```
**Auth required:** No

**Request body:**
```json
{
    "phone": "08012345678",
    "password": "testpass123"
}
```

**Response `200`:**
```json
{
    "message": "Login successful.",
    "tokens": {
        "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    },
    "user": {
        "phone": "+2348012345678",
        "first_name": "Amaka",
        "last_name": "Obi",
        "role": "tenant"
    }
}
```

---

#### Refresh access token
```
POST /accounts/token/refresh/
```
**Auth required:** No

**Request body:**
```json
{
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response `200`:**
```json
{
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

----------------------------------------------------------------------------------

#### Logout
```
POST /accounts/logout/
```
**Auth required:** Yes

Blacklists the refresh token so it can no longer be used.

**Request body:**
```json
{
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response `200`:**
```json
{
    "message": "Logged out successfully."
}
```

----------------------------------------------------------------------------------



## USER PROFILE

#### Get current user profile
```
GET /accounts/profile/
```
**Auth required:** Yes

**Response `200`:**
```json
{
    "phone": "+2348012345678",
    "first_name": "Amaka",
    "last_name": "Obi",
    "email": "amaka@example.com",
    "role": "tenant",
    "kyc_tier": 1,
    "kyc_tier_label": "Basic",
    "kyc_unlocks": [
        "Browse property listings",
        "View public profiles",
        "Submit maintenance requests",
        "View credit score",
        "Basic payments"
    ],
    "nin_verified": true,
    "bvn_verified": false,
    "phone_verified": true,
    "onboarding_steps": {
        "phone_verified": true,
        "nin_verified": true,
        "bvn_verified": false,
        "kyc_tier": 1,
        "profile_complete": true
    },
    "date_joined": "2026-03-19T11:17:00Z"
}
```

----------------------------------------------------------------------------------



## IDENTITY VERIFICATION

#### Verify NIN
```
POST /accounts/verify/nin/
```
**Auth required:** Yes

Submits the user's National Identification Number for verification.
In production this calls the Prembly or Smile Identity API against the NIMC database.

**Request body:**
```json
{
    "nin": "12345678901"
}
```

**Response `200`:**
```json
{
    "message": "NIN verified successfully.",
    "nin_verified": true
}
```

----------------------------------------------------------------------------------

#### Verify BVN
```
POST /accounts/verify/bvn/
```
**Auth required:** Yes

Links the user's Bank Verification Number.
In production this calls the Mono or Okra API against the CBN BVN database.

**Request body:**
```json
{
    "bvn": "12345678901"
}
```

**Response `200`:**
```json
{
    "message": "BVN linked successfully.",
    "bvn_verified": true
}
```

----------------------------------------------------------------------------------



### KYC Tier Upgrades

# Check KYC status
```
GET /accounts/kyc/status/
```
**Auth required:** Yes

Returns the user's current KYC tier and what they have completed.

**Response `200`:**
```json
{
    "kyc_tier": 1,
    "kyc_tier_label": "Basic",
    "tier_qualified_for": 1,
    "phone_verified": true,
    "nin_verified": true,
    "bvn_verified": false,
    "address_line1": null,
    "lga": null,
    "state": null,
    "nok_name": null,
    "monthly_income": null
}
```

----------------------------------------------------------------------------------



#### Upgrade to Tier 1 — Basic
```
POST /accounts/kyc/tier1/
```
**Auth required:** Yes

**Requirements:** Phone must be verified before calling this endpoint.

**Unlocks:** Browse listings, view credit score, basic payments.

**Request body:**
```json
{
    "nin": "12345678901"
}
```

**Response `200`:**
```json
{
    "message": "Tier 1 verification complete.",
    "kyc_tier": 1,
    "unlocks": [
        "Browse listings",
        "View credit score",
        "Basic payments"
    ]
}
```

---

#### Upgrade to Tier 2 — Financial
```
POST /accounts/kyc/tier2/
```
**Auth required:** Yes

**Requirements:** Must be KYC Tier 1 before calling this endpoint.

**Unlocks:** Rent payments, savings pockets, credit building.

**Request body:**
```json
{
    "bvn": "12345678901",
    "address_line1": "14B Adeola Odeku Street",
    "address_line2": "",
    "lga": "Eti-Osa",
    "state": "Lagos"
}
```

**Response `200`:**
```json
{
    "message": "Tier 2 verification complete.",
    "kyc_tier": 2,
    "unlocks": [
        "Rent payments",
        "Savings pockets",
        "Credit building"
    ]
}
```

---

#### Upgrade to Tier 3 — Financing
```
POST /accounts/kyc/tier3/
```
**Auth required:** Yes

**Requirements:** Must be KYC Tier 2 before calling this endpoint.

**Unlocks:** Rent-to-own, BNPL options, premium financing.

**Request body:**
```json
{
    "employer_name": "Zenith Bank",
    "monthly_income": 350000,
    "nok_name": "Chukwuemeka Obi",
    "nok_phone": "08098765432",
    "nok_relationship": "Father"
}
```

**Response `200`:**
```json
{
    "message": "Tier 3 verification complete.",
    "kyc_tier": 3,
    "unlocks": [
        "Rent-to-own",
        "BNPL options",
        "Premium financing"
    ]
}
```

---

## Error Responses

All endpoints return consistent error shapes.

**400 Bad Request — validation error:**
```json
{
    "phone": ["A user with this phone number already exists."],
    "confirm_password": ["Passwords do not match."]
}
```

**401 Unauthorized — missing or invalid token:**
```json
{
    "detail": "Authentication credentials were not provided."
}
```

**403 Forbidden — KYC tier too low:**
```json
{
    "detail": "You need to complete KYC Tier 2 to access this feature. Please link your BVN and verify your address."
}
```

---

## Complete Endpoint Reference

POST   /api/v1/accounts/register/           public   — create account
POST   /api/v1/accounts/login/              public   — password login
POST   /api/v1/accounts/login/pin/          public   — PIN login
POST   /api/v1/accounts/logout/             auth     — blacklist token
POST   /api/v1/accounts/token/refresh/      public   — refresh token
GET    /api/v1/accounts/profile/            auth     — basic profile. Get current user
GET    /api/v1/accounts/profile/builder/    auth     — full profile + score
PATCH  /api/v1/accounts/profile/builder/    auth     — update profile
POST   /api/v1/accounts/profile/photo/      auth     — upload photo
POST   /api/v1/accounts/pin/set/            auth     — set PIN + get device token
POST   /api/v1/accounts/verify/nin/         auth     — verify NIN
POST   /api/v1/accounts/verify/bvn/         auth     — verify BVN
GET    /api/v1/accounts/kyc/status/         auth     — KYC status
POST   /api/v1/accounts/kyc/tier1/          auth     — upgrade to Tier 1
POST   /api/v1/accounts/kyc/tier2/          auth     — upgrade to Tier 2
POST   /api/v1/accounts/kyc/tier3/          auth     — upgrade to Tier 3
GET    /api/v1/accounts/referral/           auth     — referral dashboard + tree
GET    /api/v1/accounts/referral/credits/   auth     — credit history
----------------------------------------------------------------------------------

## Modules Roadmap

```
~ Module 01 — Identity & Onboarding     (complete)
⬜ Module 02 — Tenancy Management
⬜ Module 03 — Credit Builder
⬜ Module 04 — Energy & Utilities
⬜ Module 05 — Waste & Sustainability
⬜ Module 06 — Property Financing
⬜ Module 07 — Property Discovery
⬜ Module 08 — Vendor & Services
⬜ Module 09 — Wallet & Payments
⬜ Module 10 — Dashboards & Analytics
⬜ Module 11 — Admin & Compliance
⬜ Module 12 — Community & Engagement
```

----------------------------------------------------------------------------------

## Contributing

1. Create a branch for your feature: e.g. `git checkout -b feature/module-02-tenancy`
2. Make your changes
3. Commit with a clear message: `git commit -m "add lease model and rent payment endpoint"`
4. Push and open a pull request: `git push origin feature/module-02-tenancy`

----------------------------------------------------------------------------------

## Licence

Private — Kredhaus. All rights reserved.
