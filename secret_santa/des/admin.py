import logging

from django import forms
from django.contrib import admin, messages
from django.core.mail import send_mail
from solo.admin import SingletonModelAdmin

from .models import DynamicEmailConfiguration

logger = logging.getLogger(__name__)


class DynamicEmailConfigurationForm(forms.ModelForm):
    email_host_password = forms.CharField(
        label='Password',
        required=False,
        widget=forms.PasswordInput,
        help_text='Введіть новий пароль, щоб змінити. Якщо залишити порожнім — '
                  'збережеться наявний пароль.',
    )

    class Meta:
        model = DynamicEmailConfiguration
        fields = '__all__'

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not self.cleaned_data.get('email_host_password'):
            instance.email_host_password = DynamicEmailConfiguration.get_solo().email_host_password
        if commit:
            instance.save()
        return instance


@admin.register(DynamicEmailConfiguration)
class DynamicEmailConfigurationAdmin(SingletonModelAdmin):
    form = DynamicEmailConfigurationForm
    fieldsets = (
        ('SMTP-сервер', {
            'fields': ('email_host', 'email_port'),
        }),
        ('Автентифікація', {
            'fields': ('email_host_user', 'email_host_password'),
        }),
        ('Безпека', {
            'fields': ('email_use_tls', 'email_use_ssl', 'fail_silently'),
        }),
        ('Відправник за замовчуванням', {
            'fields': ('from_email',),
        }),
    )
    list_display = ['email_host', 'email_port', 'email_host_user', 'email_use_tls']

    def send_test_email(modeladmin, request, queryset):
        try:
            config = DynamicEmailConfiguration.get_solo()
        except Exception:
            messages.error(request, 'Не вдалося завантажити конфігурацію електронної пошти.')
            return

        if not config.email_host:
            messages.error(request, 'SMTP-сервер (email host) не налаштований.')
            return

        try:
            send_mail(
                subject='Тестовий лист від Secret Santa',
                message='Це тестовий лист від вашого застосунку Secret Santa.',
                from_email=config.from_email or config.email_host_user or None,
                recipient_list=[config.email_host_user],
                fail_silently=False,
            )
            messages.success(request, f'Тестовий лист надіслано на {config.email_host_user}')
        except Exception as e:
            messages.error(request, f'Не вдалося надіслати тестовий лист: {e}')
            logger.exception('Test email send failed')

    send_test_email.short_description = 'Надіслати тестовий лист'

    actions = [send_test_email]
