from django.contrib import admin
from django.contrib import messages

from .assignment import AssignmentError
from .models import Celebration, Member, SecretSanta, Team


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['name', 'team', 'colleagues_names']
    fields = ['name', 'email_address', 'team', 'colleagues']

    @admin.display(description='Colleagues')
    def colleagues_names(self, obj):
        return ', '.join(str(colleague) for colleague in obj.colleagues.all())


@admin.action(description='Повторно надіслати листа про одержувача подарунка')
def resend_email(modeladmin, request, queryset):
    for secret_santa in queryset:
        secret_santa.resend_email()


@admin.register(SecretSanta)
class SecretSantaAdmin(admin.ModelAdmin):
    list_display = ['santa', 'hashed_recipient_info', 'celebration']
    fields = ['santa', 'recipient', 'celebration']
    actions = [resend_email]

    @admin.display(description='Hashed recipient info')
    def hashed_recipient_info(self, obj):
        return obj.recipient.hashed_email

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False


@admin.action(description='Хай розпочнеться святкування!')
def create_secret_santa(modeladmin, request, queryset):
    for celebration in queryset:
        try:
            celebration.run()
        except AssignmentError as exc:
            modeladmin.message_user(request, f'{celebration}: {exc}', level=messages.ERROR)


@admin.register(Celebration)
class CelebrationAdmin(admin.ModelAdmin):
    list_display = ['year', 'team']
    fields = ['year', 'team']
    actions = [create_secret_santa]