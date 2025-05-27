import logging

logger = logging.getLogger(__name__)


def change_member(sender, instance, **kwargs):
    try:
        member = getattr(instance, 'member', None)
        if member is None:
            logger.warning(f'User id={instance.id} has no linked Member instance.')
            return

        new_hashed_email = member.get_hashed_email()
        if member.hashed_email != new_hashed_email:
            member.hashed_email = new_hashed_email
            member.save(update_fields=['hashed_email'])
            logger.info(f'Updated hashed_email for Member id={member.id}')
    except Exception as e:
        logger.error(f'Error in change_member signal for User id={instance.id}: {e}', exc_info=True)
