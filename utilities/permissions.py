from rest_framework import permissions


class IsUnitOccupant(permissions.BasePermission):
    """
    Allow only the tenant occupying the unit or property owner to access utility accounts.
    """

    def has_object_permission(self, request, view, obj):
        # Allow property owner
        if request.user == obj.unit.property.owner:
            return True
        
        # Allow tenant of the unit
        # Check if user has an active lease for this unit
        has_active_lease = obj.unit.leases.filter(
            tenant=request.user,
            status__in=['active', 'pending']
        ).exists()
        
        return has_active_lease


class CanManageUtilityAccounts(permissions.BasePermission):
    """
    Allow tenants to manage utility accounts for their units only.
    Owners can manage accounts for all their units.
    """

    def has_permission(self, request, view):
        # Only authenticated users
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Allow property owner
        if request.user == obj.unit.property.owner:
            return True
        
        # Allow tenant of the unit
        has_active_lease = obj.unit.leases.filter(
            tenant=request.user,
            status__in=['active', 'pending']
        ).exists()
        
        return has_active_lease
