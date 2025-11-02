
import logging, sys, json, time, os
from datetime import datetime, timezone

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        # Attach request/span ids if present
        for key in ("request_id","span_id","case_id"):
            val = getattr(record, key, None)
            if val:
                payload[key] = val
        return json.dumps(payload, ensure_ascii=False)

def setup_json_logging(level=os.environ.get("LOG_LEVEL","INFO")):
    logger = logging.getLogger()
    logger.setLevel(level)
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(JsonFormatter())
    logger.handlers = [h]
    return logger
