import json
import logging
from copy import deepcopy
from typing import Tuple, Optional, List

from logging_loki.emitter import LokiEmitterV1
from logging import LogRecord

MAX_LABELS = 10
LOKI_EVENT_NAME = "LokiPublisher"
LOKI_EVENT_LOG_LEVEL = logging.INFO


def make_loki_event(message, tags) -> LogRecord:
    global LOKI_EVENT_NAME, LOKI_EVENT_LOG_LEVEL
    log_record = LogRecord(
        name=LOKI_EVENT_NAME,
        level=LOKI_EVENT_LOG_LEVEL,
        pathname="",
        lineno=0,
        msg=message,
        args=None,
        exc_info=None,
    )
    setattr(log_record, "tags", tags)
    return log_record


class LokiPublisher(object):
    def __init__(
        self, loki_endpoint: str, auth: Tuple[str, str], tags: Optional[dict] = None
    ):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.endpoint = loki_endpoint
        self.auth = auth
        self.tags = tags or {}
        self.emitter = LokiEmitterV1(self.endpoint, self.tags, self.auth)

    def _prepare_tags(self, data: dict, fields_to_labels: Optional[List] = None):
        """loki only support MAX_LABELS amount of tags"""
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
        loki_event = make_loki_event(message, tags)
        self.emitter(loki_event, json.dumps(message))
