"""
EduClaw 日志工具模块
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""

    # ANSI 颜色代码
    COLORS = {
        'DEBUG': '\033[36m',    # 青色
        'INFO': '\033[32m',     # 绿色
        'WARNING': '\033[33m',  # 黄色
        'ERROR': '\033[31m',    # 红色
        'CRITICAL': '\033[35m', # 紫色
        'RESET': '\033[0m'      # 重置
    }

    def __init__(self, fmt: str, use_colors: bool = True):
        """
        初始化格式化器

        Args:
            fmt: 格式字符串
            use_colors: 是否使用颜色
        """
        super().__init__(fmt)
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        """
        格式化日志记录

        Args:
            record: 日志记录

        Returns:
            格式化后的字符串
        """
        levelname = record.levelname

        if self.use_colors:
            color = self.COLORS.get(levelname, '')
            reset = self.COLORS['RESET']
            record.levelname = f"{color}{levelname}{reset}"

        return super().format(record)


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    use_colors: bool = True
) -> logging.Logger:
    """
    设置并返回一个日志记录器

    Args:
        name: 日志记录器名称
        level: 日志级别
        log_file: 日志文件路径（可选）
        use_colors: 是否使用彩色输出

    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)

    # 避免重复配置
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # 格式字符串
    fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    datefmt = '%Y-%m-%d %H:%M:%S'

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = ColoredFormatter(fmt, use_colors=use_colors)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # 文件处理器（如果指定）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(fmt, datefmt=datefmt)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


# 全局日志记录器字典
_loggers: dict[str, logging.Logger] = {}


def get_logger(
    name: str,
    level: Optional[int] = None,
    log_file: Optional[str] = None,
    use_colors: bool = True
) -> logging.Logger:
    """
    获取或创建日志记录器（单例模式）

    Args:
        name: 日志记录器名称
        level: 日志级别（仅首次创建时有效）
        log_file: 日志文件路径（仅首次创建时有效）
        use_colors: 是否使用彩色输出（仅首次创建时有效）

    Returns:
        日志记录器
    """
    if name not in _loggers:
        _loggers[name] = setup_logger(name, level, log_file, use_colors)
    return _loggers[name]


def set_global_level(level: int):
    """
    设置全局日志级别

    Args:
        level: 日志级别
    """
    for logger in _loggers.values():
        logger.setLevel(level)
        for handler in logger.handlers:
            handler.setLevel(level)


class LoggerContext:
    """
    日志上下文管理器

    用于临时改变日志级别
    """

    def __init__(self, logger: logging.Logger, temporary_level: int):
        """
        初始化上下文

        Args:
            logger: 日志记录器
            temporary_level: 临时日志级别
        """
        self.logger = logger
        self.temporary_level = temporary_level
        self.original_level = None

    def __enter__(self):
        """进入上下文"""
        self.original_level = self.logger.level
        self.logger.setLevel(self.temporary_level)
        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        self.logger.setLevel(self.original_level)
        return False


def log_function_call(logger: logging.Logger):
    """
    装饰器：记录函数调用

    Args:
        logger: 日志记录器
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger.debug(f"Calling function: {func.__name__}")
            try:
                result = func(*args, **kwargs)
                logger.debug(f"Function {func.__name__} completed successfully")
                return result
            except Exception as e:
                logger.error(f"Function {func.__name__} failed: {e}")
                raise
        return wrapper
    return decorator


class LogBuffer:
    """
    日志缓冲区

    用于捕获日志并在需要时输出
    """

    def __init__(self, logger: logging.Logger, level: int = logging.INFO):
        """
        初始化日志缓冲区

        Args:
            logger: 日志记录器
            level: 捕获的日志级别
        """
        self.logger = logger
        self.level = level
        self.buffer: list[str] = []
        self.handler = None

    def start(self):
        """开始捕获日志"""
        self.buffer.clear()
        self.handler = logging.Handler()
        self.handler.setLevel(self.level)
        self.handler.emit = lambda record: self.buffer.append(
            self.logger.handlers[0].formatter.format(record)
        )
        self.logger.addHandler(self.handler)

    def stop(self):
        """停止捕获日志"""
        if self.handler:
            self.logger.removeHandler(self.handler)
            self.handler = None

    def get_buffer(self) -> list[str]:
        """获取缓冲区内容"""
        return self.buffer.copy()

    def clear(self):
        """清空缓冲区"""
        self.buffer.clear()
