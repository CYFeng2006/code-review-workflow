"""
审查Agent (ReviewAgent)

负责审查代码质量，检查语法错误、代码规范、潜在问题等。
输出审查结果，包括是否通过、问题列表、评分等。
"""
from typing import Any, Dict, List
import re

from .base import BaseAgent


class ReviewAgent(BaseAgent):
    """
    审查Agent - 对代码进行质量审查

    输入：代码字典（来自CodingAgent的输出）
    输出：审查结果字典
    """

    def __init__(self, name: str = "ReviewAgent"):
        super().__init__(name, description="审查代码质量的Agent")
        self.checks = [
            self._check_syntax,
            self._check_naming,
            self._check_comments,
            self._check_error_handling,
            self._check_complexity,
            self._check_style,
        ]

    def execute(self, input_data: Any) -> Dict[str, Any]:
        """
        审查代码质量

        Args:
            input_data: 代码数据（字典或字符串）
                - 字典: 包含 code, language, filename 等字段
                - 字符串: 直接作为代码内容

        Returns:
            审查结果字典:
                - passed: 是否通过审查
                - score: 评分 (0-100)
                - issues: 问题列表
                - suggestions: 改进建议
                - summary: 审查摘要
        """
        self.log_info("开始代码审查...")

        # 解析输入
        if isinstance(input_data, dict):
            code = input_data.get("code", "")
            language = input_data.get("language", "python")
            filename = input_data.get("filename", "unknown")
        elif isinstance(input_data, str):
            code = input_data
            language = "python"
            filename = "unknown"
        else:
            raise ValueError(f"不支持的输入类型: {type(input_data)}")

        if not code:
            raise ValueError("代码内容不能为空")

        self.log_info(f"审查文件: {filename}")
        self.log_info(f"代码行数: {len(code.strip().split(chr(10)))}")

        # 执行各项检查
        issues = []
        for check in self.checks:
            try:
                check_issues = check(code, language)
                issues.extend(check_issues)
            except Exception as e:
                self.log_warning(f"检查 {check.__name__} 出错: {e}")

        # 计算评分
        score = self._calculate_score(issues)

        # 生成建议
        suggestions = self._generate_suggestions(issues)

        # 判断是否通过
        passed = score >= 60 and not any(
            issue.get("severity") == "critical" for issue in issues
        )

        # 统计问题严重程度
        critical_count = sum(1 for i in issues if i["severity"] == "critical")
        warning_count = sum(1 for i in issues if i["severity"] == "warning")
        info_count = sum(1 for i in issues if i["severity"] == "info")

        result = {
            "passed": passed,
            "score": score,
            "total_issues": len(issues),
            "critical_count": critical_count,
            "warning_count": warning_count,
            "info_count": info_count,
            "issues": issues,
            "suggestions": suggestions,
            "summary": (
                f"代码审查{'通过' if passed else '未通过'}，"
                f"评分: {score}/100，"
                f"发现 {len(issues)} 个问题 "
                f"(严重: {critical_count}, 警告: {warning_count}, 信息: {info_count})"
            ),
            "original_code": code,
            "language": language,
            "filename": filename,
        }

        self.log_info(result["summary"])

        # 保存到全局状态
        self.set_state_data("review_result", result)

        return result

    def _check_syntax(self, code: str, language: str) -> List[Dict]:
        """检查语法问题"""
        issues = []

        if language == "python":
            # 检查基本语法问题
            lines = code.split("\n")
            indent_stack = [0]  # 缩进栈

            for i, line in enumerate(lines, 1):
                stripped = line.rstrip()
                if not stripped.strip():
                    continue

                # 检查缩进（简化版）
                indent = len(stripped) - len(stripped.lstrip())
                if stripped.strip().endswith(":"):
                    # 下一行应该缩进更多
                    indent_stack.append(indent)

            # 检查括号匹配
            stack = []
            for i, char in enumerate(code):
                if char in "([{":
                    stack.append(char)
                elif char in ")]}":
                    if not stack:
                        issues.append({
                            "type": "syntax",
                            "severity": "critical",
                            "message": f"多余的闭合括号 '{char}'",
                            "position": i,
                        })
                    else:
                        opening = stack.pop()
                        if (opening == "(" and char != ")") or \
                           (opening == "[" and char != "]") or \
                           (opening == "{" and char != "}"):
                            issues.append({
                                "type": "syntax",
                                "severity": "critical",
                                "message": f"括号不匹配: 期望匹配 '{opening}'，实际为 '{char}'",
                                "position": i,
                            })

            if stack:
                issues.append({
                    "type": "syntax",
                    "severity": "critical",
                    "message": f"有 {len(stack)} 个未闭合的括号",
                    "details": stack,
                })

            # 检查是否有print忘记加括号（Python3）
            if re.search(r'\bprint\s+[^(]', code):
                issues.append({
                    "type": "syntax",
                    "severity": "warning",
                    "message": "可能存在 Python 2 风格的 print 语句（缺少括号）",
                    "check": "使用 print() 函数语法",
                })

        return issues

    def _check_naming(self, code: str, language: str) -> List[Dict]:
        """检查命名规范"""
        issues = []

        if language == "python":
            # 检查类名是否为大驼峰
            class_matches = re.findall(r'class\s+(\w+)', code)
            for cls_name in class_matches:
                if not cls_name[0].isupper():
                    issues.append({
                        "type": "naming",
                        "severity": "warning",
                        "message": f"类名 '{cls_name}' 不符合大驼峰命名规范",
                        "suggestion": f"应改为 '{cls_name[0].upper() + cls_name[1:]}'",
                    })

            # 检查函数名是否为蛇形
            func_matches = re.findall(r'def\s+(\w+)', code)
            for func_name in func_matches:
                if func_name.startswith("__") and func_name.endswith("__"):
                    continue  # 魔术方法跳过
                if re.search(r'[A-Z]', func_name):
                    issues.append({
                        "type": "naming",
                        "severity": "info",
                        "message": f"函数名 '{func_name}' 建议使用蛇形命名",
                        "suggestion": "使用小写字母和下划线",
                    })

        return issues

    def _check_comments(self, code: str, language: str) -> List[Dict]:
        """检查注释和文档字符串"""
        issues = []

        if language == "python":
            # 检查函数是否有文档字符串
            func_pattern = r'def\s+(\w+)\s*\([^)]*\)\s*:'
            lines = code.split("\n")

            func_indices = []
            for i, line in enumerate(lines):
                if re.match(func_pattern, line.strip()):
                    match = re.match(func_pattern, line.strip())
                    func_indices.append((i, match.group(1)))

            for idx, func_name in func_indices:
                if func_name.startswith("__"):
                    continue
                # 查找下一个非空行
                next_line = ""
                for j in range(idx + 1, min(idx + 5, len(lines))):
                    if lines[j].strip():
                        next_line = lines[j].strip()
                        break

                if not next_line.startswith('"""') and not next_line.startswith("'''"):
                    issues.append({
                        "type": "comments",
                        "severity": "info",
                        "message": f"函数 '{func_name}' 缺少文档字符串",
                        "suggestion": "添加 docstring 说明函数功能、参数和返回值",
                    })

            # 注释比例检查
            total_lines = len([l for l in lines if l.strip()])
            comment_lines = len([l for l in lines if l.strip().startswith("#")])
            if total_lines > 20 and comment_lines / total_lines < 0.05:
                issues.append({
                    "type": "comments",
                    "severity": "info",
                    "message": "代码注释比例较低",
                    "suggestion": "建议添加适当的注释说明复杂逻辑",
                })

        return issues

    def _check_error_handling(self, code: str, language: str) -> List[Dict]:
        """检查错误处理"""
        issues = []

        if language == "python":
            # 检查是否有裸露的 except
            bare_excepts = re.findall(r'except\s*:', code)
            if bare_excepts:
                issues.append({
                    "type": "error_handling",
                    "severity": "warning",
                    "message": f"发现 {len(bare_excepts)} 处裸露的 except",
                    "suggestion": "应指定具体的异常类型，避免捕获所有异常",
                })

            # 检查除法操作是否有零除保护
            divide_ops = re.findall(r'/\s*(\w+)', code)
            if divide_ops and "except ZeroDivisionError" not in code and "if.*!= 0" not in code:
                issues.append({
                    "type": "error_handling",
                    "severity": "info",
                    "message": "除法操作可能存在除零风险",
                    "suggestion": "添加除零检查或捕获 ZeroDivisionError",
                })

        return issues

    def _check_complexity(self, code: str, language: str) -> List[Dict]:
        """检查代码复杂度"""
        issues = []

        if language == "python":
            lines = code.split("\n")

            # 检查函数长度
            func_start = -1
            func_name = ""
            for i, line in enumerate(lines):
                if line.strip().startswith("def "):
                    func_start = i
                    func_name = line.strip().split("def ")[1].split("(")[0]
                elif func_start >= 0 and line.strip() and not line[0].isspace() and not line.strip().startswith("#"):
                    func_length = i - func_start
                    if func_length > 50:
                        issues.append({
                            "type": "complexity",
                            "severity": "warning",
                            "message": f"函数 '{func_name}' 过长 ({func_length} 行)",
                            "suggestion": "建议拆分为多个小函数以提高可读性",
                        })
                    func_start = -1

            # 检查嵌套深度
            max_depth = 0
            current_depth = 0
            for line in lines:
                stripped = line.strip()
                if stripped.endswith(":") and not stripped.startswith("#"):
                    current_depth += 1
                    max_depth = max(max_depth, current_depth)
                elif stripped.startswith("return") or stripped.startswith("break"):
                    current_depth = max(0, current_depth - 1)

            if max_depth > 4:
                issues.append({
                    "type": "complexity",
                    "severity": "warning",
                    "message": f"代码嵌套深度较深 (最大 {max_depth} 层)",
                    "suggestion": "建议通过提前返回或提取函数来降低嵌套深度",
                })

        return issues

    def _check_style(self, code: str, language: str) -> List[Dict]:
        """检查代码风格"""
        issues = []

        if language == "python":
            lines = code.split("\n")

            # 检查行长度
            long_lines = [(i + 1, len(l)) for i, l in enumerate(lines) if len(l) > 100]
            if long_lines:
                issues.append({
                    "type": "style",
                    "severity": "info",
                    "message": f"有 {len(long_lines)} 行超过 100 字符",
                    "suggestion": "建议将长行拆分为多行以提高可读性",
                    "details": [f"第 {ln} 行 ({length} 字符)" for ln, length in long_lines[:5]],
                })

            # 检查行尾空格
            trailing_space_lines = [i + 1 for i, l in enumerate(lines) if l.rstrip() != l and l.strip()]
            if trailing_space_lines:
                issues.append({
                    "type": "style",
                    "severity": "info",
                    "message": f"有 {len(trailing_space_lines)} 行存在行尾空格",
                    "suggestion": "删除行尾空格以保持代码整洁",
                })

            # 检查是否有 TODO 注释
            todos = re.findall(r'TODO[^\n]*', code)
            if todos:
                issues.append({
                    "type": "style",
                    "severity": "info",
                    "message": f"发现 {len(todos)} 个 TODO 注释",
                    "suggestion": "在提交前完成 TODO 项",
                    "details": todos[:5],
                })

        return issues

    def _calculate_score(self, issues: List[Dict]) -> int:
        """根据问题计算评分"""
        score = 100
        for issue in issues:
            severity = issue.get("severity", "info")
            if severity == "critical":
                score -= 20
            elif severity == "warning":
                score -= 5
            elif severity == "info":
                score -= 2
        return max(0, min(100, score))

    def _generate_suggestions(self, issues: List[Dict]) -> List[str]:
        """生成改进建议"""
        suggestions = []
        for issue in issues:
            if issue.get("suggestion"):
                suggestions.append(issue["suggestion"])
        return suggestions[:5]  # 最多返回5条建议
