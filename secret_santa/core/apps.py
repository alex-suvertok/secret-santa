from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self) -> None:
        from .models import User
        from fieldsignals import post_save_changed
        from .signals import change_member

        # Connect the change_member signal to the User model's post_save_changed signal
        post_save_changed.connect(change_member, sender=User, fields=['email'])
