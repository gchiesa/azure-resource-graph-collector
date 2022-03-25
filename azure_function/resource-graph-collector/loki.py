import json
import logging
from datetime import datetime
from typing import Tuple

from logging_loki import LokiHandler


class LokiCustomHandler(LokiHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(
            url=kwargs.get('url', None),
            tags=kwargs.get('tags', None),
            auth=kwargs.get('auth', None),
            version=kwargs.get('version', None),
        )
        self._logger_for_errors = kwargs.get('logger_for_errors', None)

    def emit(self, record: logging.LogRecord):
        """Send log record to Loki."""
        try:
            self.emitter(record, self.format(record))
        except Exception as e:
            self._logger_for_errors.error(f"Error while publishing on Loki instance. Type: {str(type(e))}, "
                                          f"Value: {str(e)}")
            self.emitter.close()
            raise


class LokiPublisher(object):
    def __init__(self, loki_endpoint: str, auth: Tuple[str, str], tags: dict):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.publisher = None
        self.endpoint = loki_endpoint
        self.auth = auth
        self.tags = tags
        self._initialize()

    def _initialize(self):
        self.publisher = logging.getLogger(f"{self.__class__.__name__}-publisher")
        for handler in self.publisher.handlers:
            self.publisher.removeHandler(handler)

        self.publisher.addHandler(LokiCustomHandler(url=self.endpoint,
                                                    tags=self.tags,
                                                    auth=self.auth,
                                                    version="1", logger_for_errors=self.logger))

    @staticmethod
    def _prepare_tags(data: dict):
        """cleanup the tags"""
        tags = {k: v for k, v in data.items() if isinstance(v, str)}
        return tags

    def publish(self, message: dict):
        timestamp = datetime.utcnow()
        data = {'timestamp': timestamp.isoformat()}
        data.update(message)
        self.logger.debug(f"Logging entry:\n---\n{json.dumps(data)}\n---")
        self.publisher.info(json.dumps(data), extra={'tags': self._prepare_tags(message)})
