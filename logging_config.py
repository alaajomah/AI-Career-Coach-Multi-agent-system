import logging
import json

logger = logging.getLogger("career_agent")
logger.setLevel(logging.INFO)

handler = logging.FileHandler("app.log")

class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps(record.msg)

handler.setFormatter(JsonFormatter())
logger.addHandler(handler)