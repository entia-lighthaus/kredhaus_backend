Endpoints

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

