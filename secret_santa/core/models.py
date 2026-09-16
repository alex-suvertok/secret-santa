import hashlib
import logging

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.db import models
from django.utils import timezone
from model_utils import FieldTracker

from .assignment import AssignmentError, build_assignment

logger = logging.getLogger(__name__)


class User(AbstractUser):
    dob = models.DateField(verbose_name='Date of birth', null=True, blank=True)

    @property
    def name(self) -> str:
        first_name = self.first_name
        last_name = self.last_name

        if first_name and last_name:
            return f'{first_name} {last_name}'
        if first_name:
            return first_name
        if last_name:
            return last_name
        return self.email

    def __str__(self) -> str:
        return self.name


class Team(models.Model):
    name = models.CharField(verbose_name='Name', max_length=255)

    def __str__(self) -> str:
        return self.name


class Member(models.Model):
    team = models.ForeignKey(Team, related_name='members', on_delete=models.CASCADE)

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField('Name', max_length=255, null=True, blank=True)
    email_address = models.EmailField('Email address')
    email_address_tracker = FieldTracker(fields=['email_address'])
    hashed_email = models.CharField('Hashed recipient\'s email', max_length=64, null=True, blank=True)

    colleagues = models.ManyToManyField('self', blank=True)

    def save(self, *args, **kwargs) -> None:
        # Recompute the hash whenever a Member is first created or its email source changed
        if self.pk is None or self.email_address_tracker.changed() or (self.user and self.user.email):
            self.hashed_email = self.get_hashed_email()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        super().clean()
        if not (self.name or self.user):
            raise ValidationError("Учасник повинен мати ім'я або зв'язок з користувачем")

    def __str__(self) -> str:
        return self.name or (self.user.name if self.user else '')

    def get_hashed_email(self) -> str:
        return hashlib.sha256((self.email + settings.HASH_SALT).encode('utf-8')).hexdigest()

    @property
    def email(self) -> str:
        user = self.user
        return user.email if user else self.email_address

    @property
    def full_name(self) -> str:
        user = self.user
        return user.name if user else self.name


def mailing(santa, recipient_name) -> None:
    from_email = settings.DEFAULT_FROM_EMAIL
    try:
        from des.models import DynamicEmailConfiguration
        from_email = DynamicEmailConfiguration.get_solo().from_email or from_email
    except Exception:
        logger.warning('Could not load DynamicEmailConfiguration, using DEFAULT_FROM_EMAIL', exc_info=True)

    team_name = santa.team.name if santa.team else ''
    subject = 'Привіт! Це Secret Santa від Alex Suvertok'
    html_body = (
        f'<p>Привіт, {santa.full_name}!</p>'
        f'<p>Команда &quot;{team_name}&quot; грає в Secret Santa.</p>'
        f'<h3>Вас обрано таємним Сантою для {recipient_name}</h3>'
        f'<p>Приготуйте, будь ласка, подарунок для {recipient_name}. Успіхів!</p>'
    )

    message = EmailMessage(
        subject=subject,
        body=html_body,
        from_email=from_email,
        to=[santa.email],
    )
    message.content_subtype = 'html'
    try:
        message.send(fail_silently=settings.EMAIL_FAIL_SILENTLY)
    except Exception:
        logger.exception('Failed to send email to %s', santa.email)


class Celebration(models.Model):
    team = models.ForeignKey(Team, verbose_name='The team celebrating the new year', on_delete=models.CASCADE)
    year = models.PositiveSmallIntegerField(verbose_name='Next year')

    def __str__(self) -> str:
        return f'{self.team} у {self.year}'

    class Meta:
        unique_together = ['team', 'year']
        ordering = ['year']

    def clean(self) -> None:
        super().clean()
        specified_year = self.year
        current_year = timezone.now().year
        if specified_year <= current_year:
            raise ValidationError(
                f'Введіть наступний рік. Вказаний рік ({specified_year}) менший або '
                f'дорівнює поточному ({current_year})'
            )

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def run(self) -> None:
        """Build the exchange, then persist and email — only after success.

        Raises AssignmentError (with a user-friendly message) when no valid
        exchange exists; existing SecretSanta rows are left untouched then.
        """
        members = list(self.team.members.prefetch_related('colleagues'))
        assignments = build_assignment(members)

        self.clear()
        SecretSanta.objects.bulk_create([
            SecretSanta(santa=santa, recipient=recipient, celebration=self)
            for santa, recipient in assignments.items()
        ])

        for santa, recipient in assignments.items():
            mailing(santa, recipient.full_name)

    def clear(self) -> None:
        self.secret_santas.all().delete()


class SecretSanta(models.Model):
    santa = models.ForeignKey(Member, verbose_name='Santa', related_name='me_santa', on_delete=models.CASCADE)
    recipient = models.ForeignKey(
        Member, verbose_name='Recipient of a gift from Santa', related_name='my_santa', on_delete=models.CASCADE
    )
    celebration = models.ForeignKey(Celebration, related_name='secret_santas', on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f'{self.santa} {self.recipient} {self.celebration}'

    class Meta:
        unique_together = [
            ('celebration', 'santa'),
            ('celebration', 'recipient'),
        ]

    def resend_email(self) -> None:
        mailing(self.santa, self.recipient.full_name)