"""
日志模块 - Workflow执行日志与状态追踪
"""
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
import json
import sys


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

    @property
    def level_order(self) -> int:
        """级别排序，数值越大越严重"""
        levels = {"debug": 0, "info": 1, "warning": 2, "error": 3}
        return levels[self.value]


class WorkflowLogger:
    """
    Workflow执行日志记录器

    支持：
    - 分级日志输出
    - 按trace_id追踪
    - 彩色终端输出
    - 日志历史记录
    - 自定义日志回调
    """

    # 终端颜色
    COLORS = {
        "debug": "\033[36m",    # 青色
        "info": "\033[32m",     # 绿色
        "warning": "\033[33m",  # 黄色
        "error": "\033[31m",    # 红色
        "reset": "\033[0m",
        "agent": "\033[35m",    # 紫色
        "workflow": "\033[34m", # 蓝色
    }

    def __init__(
        self,
        level: LogLevel = LogLevel.INFO,
        use_color: bool = True,
        output_handler: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.level = level
        self.use_color = use_color
        self.output_handler = output_handler
        self._logs: List[Dict[str, Any]] = []
        self._indent_level = 0

    def _should_log(self, level: LogLevel) -> bool:
        """判断是否应该输出该级别日志"""
        return level.level_order >= self.level.level_order

    def _log(
        self,
        level: LogLevel,
        message: str,
        component: str = "workflow",
        trace_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ):
        """记录一条日志"""
        if not self._should_log(level):
            return

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level.value,
            "component": component,
            "message": message,
            "trace_id": trace_id or "main",
            "extra": extra or {},
        }

        self._logs.append(log_entry)

        # 输出到终端
        self._print_log(log_entry)

        # 自定义回调
        if self.output_handler:
            self.output_handler(log_entry)

    def _print_log(self, log: Dict[str, Any]):
        """格式化打印日志"""
        indent = "  " * self._indent_level
        ts = log["timestamp"][11:23]  # 只取时间部分

        if self.use_color:
            color = self.COLORS.get(log["level"], "")
            comp_color = self.COLORS.get("agent" if log["component"] != "workflow" else "workflow", "")
            reset = self.COLORS["reset"]
            print(
                f"{color}[{ts}]{reset} "
                f"{comp_color}[{log['component']}]{reset} "
                f"{indent}{log['message']}"
            )
        else:
            print(f"[{ts}] [{log['component']}] {indent}{log['message']}")

    # --- 便捷方法 ---

    def debug(self, message: str, component: str = "workflow",
              trace_id: Optional[str] = None, **kwargs):
        """DEBUG级别日志"""
        self._log(LogLevel.DEBUG, message, component, trace_id, kwargs)

    def info(self, message: str, component: str = "workflow",
             trace_id: Optional[str] = None, **kwargs):
        """INFO级别日志"""
        self._log(LogLevel.INFO, message, component, trace_id, kwargs)

    def warning(self, message: str, component: str = "workflow",
                trace_id: Optional[str] = None, **kwargs):
        """WARNING级别日志"""
        self._log(LogLevel.WARNING, message, component, trace_id, kwargs)

    def error(self, message: str, component: str = "workflow",
              trace_id: Optional[str] = None, **kwargs):
        """ERROR级别日志"""
        self._log(LogLevel.ERROR, message, component, trace_id, kwargs)

    # --- 上下文管理（缩进）---

    def push_indent(self):
        """增加缩进层级"""
        self._indent_level += 1

    def pop_indent(self):
        """减少缩进层级"""
        if self._indent_level > 0:
            self._indent_level -= 1

    # --- 历史记录 ---

    @property
    def logs(self) -> List[Dict[str, Any]]:
        """获取所有日志"""
        return list(self._logs)

    def get_logs_by_trace(self, trace_id: str) -> List[Dict[str, Any]]:
        """按trace_id过滤日志"""
        return [log for log in self._logs if log["trace_id"] == trace_id]

    def get_logs_by_level(self, level: LogLevel) -> List[Dict[str, Any]]:
        """按级别过滤日志"""
        return [log for log in self._logs if log["level"] == level.value]

    def export_json(self) -> str:
        """导出日志为JSON"""
        return json.dumps(self._logs, ensure_ascii=False, indent=2)

    def clear(self):
        """清空日志"""
        self._logs.clear()

    def summary(self) -> Dict[str, int]:
        """获取日志统计"""
        counts = {"debug": 0, "info": 0, "warning": 0, "error": 0}
        for log in self._logs:
            counts[log["level"]] = counts.get(log["level"], 0) + 1
        return counts
