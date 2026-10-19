"""
修复Agent (FixAgent)

负责根据审查结果自动修复代码中的问题。
接收代码和审查结果，输出修复后的代码。
"""
from typing import Any, Dict, List
import re

from .base import BaseAgent


class FixAgent(BaseAgent):
    """
    修复Agent - 根据审查结果修复代码问题

    输入：审查结果字典（来自ReviewAgent）
    输出：修复后的代码结果字典
    """

    def __init__(self, name: str = "FixAgent"):
        super().__init__(name, description="根据审查结果修复代码问题的Agent")

    def execute(self, input_data: Any) -> Dict[str, Any]:
        """
        根据审查结果修复代码

        Args:
            input_data: 审查结果数据
                - 必须包含 original_code, issues, language 等字段

        Returns:
            修复结果字典:
                - fixed_code: 修复后的代码
                - original_code: 原始代码
                - fixes_applied: 应用的修复列表
                - remaining_issues: 剩余未修复的问题
                - fix_count: 修复数量
                - language: 编程语言
        """
        self.log_info("开始修复代码问题...")

        # 解析输入
        if isinstance(input_data, dict):
            original_code = input_data.get("original_code", input_data.get("code", ""))
            issues = input_data.get("issues", [])
            language = input_data.get("language", "python")
            filename = input_data.get("filename", "fixed_output.py")
        else:
            raise ValueError(f"不支持的输入类型: {type(input_data)}")

        if not original_code:
            raise ValueError("原始代码不能为空")

        self.log_info(f"待修复问题数: {len(issues)}")

        # 执行修复
        fixed_code = original_code
        fixes_applied = []
        remaining_issues = []

        for issue in issues:
            issue_type = issue.get("type", "")
            severity = issue.get("severity", "info")

            # 尝试修复
            try:
                result = self._apply_fix(fixed_code, issue, language)
                if result["fixed"]:
                    fixed_code = result["code"]
                    fixes_applied.append({
                        "issue": issue["message"],
                        "fix": result["fix_description"],
                        "severity": severity,
                    })
                    self.log_debug(f"已修复: {issue['message']}")
                else:
                    remaining_issues.append(issue)
            except Exception as e:
                self.log_warning(f"修复失败: {issue['message']} - {e}")
                remaining_issues.append(issue)

        result = {
            "fixed_code": fixed_code,
            "original_code": original_code,
            "fixes_applied": fixes_applied,
            "remaining_issues": remaining_issues,
            "fix_count": len(fixes_applied),
            "language": language,
            "filename": filename,
            "summary": (
                f"修复完成：共修复 {len(fixes_applied)} 个问题，"
                f"剩余 {len(remaining_issues)} 个问题需人工处理"
            ),
        }

        self.log_info(result["summary"])

        # 保存到全局状态
        self.set_state_data("fixed_code", result)

        return result

    def _apply_fix(self, code: str, issue: Dict, language: str) -> Dict:
        """
        应用单个修复

        Returns:
            {
                "fixed": bool,
                "code": str,      # 修复后的代码
                "fix_description": str,
            }
        """
        issue_type = issue.get("type", "")
        message = issue.get("message", "")

        # 根据问题类型应用不同的修复策略
        if issue_type == "style":
            return self._fix_style(code, issue, language)
        elif issue_type == "naming":
            return self._fix_naming(code, issue, language)
        elif issue_type == "syntax":
            return self._fix_syntax(code, issue, language)
        elif issue_type == "comments":
            return self._fix_comments(code, issue, language)
        elif issue_type == "error_handling":
            return self._fix_error_handling(code, issue, language)
        else:
            return {"fixed": False, "code": code, "fix_description": ""}

    def _fix_style(self, code: str, issue: Dict, language: str) -> Dict:
        """修复代码风格问题"""
        message = issue.get("message", "")

        # 修复行尾空格
        if "行尾空格" in message:
            lines = code.split("\n")
            fixed_lines = [line.rstrip() for line in lines]
            return {
                "fixed": True,
                "code": "\n".join(fixed_lines),
                "fix_description": "删除了所有行尾空格",
            }

        return {"fixed": False, "code": code, "fix_description": ""}

    def _fix_naming(self, code: str, issue: Dict, language: str) -> Dict:
        """修复命名规范问题"""
        message = issue.get("message", "")
        suggestion = issue.get("suggestion", "")

        # 修复类名（大驼峰）
        if "类名" in message and "大驼峰" in message:
            # 提取类名
            import re
            match = re.search(r"类名 '(\w+)'", message)
            if match:
                old_name = match.group(1)
                new_name = old_name[0].upper() + old_name[1:]
                fixed_code = re.sub(
                    rf'\bclass\s+{old_name}\b',
                    f'class {new_name}',
                    code
                )
                # 同时替换构造函数中的引用
                fixed_code = re.sub(
                    rf'\b{old_name}\(',
                    f'{new_name}(',
                    fixed_code
                )
                return {
                    "fixed": True,
                    "code": fixed_code,
                    "fix_description": f"类名 {old_name} -> {new_name}",
                }

        return {"fixed": False, "code": code, "fix_description": ""}

    def _fix_syntax(self, code: str, issue: Dict, language: str) -> Dict:
        """修复语法问题"""
        message = issue.get("message", "")

        # 修复未闭合的括号（简单情况）
        if "未闭合的括号" in message:
            details = issue.get("details", [])
            if details:
                closing_map = {"(": ")", "[": "]", "{": "}"}
                extra_closing = "".join(closing_map.get(b, b) for b in reversed(details))
                # 在最后一个非空行添加闭合括号
                lines = code.rstrip().split("\n")
                lines[-1] = lines[-1] + extra_closing
                return {
                    "fixed": True,
                    "code": "\n".join(lines) + "\n",
                    "fix_description": f"补充了 {len(details)} 个未闭合的括号",
                }

        # 修复Python 2风格的print
        if "print" in message and "括号" in message:
            fixed_code = re.sub(r'\bprint\s+([^(\n]+)', r'print(\1)', code)
            if fixed_code != code:
                return {
                    "fixed": True,
                    "code": fixed_code,
                    "fix_description": "将 Python 2 风格 print 改为函数调用",
                }

        return {"fixed": False, "code": code, "fix_description": ""}

    def _fix_comments(self, code: str, issue: Dict, language: str) -> Dict:
        """修复注释问题（添加基本文档字符串）"""
        message = issue.get("message", "")

        if "缺少文档字符串" in message and language == "python":
            import re
            match = re.search(r"函数 '(\w+)' 缺少文档字符串", message)
            if match:
                func_name = match.group(1)
                # 找到函数定义行，在后面添加docstring
                pattern = rf'(def\s+{func_name}\s*\([^)]*\)\s*:)'
                replacement = rf'\1\n        """{func_name}函数。\n\n        Args:\n            待补充\n\n        Returns:\n            待补充\n        """'
                fixed_code = re.sub(pattern, replacement, code, count=1)
                if fixed_code != code:
                    return {
                        "fixed": True,
                        "code": fixed_code,
                        "fix_description": f"为函数 {func_name} 添加了文档字符串模板",
                    }

        return {"fixed": False, "code": code, "fix_description": ""}

    def _fix_error_handling(self, code: str, issue: Dict, language: str) -> Dict:
        """修复错误处理问题"""
        message = issue.get("message", "")

        # 修复裸露的except
        if "裸露的 except" in message and language == "python":
            # 将裸露的 except 改为 except Exception
            fixed_code = re.sub(r'except\s*:', 'except Exception:', code)
            if fixed_code != code:
                return {
                    "fixed": True,
                    "code": fixed_code,
                    "fix_description": "将裸露的 except 改为 except Exception",
                }

        return {"fixed": False, "code": code, "fix_description": ""}
