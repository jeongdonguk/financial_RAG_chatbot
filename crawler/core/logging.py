import logging
import os
import sys
import traceback
from logging.handlers import TimedRotatingFileHandler
from pythonjsonlogger import jsonlogger

# 로그 저장 디렉토리 및 파일 설정
LOG_DIR = "./logs"
BASE_LOG_FILE = "app.log"
LOG_PATH = os.path.join(LOG_DIR, BASE_LOG_FILE)

# stdout/stderr 인코딩 보정 (Docker 환경 대응)
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["filename"] = record.filename
        log_record["funcName"] = record.funcName
        log_record["lineno"] = record.lineno

        # 에러일 경우 traceback 포함
        if record.levelno >= logging.ERROR:
            exc = record.exc_info or sys.exc_info()
            if exc and exc[0] is not None:
                log_record["traceback"] = "".join(traceback.format_exception(*exc))

        # 사용자 정의 필드 처리
        for k, v in message_dict.items():
            log_record[k] = v

    def format(self, record):
        # 한글 인코딩 깨짐 방지
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = record.msg.encode('utf-8').decode('utf-8')
        return super().format(record)

    def jsonify_log_record(self, log_record):
        import json
        return json.dumps(log_record, ensure_ascii=False, default=str)


class RequestLoggerAdapter(logging.LoggerAdapter):
    """
    사용 예:
    log.info("처리 완료", request=req, extra={"message": "..."})
    """
    def process(self, msg, kwargs):
        request = kwargs.pop("request", None)
        extra = kwargs.setdefault("extra", {})
        extra.setdefault("message", msg)

        if request:
            extra.update({
                "path": request.url.path,
            })
        return msg, kwargs


def _ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def get_logger(name: str = "app", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # 중복 방지

    _ensure_log_dir()
    logger.setLevel(level)

    formatter = CustomJsonFormatter(
        "%(asctime)s %(level)s %(logger)s %(filename)s:%(lineno)d %(funcName)s %(message)s",
        rename_fields={"asctime": "timestamp"},
    )

    # 콘솔 핸들러 (Fluent Bit 수집용)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    sh.setLevel(level)
    logger.addHandler(sh)

    # 파일 핸들러 (자정 회전, 10일 보관)
    fh = TimedRotatingFileHandler(
        LOG_PATH,
        when="midnight",
        interval=1,
        backupCount=10,
        encoding="utf-8",
        utc=False,
        delay=True,
    )
    fh.suffix = "%Y-%m-%d"
    fh.setFormatter(formatter)
    fh.setLevel(level)
    logger.addHandler(fh)

    logger.propagate = False
    return logger


def get_request_logger(name: str = "app") -> RequestLoggerAdapter:
    return RequestLoggerAdapter(get_logger(name), {})
