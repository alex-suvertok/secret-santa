import hashlib
from random import choice

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from model_utils import FieldTracker
from templated_email import send_templated_mail


class User(AbstractUser):
    dob = models.DateField(verbose_name='Date of birth', null=True, blank=True)

    @property
    def name(self):
        # Construct user's name from first_name and last_name, fallback to email
        first_name = self.first_name
        last_name = self.last_name

        if first_name and last_name:
            return f'{first_name} {last_name}'
        elif first_name:
            return first_name
        elif last_name:
            return last_name
        return self.email

    def __str__(self) -> str:
        return self.name


class Team(models.Model):
    # Team name
    name = models.CharField(verbose_name='Name', max_length=255)

    def __str__(self) -> str:
        return self.name


class Member(models.Model):
    # Relation to team — many members per one team
    team = models.ForeignKey(Team, related_name='members', on_delete=models.CASCADE)

    # Optional relation to User (if present)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    # Name can be empty (null=True, blank=True)
    name = models.CharField('Name', max_length=255, null=True, blank=True)
    # Email address (required)
    email_address = models.EmailField('Email address')
    # Tracks changes in email_address for automatic hashed_email update
    email_address_tracker = FieldTracker(fields=['email_address'])
    # Hashed email for privacy, stored in DB
    hashed_email = models.CharField('Hashed recipient\'s email', max_length=32, null=True, blank=True)

    # Many-to-many self-referential relation for colleagues within members
    colleagues = models.ManyToManyField('self', blank=True)

    def save(self, *args, **kwargs) -> None:
        # If new record or email_address changed and no linked user — update hashed_email
        if self.pk is None or (self.email_address_tracker.changed() and self.user is None):
            # Generate hashed email
            self.hashed_email = self.get_hashed_email()

        # Validation: must have either name or user linked, otherwise raise ValidationError
        if self.name or self.user:
            super().save(*args, **kwargs)
        else:
            raise ValidationError('The member must have a name or connection to the user')

    def __str__(self) -> str:
        # Return name or linked user's name if available
        return self.name or (self.user.name if self.user else '')

    def get_hashed_email(self):
        # Take email (user.email or email_address) and create MD5 hash with salt
        email = self.email or ''
        return hashlib.md5((email + settings.HASH_SALT).encode('utf-8')).hexdigest()

    @property
    def email(self) -> str:
        # Return user's email if linked, else email_address
        user = self.user
        return user.email if user else self.email_address

    @property
    def full_name(self) -> str:
        # Same for full name
        user = self.user
        return user.name if user else self.name


def mailing(santa, recipient_name) -> None:
    try:
        # Send templated email with your_ward.email template
        send_templated_mail(
            template_name='your_ward.email',
            recipient_list=[santa.email],
            from_email=settings.TEMPLATED_EMAIL_FROM_EMAIL,
            context=dict(recipient_name=recipient_name)
        )
    except Exception:
        # Silently ignore exceptions — logging is recommended
        pass


class Celebration(models.Model):
    # Team celebrating New Year
    team = models.ForeignKey(Team, verbose_name='The team celebrating the new year', on_delete=models.CASCADE)
    # Celebration year (must be greater than current year)
    year = models.PositiveSmallIntegerField(verbose_name='Next year')

    def __str__(self) -> str:
        return f'{self.team} in {self.year}'

    class Meta:
        # Unique pair team+year
        unique_together = ['team', 'year']
        ordering = ['year']

    def save(self, **kwargs) -> None:
        specified_year = self.year
        current_year = timezone.now().year

        if specified_year <= current_year:
            raise ValidationError(
                f'Enter the next year. The specified year ({specified_year}) is less than the current year ({current_year})'
            )
        return super().save(**kwargs)

    def get_colleagues_count_dict(self, colleagues_dict):
        # Return dict {member: number of colleagues}, sorted by number of colleagues
        colleagues_count_dict = dict()
        for key, value in colleagues_dict.items():
            colleagues_count_dict[key] = len(value)

        return dict(sorted(colleagues_count_dict.items(), key=lambda item: item[1]))

    def check_and_run(self):
        flag = True
        while flag:
            try:
                dict_for_mailing = dict()
                list_for_create_secret_santa = list()

                # Build a dict of colleagues for each member
                colleagues_dict = dict()
                for member in self.team.members.prefetch_related('colleagues'):
                    for colleague in member.colleagues.all():
                        if member in colleagues_dict:
                            colleagues_dict[member].append(colleague)
                        else:
                            colleagues_dict[member] = [colleague]

                colleagues_count_dict = self.get_colleagues_count_dict(colleagues_dict)

                # While there are members with colleagues — randomly assign a colleague as gift recipient
                while colleagues_count_dict:
                    member = list(colleagues_count_dict.keys())[0]
                    colleague = choice(colleagues_dict[member])
                    dict_for_mailing[member] = colleague.full_name
                    list_for_create_secret_santa.append(SecretSanta(santa=member, recipient=colleague, celebration=self))

                    # Remove assigned colleague and member from colleagues dict
                    colleagues_dict.pop(member)
                    for key, value in colleagues_dict.items():
                        if colleague in value:
                            value.remove(colleague)
                            colleagues_dict[key] = value
                    colleagues_count_dict = self.get_colleagues_count_dict(colleagues_dict)

                # Bulk create SecretSanta records
                SecretSanta.objects.bulk_create(list_for_create_secret_santa)

                # Send emails to each Santa
                for key, value in dict_for_mailing.items():
                    mailing(key, value)

                flag = False
            except Exception:
                # Empty except block — risk of infinite loop, logging errors is recommended
                pass

    def run(self):
        # Clear previous records and run assignment algorithm
        self.clear()
        self.check_and_run()

    def clear(self):
        # Delete all SecretSanta records for this Celebration
        self.secret_santas.all().delete()


class SecretSanta(models.Model):
    # Each Santa has a unique recipient (OneToOne)
    santa = models.OneToOneField(Member, verbose_name='Santa', related_name='me_santa', on_delete=models.CASCADE)
    recipient = models.OneToOneField(
        Member, verbose_name='Recipient of a gift from Santa', related_name='my_santa', on_delete=models.CASCADE
    )
    celebration = models.ForeignKey(Celebration, related_name='secret_santas', on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f'{self.santa} {self.recipient} {self.celebration}'

    class Meta:
        unique_together = ['santa', 'recipient', 'celebration']

    def resend_email(self) -> None:
        # Resend email for a specific Santa
        mailing(self.santa, self.recipient.name)
