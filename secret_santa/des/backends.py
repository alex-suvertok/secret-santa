from django.core.mail.backends.smtp import EmailBackend
from django.core.mail.backends.console import EmailBackend as ConsoleBackend

from .models import DynamicEmailConfiguration


class ConfiguredEmailBackend(EmailBackend):
    def __init__(self, **kwargs):
        try:
            config = DynamicEmailConfiguration.get_solo()
        except Exception:
            config = None

        if config is None or not config.email_host:
            fallback = ConsoleBackend(fail_silently=kwargs.get('fail_silently', False))
            self._use_fallback = True
            super().__init__(**kwargs)
            self._fallback = fallback
            return

        self._use_fallback = False
        super().__init__(
            host=config.email_host,
            port=config.email_port,
            username=config.email_host_user or '',
            password=config.email_host_password or '',
            use_tls=config.email_use_tls,
            use_ssl=config.email_use_ssl,
            fail_silently=kwargs.get('fail_silently', config.fail_silently),
            **{k: v for k, v in kwargs.items() if k != 'fail_silently'},
        )

    def open(self):
        if self._use_fallback:
            return self._fallback.open()
        return super().open()

    def send_messages(self, email_messages):
        if self._use_fallback:
            return self._fallback.send_messages(email_messages)
        return super().send_messages(email_messages)

    def close(self):
        if self._use_fallback:
            self._fallback.close()
            return
        super().close()
