from rest_framework import serializers
from .models import User
from django.contrib.auth import authenticate


class RegisterSerializer(serializers.ModelSerializer):

    password         = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model  = User
        fields = [
            'phone',
            'first_name',
            'last_name',
            'email',
            'role',
            'password',
            'confirm_password',
        ]

    def validate_phone(self, value):
        # Normalise: if starts with 0, replace with +234
        value = value.strip()
        if value.startswith('0'):
            value = '+234' + value[1:]
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('confirm_password'):
            raise serializers.ValidationError(
                {'confirm_password': 'Passwords do not match.'}
            )
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user     = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
    


class LoginSerializer(serializers.Serializer):

    phone    = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        phone    = attrs.get('phone')
        password = attrs.get('password')

        # Normalise phone
        if phone.startswith('0'):
            phone = '+234' + phone[1:]

        # authenticate() checks the password against the hashed version in the DB
        user = authenticate(username=phone, password=password)

        if not user:
            raise serializers.ValidationError('Invalid phone number or password.')

        if not user.is_active:
            raise serializers.ValidationError('This account has been deactivated.')

        attrs['user'] = user
        return attrs
    
#creating a protected endpoint
# This endpoint returns the currently logged-in user's profile. It's protected, meaning if you call it without a valid token, it rejects you.
class UserProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model  = User
        fields = [
            'phone',
            'first_name',
            'last_name',
            'email',
            'role',
            'date_joined',
        ]