import json
import logging
from datetime import datetime
from typing import Tuple

import logging_loki


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

        self.publisher.addHandler(logging_loki.LokiHandler(url=self.endpoint,
                                                           tags=self.tags,
                                                           auth=self.auth,
                                                           version="1"))

    @staticmethod
    def _prepare_tags(data: dict):
        tags = {k: v for k, v in data.items() if isinstance(v, str)}
        return tags

    def publish(self, message: dict):
        timestamp = datetime.utcnow()
        data = {'timestamp': timestamp.isoformat()}
        data.update(message)
        # tag_data = self._prepare_tags(data)
        self.logger.debug(f"Logging entry:\n---\n{json.dumps(data)}\n---")
        # self.logger.info(f"tags: \n---\n{tag_data}\n---")
        # self.publisher.info(json.dumps(data), extra={'tags': tag_data})
        self.publisher.info(json.dumps(data))
