from django.db import models
from solo.models import SingletonModel


class DynamicEmailConfiguration(SingletonModel):
    email_host = models.CharField('SMTP host', max_length=255, default='localhost')
    email_port = models.PositiveIntegerField('SMTP port', default=25)
    email_host_user = models.CharField('Username', max_length=255, blank=True, default='')
    email_host_password = models.CharField('Password', max_length=255, blank=True, default='')
    email_use_tls = models.BooleanField('Use TLS', default=True)
    email_use_ssl = models.BooleanField('Use SSL', default=False)
    fail_silently = models.BooleanField('Fail silently', default=False)
    from_email = models.EmailField('From email', blank=True, default='')

    class Meta:
        verbose_name = 'Dynamic Email Configuration'

    def __str__(self) -> str:
        return f'{self.email_host}:{self.email_port}'
