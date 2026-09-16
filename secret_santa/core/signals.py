import logging

logger = logging.getLogger(__name__)


def change_member(sender, instance, **kwargs):
    try:
        member = getattr(instance, 'member', None)
        if member is None:
            logger.warning('User id=%s has no linked Member instance.', instance.id)
            return

        new_hashed_email = member.get_hashed_email()
        if member.hashed_email != new_hashed_email:
            member.hashed_email = new_hashed_email
            member.save(update_fields=['hashed_email'])
            logger.info('Updated hashed_email for Member id=%s', member.id)
    except Exception:
        logger.exception('Error in change_member signal for User id=%s', instance.id)