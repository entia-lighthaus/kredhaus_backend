from django.urls import path
from .views import (
    DevFundWalletView,
    WalletView,
    WalletSummaryView,
    TransactionListView,
    SavingsPocketListCreateView,
    FundPocketView,
    WithdrawPocketView,
    RequestPocketUnlockView,  
    ConfirmPocketUnlockView,
    FlutterwaveWebhookView,
)

app_name = 'wallet'

urlpatterns = [

    # ── Wallet ─────────────────────────────────────────────────────────
    path(
        '',
        WalletView.as_view(),
        name='wallet',
    ),
    path(
        'summary/',
        WalletSummaryView.as_view(),
        name='wallet-summary',
    ),

    # ── Transactions ───────────────────────────────────────────────────
    # This endpoint returns a paginated list of transactions for the authenticated user's wallet, ordered by most recent first. 
    # It includes details such as amount, type (credit/debit), date, and description for each transaction.
    path(
        'transactions/',
        TransactionListView.as_view(),
        name='transactions',
    ),

    # ── Savings Pockets ────────────────────────────────────────────────
    # The following endpoints allow users to create and manage savings pockets within their wallet.
    
    path(
        'pockets/',
        SavingsPocketListCreateView.as_view(),
        name='pocket-list-create',
    ),
    path(
        'pockets/fund/',
        FundPocketView.as_view(),
        name='pocket-fund',
    ),
    path(
        'pockets/withdraw/',
        WithdrawPocketView.as_view(),
        name='pocket-withdraw',
    ),

    path( # Request pocket unlock starts a 3-day countdown during which the pocket remains locked. After the waiting period, the user can confirm the unlock.
    'pockets/unlock/request/',
    RequestPocketUnlockView.as_view(),
    name='pocket-unlock-request',
    ),
    path( # Confirm pocket unlock can only be done after the 3-day waiting period has passed since the unlock request. This two-step process encourages saving discipline by preventing impulsive withdrawals from locked pockets.
        'pockets/unlock/confirm/',
        ConfirmPocketUnlockView.as_view(),
        name='pocket-unlock-confirm',
    ),


    # ── Webhooks ───────────────────────────────────────────────────────
    path(
        'webhook/',
        FlutterwaveWebhookView.as_view(),
        name='webhook',
    ),

    # ── Dev Tools (Remove in Production) ───────────────────────────────────────────────
    path('dev/fund/', DevFundWalletView.as_view(), name='dev-fund'),
]