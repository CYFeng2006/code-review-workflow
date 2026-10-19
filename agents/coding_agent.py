"""
编码Agent (CodingAgent)

负责根据需求描述生成代码。
作为代码审查流程的第一个Agent，接收需求输入，输出代码。
"""
from typing import Any, Dict, List
import re

from .base import BaseAgent


class CodingAgent(BaseAgent):
    """
    编码Agent - 根据需求生成代码

    输入：需求描述（字符串或字典）
    输出：生成的代码（字典，包含code, language, filename等）
    """

    def __init__(self, name: str = "CodingAgent"):
        super().__init__(name, description="根据需求生成代码的Agent")
        self.code_templates = {
            "python": self._generate_python,
            "javascript": self._generate_javascript,
        }

    def execute(self, input_data: Any) -> Dict[str, Any]:
        """
        根据需求生成代码

        Args:
            input_data: 需求描述，可以是字符串或字典
                - 字符串：直接作为需求描述
                - 字典：包含 requirement, language, filename 等字段

        Returns:
            生成结果字典：
                - code: 生成的代码
                - language: 编程语言
                - filename: 文件名
                - requirement: 原始需求
                - description: 代码功能描述
        """
        self.log_info("开始生成代码...")

        # 解析输入
        if isinstance(input_data, str):
            requirement = input_data
            language = "python"
            filename = "output.py"
        elif isinstance(input_data, dict):
            requirement = input_data.get("requirement", input_data.get("description", ""))
            language = input_data.get("language", "python").lower()
            filename = input_data.get("filename", f"output.{self._get_extension(language)}")
        else:
            raise ValueError(f"不支持的输入类型: {type(input_data)}")

        if not requirement:
            raise ValueError("需求描述不能为空")

        self.log_info(f"需求: {requirement[:50]}...")
        self.log_info(f"语言: {language}")

        # 根据需求生成代码
        code = self._generate_code(requirement, language)

        result = {
            "code": code,
            "language": language,
            "filename": filename,
            "requirement": requirement,
            "description": f"实现了 {requirement} 的功能",
            "lines_of_code": len(code.strip().split("\n")),
        }

        self.log_info(f"代码生成完成，共 {result['lines_of_code']} 行")

        # 保存到全局状态
        self.set_state_data("generated_code", result)

        return result

    def _generate_code(self, requirement: str, language: str) -> str:
        """根据需求和语言生成代码"""
        generator = self.code_templates.get(language, self._generate_python)
        return generator(requirement)

    def _generate_python(self, requirement: str) -> str:
        """生成Python代码模板"""
        # 根据需求关键词决定生成什么样的代码
        req_lower = requirement.lower()

        if "排序" in requirement or "sort" in req_lower:
            return '''def sort_list(lst, reverse=False):
    """
    对列表进行排序

    Args:
        lst: 待排序的列表
        reverse: 是否降序排列

    Returns:
        排序后的新列表
    """
    if not isinstance(lst, list):
        raise TypeError("输入必须是列表类型")
    
    result = lst.copy()
    for i in range(len(result)):
        for j in range(0, len(result) - i - 1):
            if reverse:
                if result[j] < result[j + 1]:
                    result[j], result[j + 1] = result[j + 1], result[j]
            else:
                if result[j] > result[j + 1]:
                    result[j], result[j + 1] = result[j + 1], result[j]
    return result


if __name__ == "__main__":
    numbers = [64, 34, 25, 12, 22, 11, 90]
    print("原始列表:", numbers)
    print("升序排序:", sort_list(numbers))
    print("降序排序:", sort_list(numbers, reverse=True))
'''
        elif "计算器" in requirement or "calculator" in req_lower:
            return '''class Calculator:
    """简单计算器类"""

    def add(self, a, b):
        """加法"""
        return a + b

    def subtract(self, a, b):
        """减法"""
        return a - b

    def multiply(self, a, b):
        """乘法"""
        return a * b

    def divide(self, a, b):
        """除法"""
        if b == 0:
            raise ValueError("除数不能为零")
        return a / b

    def power(self, base, exp):
        """幂运算"""
        return base ** exp


if __name__ == "__main__":
    calc = Calculator()
    print(f"10 + 5 = {calc.add(10, 5)}")
    print(f"10 - 5 = {calc.subtract(10, 5)}")
    print(f"10 * 5 = {calc.multiply(10, 5)}")
    print(f"10 / 5 = {calc.divide(10, 5)}")
    print(f"2 ^ 10 = {calc.power(2, 10)}")
'''
        elif "待办" in requirement or "todo" in req_lower:
            return '''class TodoList:
    """待办事项管理"""

    def __init__(self):
        self.items = []

    def add(self, task):
        """添加待办事项"""
        self.items.append({"task": task, "done": False})
        return len(self.items)

    def complete(self, index):
        """标记为已完成"""
        if 0 <= index < len(self.items):
            self.items[index]["done"] = True
            return True
        return False

    def remove(self, index):
        """删除待办事项"""
        if 0 <= index < len(self.items):
            self.items.pop(index)
            return True
        return False

    def list_all(self):
        """列出所有待办"""
        return self.items.copy()

    def list_pending(self):
        """列出未完成的待办"""
        return [item for item in self.items if not item["done"]]


if __name__ == "__main__":
    todo = TodoList()
    todo.add("学习Python")
    todo.add("完成作业")
    todo.complete(0)
    print("所有待办:", todo.list_all())
    print("未完成:", todo.list_pending())
'''
        else:
            # 通用模板
            func_name = self._snake_case(requirement[:20])
            return f'''def {func_name}(input_data):
    """
    {requirement}

    Args:
        input_data: 输入数据

    Returns:
        处理后的结果
    """
    # TODO: 实现具体逻辑
    result = input_data
    return result


if __name__ == "__main__":
    # 示例用法
    data = "test"
    output = {func_name}(data)
    print(f"输入: {{data}}, 输出: {{output}}")
'''

    def _generate_javascript(self, requirement: str) -> str:
        """生成JavaScript代码模板"""
        func_name = self._camel_case(requirement[:20])
        return f'''function {func_name}(inputData) {{
    /**
     * {requirement}
     * 
     * @param {{*}} inputData - 输入数据
     * @returns {{*}} 处理后的结果
     */
    // TODO: 实现具体逻辑
    const result = inputData;
    return result;
}}

// 示例用法
const data = "test";
const output = {func_name}(data);
console.log(`输入: ${{data}}, 输出: ${{output}}`);
'''

    @staticmethod
    def _get_extension(language: str) -> str:
        """根据语言获取文件扩展名"""
        ext_map = {
            "python": "py",
            "javascript": "js",
            "java": "java",
            "c++": "cpp",
            "cpp": "cpp",
            "go": "go",
            "rust": "rs",
        }
        return ext_map.get(language.lower(), "txt")

    @staticmethod
    def _snake_case(text: str) -> str:
        """转换为蛇形命名"""
        text = re.sub(r"[^\w\s]", "", text)
        text = re.sub(r"\s+", "_", text.strip().lower())
        return text[:30] or "main"

    @staticmethod
    def _camel_case(text: str) -> str:
        """转换为驼峰命名"""
        words = re.sub(r"[^\w\s]", "", text).strip().split()
        if not words:
            return "main"
        return words[0].lower() + "".join(w.capitalize() for w in words[1:])
