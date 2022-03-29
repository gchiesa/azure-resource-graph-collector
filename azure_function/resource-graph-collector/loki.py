import json
import logging
from copy import deepcopy
from typing import Tuple, Optional, List

from logging_loki.emitter import LokiEmitterV1

MAX_LABELS = 10


class LokiPublisher(object):
    def __init__(self, loki_endpoint: str, auth: Tuple[str, str], tags: Optional[dict] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.emitter = None
        self.endpoint = loki_endpoint
        self.auth = auth
        self.tags = tags or {}
        self._initialize()

    def _initialize(self):
        self.emitter = LokiEmitterV1(self.endpoint, self.tags, self.auth)

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
        self.logger.debug(f"Logging entry:\n---\n{json.dumps(message)}\n---")
        self.emitter(json.dumps(message), extra={'tags': tags})
