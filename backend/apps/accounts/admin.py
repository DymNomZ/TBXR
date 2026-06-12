from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

''' ADDED THIS SO WE CAN CHANGE ROLES EASILY ON THE ADMIN PAGE '''
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Role Information', {'fields': ('role',)}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff')

admin.site.register(User, CustomUserAdmin)