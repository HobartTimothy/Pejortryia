import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """初始化全局日志配置。

    - 输出到 stdout，格式：时间 | 级别 | 模块:行号 | 消息
    - 将 aiogram 内部事件日志降噪为 WARNING，避免刷屏
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
