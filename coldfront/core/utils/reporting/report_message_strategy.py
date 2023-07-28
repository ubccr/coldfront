import logging

from abc import ABC

from django.core.management.base import BaseCommand
from django.utils.termcolors import colorize


class ReportMessageStrategy(ABC):
    """An interface that uses the Strategy design pattern to vary how
    messages are reported."""

    def error(self, message):
        raise NotImplementedError

    def success(self, message):
        raise NotImplementedError

    def warning(self, message):
        raise NotImplementedError


class EnqueueForLoggingStrategy(ReportMessageStrategy):
    """A strategy for enqueueing messages to be written to a logging instance
    later."""

    def __init__(self, logger):
        assert isinstance(logger, logging.Logger)
        self._logger = logger
        # Tuples of the form (logging_func, message).
        self._queue = []

    def error(self, message):
        logging_func = self._logger.error
        self._queue.append((logging_func, message))

    def success(self, message):
        logging_func = self._logger.info
        self._queue.append((logging_func, message))

    def warning(self, message):
        logging_func = self._logger.warning
        self._queue.append((logging_func, message))

    def log_queued_messages(self):
        for logging_func, message in self._queue:
            logging_func(message)


class PrintStrategy(ReportMessageStrategy):
    """A strategy for printing messages."""

    def error(self, message):
        print(colorize(text=message, fg="red"))

    def success(self, message):
        print(colorize(text=message, fg="green"))

    def warning(self, message):
        print(colorize(text=message, fg="yellow"))


class WriteViaCommandStrategy(ReportMessageStrategy):
    """A strategy for writing messages to stdout/stderr via a Django
    management command."""

    def __init__(self, command):
        assert isinstance(command, BaseCommand)
        self._command = command

    def error(self, message):
        stream = self._command.stderr
        style = self._command.style.ERROR
        stream.write(style(message))

    def success(self, message):
        stream = self._command.stdout
        style = self._command.style.SUCCESS
        stream.write(style(message))

    def warning(self, message):
        stream = self._command.stdout
        style = self._command.style.WANRING
        stream.write(style(message))
