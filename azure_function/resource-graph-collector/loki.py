import json
import logging
from copy import deepcopy
from typing import Tuple, Optional, List

from logging_loki import LokiHandler

MAX_LABELS = 10


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
    def __init__(self, loki_endpoint: str, auth: Tuple[str, str], tags: Optional[dict] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.publisher = None
        self.endpoint = loki_endpoint
        self.auth = auth
        self.tags = tags or {}
        self._initialize()

    def _initialize(self):
        self.publisher = logging.getLogger(f"{self.__class__.__name__}-publisher")
        for handler in self.publisher.handlers:
            self.publisher.removeHandler(handler)

        self.publisher.addHandler(LokiCustomHandler(url=self.endpoint,
                                                    tags=self.tags,
                                                    auth=self.auth,
                                                    version="1", logger_for_errors=self.logger))

    def _prepare_tags(self, data: dict, fields_to_labels: Optional[List] = None):
        """loki only support X amount of tags"""
        tags = deepcopy(self.tags)
        if not fields_to_labels:
            return tags
        clean_tags = {k: v for k, v in data.items() if isinstance(v, str)}
        tags.update({k: v for k, v in clean_tags.items() if k in fields_to_labels})
        return tags

    def publish(self, message: dict, fields_to_labels: Optional[List] = None):
        tags = self._prepare_tags(message, fields_to_labels)
        self.logger.debug(f"TAGS[{len(tags)}]: {tags}")
        self.logger.info(f"Logging entry:\n---\n{json.dumps(message)}\n---")
        self.publisher.info(json.dumps(message), extra={'tags': tags})
