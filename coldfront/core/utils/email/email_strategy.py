from abc import ABC
from abc import abstractmethod
from collections import deque
import logging


logger = logging.getLogger(__name__)


class EmailStrategy(ABC):
    """An interface that uses the Strategy design pattern to vary how
    emails are processed."""

    @abstractmethod
    def process_email(self, email_method, *email_args, **email_kwargs):
        """Given a method for sending an email, as well as arguments and
        keyword arguments for the method, perform some processing."""
        pass


class EnqueueEmailStrategy(EmailStrategy):
    """A strategy for enqueueing emails for later processing."""

    def __init__(self, queue=None):
        """Create a new queue (deque) or accept an existing one to
        update."""
        if queue is not None:
            assert isinstance(queue, deque)
            self._queue = queue
        else:
            self._queue = deque()

    def get_queue(self):
        """Return the underlying deque containing queued emails."""
        return self._queue

    def process_email(self, email_method, *email_args, **email_kwargs):
        """Given a method for sending an email, as well as arguments and
        keyword arguments for the method, enqueue the email to a
        queue."""
        self._queue.append((email_method, email_args, email_kwargs))

    def send_queued_emails(self):
        """Dequeue and send all emails in the queue."""
        while self._queue:
            item = self._queue.popleft()
            try:
                email_method, email_args, email_kwargs = item
                email_method(*email_args, **email_kwargs)
            except Exception as e:
                logger.exception(e)


class DropEmailStrategy(EmailStrategy):
    """A strategy for dropping emails."""

    def process_email(self, email_method, *email_args, **email_kwargs):
        """Given a method for sending an email, as well as arguments and
        keyword arguments for the method, drop the email."""
        pass


class SendEmailStrategy(EmailStrategy):
    """A strategy for sending emails immediately."""

    def process_email(self, email_method, *email_args, **email_kwargs):
        """Given a method for sending an email, as well as arguments and
        keyword arguments for the method, send the email immediately."""
        try:
            email_method(*email_args, **email_kwargs)
        except Exception as e:
            logger.exception(e)
