import logging
import sys
from io import StringIO
from typing import Optional

import bracelogger


class AppSingleton:
    __instance: Optional["AppSingleton"] = None
    __logger: logging.Logger = bracelogger.get_logger()
    __log_buffer: StringIO = StringIO()

    def __new__(cls) -> "AppSingleton":
        if cls.__instance is None:
            cls.__instance = super(AppSingleton, cls).__new__(cls)
            cls.__instance.setup_logger()
        return cls.__instance

    def setup_logger(self) -> None:

        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

        # Output messages to stderr continuously
        stderr_output = logging.StreamHandler(sys.stderr)
        stderr_output.setLevel(logging.DEBUG)
        stderr_output.setFormatter(formatter)
        self.__logger.addHandler(stderr_output)

        # Configure the logging module to use a StringIO object as a buffer
        # for log messages with level INFO and above
        self.__log_buffer = StringIO()
        buffered_output = logging.StreamHandler(self.__log_buffer)
        buffered_output.setLevel(logging.INFO)
        buffered_output.setFormatter(formatter)
        self.__logger.addHandler(buffered_output)

    def get_logger(self) -> logging.Logger:
        return self.__logger

    def reset_log_buffer(self) -> None:
        self.__log_buffer.truncate(0)

    def get_log_messages(self) -> str:
        log_messages = self.__log_buffer.getvalue()
        return log_messages


app_logger = AppSingleton().get_logger()
