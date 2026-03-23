from django.conf import settings


# Points awarded per event per level
REFERRAL_POINTS = {
    'signup': {
        1: 500,   # direct referral signs up
        2: 200,   # their referral signs up
        3: 100,
        4: 50,
        5: 25,
    },
    'kyc': {
        1: 1000,
        2: 400,
        3: 200,
        4: 100,
        5: 50,
    },
    'payment': {
        1: 2000,
        2: 800,
        3: 400,
        4: 200,
        5: 100,
    },
}

MAX_LEVELS = 5


class ReferralService:

    @staticmethod
    def award_credits(source_user, credit_type: str):
        """
        Called when a user completes a credit-triggering
        action (signup, kyc, first payment).

        Walks up the referral_path and awards points
        to every ancestor up to MAX_LEVELS deep.
        """
        from .models import ReferralCredit

        if not source_user.referral_path:
            return   # no referrers — nothing to award

        ancestor_ids = source_user.referral_path.split('|')

        from .models import User
        for level, ancestor_id in enumerate(ancestor_ids, start=1):
            if level > MAX_LEVELS:
                break
            try:
                beneficiary = User.objects.get(id=ancestor_id)
            except User.DoesNotExist:
                continue

            points = REFERRAL_POINTS.get(credit_type, {}).get(level, 0)
            if points == 0:
                continue

            ReferralCredit.objects.create(
                beneficiary=beneficiary,
                source_user=source_user,
                credit_type=credit_type,
                level=level,
                points=points,
                description=(
                    f'Level {level} {credit_type} credit from '
                    f'{source_user.first_name} {source_user.last_name}'
                ),
            )

    @staticmethod
    def get_referral_tree(user, depth=0, max_depth=5):
        """
        Returns the full downline tree for a user
        as a nested dictionary.
        Used for the referral dashboard.
        """
        if depth >= max_depth:
            return []

        children = user.direct_referrals.all()
        tree = []

        for child in children:
            tree.append({
                'id':         child.id,
                'name':       f'{child.first_name} {child.last_name}',
                'phone':      child.phone,
                'joined':     child.date_joined,
                'kyc_tier':   child.kyc_tier,
                'level':      depth + 1,
                'downline':   ReferralService.get_referral_tree(
                                  child, depth + 1, max_depth
                              ),
            })
        return tree