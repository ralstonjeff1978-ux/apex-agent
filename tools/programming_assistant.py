"""
PROGRAMMING ASSISTANT - Code Generation and Annotation
=====================================================
Focused programming assistant that generates code based on prompts.

Features:
- Code generation from natural language descriptions
- Code annotation and documentation
- Debugging assistance
- Code review and optimization suggestions
- Multi-language support
- Integration with existing file tools
"""

import re
import ast
import json
import yaml
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging

log = logging.getLogger("programming_assistant")

_CONFIG_PATH = Path(__file__).parent.parent / "core" / "config.yaml"


def _storage_base() -> Path:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return Path(cfg.get("storage", {}).get("base", "C:/ai_agent/apex/data"))


class ProgrammingAssistant:
    def __init__(self):
        self.supported_languages = ['python', 'javascript', 'html', 'css', 'json']
        self.code_templates = self._load_code_templates()

    def _load_code_templates(self) -> Dict:
        """Load code templates for common patterns"""
        return {
            'python_class': '''class {class_name}:
    """{description}"""

    def __init__(self{init_params}):
        """Initialize {class_name}"""
        pass

    def {method_name}(self{method_params}):
        """{method_description}"""
        pass''',

            'python_function': '''def {function_name}({params}):
    """{description}

    Args:
        {param_descriptions}

    Returns:
        {return_type}: {return_description}
    """
    pass''',

            'flask_route': '''@app.route('/{route}', methods=['{methods}'])
def {function_name}():
    """{description}"""
    return {response}'''
        }

    def analyze_prompt(self, prompt: str) -> Dict:
        """Analyze programming prompt to determine requirements"""
        analysis = {
            'language': 'python',
            'task_type': 'unknown',
            'required_libraries': [],
            'complexity': 'medium',
            'file_operations': False,
            'web_framework': None,
            'data_processing': False
        }

        prompt_lower = prompt.lower()

        # Detect language
        if 'javascript' in prompt_lower or 'js' in prompt_lower:
            analysis['language'] = 'javascript'
        elif 'html' in prompt_lower:
            analysis['language'] = 'html'
        elif 'css' in prompt_lower:
            analysis['language'] = 'css'

        # Detect task type
        if 'class' in prompt_lower or 'object' in prompt_lower:
            analysis['task_type'] = 'class_creation'
        elif 'function' in prompt_lower or 'def' in prompt_lower:
            analysis['task_type'] = 'function_creation'
        elif 'web' in prompt_lower or 'api' in prompt_lower or 'flask' in prompt_lower:
            analysis['task_type'] = 'web_application'
            analysis['web_framework'] = 'flask'
        elif 'data' in prompt_lower or 'process' in prompt_lower or 'analyze' in prompt_lower:
            analysis['task_type'] = 'data_processing'
            analysis['data_processing'] = True
        elif 'file' in prompt_lower or 'read' in prompt_lower or 'write' in prompt_lower:
            analysis['task_type'] = 'file_operations'
            analysis['file_operations'] = True

        # Detect required libraries
        libraries = []
        if 'requests' in prompt_lower:
            libraries.append('requests')
        if 'pandas' in prompt_lower or 'dataframe' in prompt_lower:
            libraries.append('pandas')
        if 'numpy' in prompt_lower or 'array' in prompt_lower:
            libraries.append('numpy')
        if 'flask' in prompt_lower:
            libraries.append('flask')
        if 'json' in prompt_lower:
            libraries.append('json')

        analysis['required_libraries'] = libraries

        # Assess complexity
        if len(prompt.split()) > 50 or 'complex' in prompt_lower:
            analysis['complexity'] = 'high'
        elif len(prompt.split()) < 10:
            analysis['complexity'] = 'low'

        return analysis

    def generate_code(self, prompt: str, clarification_callback=None) -> str:
        """Generate code based on prompt"""
        try:
            analysis = self.analyze_prompt(prompt)
            log.info("Prompt analysis: %s", analysis)

            if analysis['task_type'] == 'class_creation':
                return self._generate_class(prompt, analysis)
            elif analysis['task_type'] == 'function_creation':
                return self._generate_function(prompt, analysis)
            elif analysis['task_type'] == 'web_application':
                return self._generate_web_app(prompt, analysis)
            elif analysis['task_type'] == 'data_processing':
                return self._generate_data_processing(prompt, analysis)
            elif analysis['task_type'] == 'file_operations':
                return self._generate_file_operations(prompt, analysis)
            else:
                return self._generate_generic_code(prompt, analysis)

        except Exception as e:
            log.error("Code generation error: %s", e)
            return f"# Error generating code: {str(e)}\n# Please provide more specific requirements"

    def _generate_class(self, prompt: str, analysis: Dict) -> str:
        """Generate a Python class"""
        class_name_match = re.search(
            r'(?:create|make|build)\s+a?\s+(?:class|object)\s+called\s+(\w+)',
            prompt, re.IGNORECASE
        )
        class_name = class_name_match.group(1) if class_name_match else "MyClass"
        description = prompt.split('.')[0] if '.' in prompt else prompt

        code = f'''class {class_name}:
    """{description}"""

    def __init__(self):
        """Initialize {class_name}"""
        pass

    def example_method(self):
        """Example method"""
        pass

# Usage example:
# obj = {class_name}()
# obj.example_method()
'''
        return code

    def _generate_function(self, prompt: str, analysis: Dict) -> str:
        """Generate a Python function"""
        func_name_match = re.search(
            r'(?:create|make|build|write)\s+a?\s+function\s+called\s+(\w+)',
            prompt, re.IGNORECASE
        )
        func_name = func_name_match.group(1) if func_name_match else "my_function"

        code = f'''def {func_name}():
    """{prompt}"""
    # TODO: Implement function logic
    pass

# Usage example:
# result = {func_name}()
'''
        return code

    def _generate_web_app(self, prompt: str, analysis: Dict) -> str:
        """Generate a web application"""
        code = '''from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    """Home page"""
    return "Hello, World!"

@app.route('/api/data', methods=['GET'])
def get_data():
    """Get data endpoint"""
    return jsonify({"message": "Data retrieved successfully"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
'''
        return code

    def _generate_data_processing(self, prompt: str, analysis: Dict) -> str:
        """Generate data processing code"""
        code = '''import pandas as pd
import numpy as np

def process_data(data):
    """Process the input data

    Args:
        data: Input data to process

    Returns:
        Processed data
    """
    if not isinstance(data, pd.DataFrame):
        df = pd.DataFrame(data)
    else:
        df = data

    print(f"Processing {len(df)} rows of data")

    return df

# Usage example:
# data = pd.read_csv('data.csv')
# processed_data = process_data(data)
'''
        return code

    def _generate_file_operations(self, prompt: str, analysis: Dict) -> str:
        """Generate file operations code"""
        code = '''import os
import json

def read_file(filepath):
    """Read file content

    Args:
        filepath: Path to the file

    Returns:
        File content as string
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"File {filepath} not found")
        return None
    except Exception as e:
        print(f"Error reading file: {e}")
        return None

def write_file(filepath, content):
    """Write content to file

    Args:
        filepath: Path to the file
        content: Content to write
    """
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"File written successfully: {filepath}")
    except Exception as e:
        print(f"Error writing file: {e}")

# Usage examples:
# content = read_file('input.txt')
# write_file('output.txt', 'Hello, World!')
'''
        return code

    def _generate_generic_code(self, prompt: str, analysis: Dict) -> str:
        """Generate generic code based on prompt"""
        code = f'''#!/usr/bin/env python3
"""
{prompt}
"""

def main():
    """Main function"""
    print("Implementing: {prompt}")
    # TODO: Add your implementation here
    pass

if __name__ == "__main__":
    main()
'''
        return code

    def annotate_code(self, code: str, style: str = "google") -> str:
        """Add documentation and annotations to code"""
        try:
            if code.strip().startswith('def ') or 'def ' in code:
                return self._annotate_python_functions(code, style)
            elif code.strip().startswith('class ') or 'class ' in code:
                return self._annotate_python_classes(code, style)
            else:
                return self._annotate_generic(code, style)
        except Exception as e:
            log.error("Annotation error: %s", e)
            return f"# Original code preserved due to annotation error\n{code}"

    def _annotate_python_functions(self, code: str, style: str) -> str:
        """Add docstrings to Python functions"""
        lines = code.split('\n')
        annotated_lines = []

        for line in lines:
            annotated_lines.append(line)

            if line.strip().startswith('def ') and ':' in line:
                indent = len(line) - len(line.lstrip())
                func_def = line.strip()
                func_name = func_def.split('def ')[1].split('(')[0]
                params = func_def.split('(')[1].split(')')[0] if '(' in func_def else ""

                docstring = f'{"".ljust(indent + 4)}"""TODO: Document {func_name}'
                if params:
                    docstring += f'\n{"".ljust(indent + 4)}Args:'
                    for param in params.split(','):
                        param = param.strip()
                        if param and param != 'self':
                            docstring += f'\n{"".ljust(indent + 8)}{param}: Description of {param}'
                docstring += f'\n{"".ljust(indent + 4)}"""'
                annotated_lines.append(docstring)

        return '\n'.join(annotated_lines)

    def _annotate_python_classes(self, code: str, style: str) -> str:
        """Add docstrings to Python classes"""
        lines = code.split('\n')
        annotated_lines = []

        for line in lines:
            annotated_lines.append(line)

            if line.strip().startswith('class ') and ':' in line:
                indent = len(line) - len(line.lstrip())
                docstring = f'{"".ljust(indent + 4)}"""TODO: Document this class"""'
                annotated_lines.append(docstring)

        return '\n'.join(annotated_lines)

    def _annotate_generic(self, code: str, style: str) -> str:
        """Add generic annotations"""
        annotated_lines = ['# ========================================']
        annotated_lines.append('# AUTO-GENERATED CODE')
        annotated_lines.append('# ========================================')
        annotated_lines.append('')

        for line in code.split('\n'):
            annotated_lines.append(line)

        annotated_lines.append('')
        annotated_lines.append('# ========================================')
        annotated_lines.append('# END OF AUTO-GENERATED CODE')
        annotated_lines.append('# ========================================')

        return '\n'.join(annotated_lines)

    def review_code(self, code: str) -> Dict:
        """Review code for common issues and improvements"""
        issues = []
        suggestions = []

        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                issues.append(f"Line {i}: line too long ({len(line)} chars)")
            if 'TODO' in line:
                suggestions.append(f"Line {i}: unresolved TODO")

        return {
            "issues": issues,
            "suggestions": suggestions,
            "line_count": len(lines),
            "quality": "good" if not issues else "needs_review"
        }

    def debug_code(self, code: str, error_message: str = "") -> str:
        """Provide debugging suggestions for code"""
        suggestions = []

        if error_message:
            if "SyntaxError" in error_message:
                suggestions.append("Check for missing colons, parentheses, or indentation errors.")
            if "NameError" in error_message:
                suggestions.append("Ensure all variables and functions are defined before use.")
            if "TypeError" in error_message:
                suggestions.append("Check argument types and counts in function calls.")
            if "ImportError" in error_message or "ModuleNotFoundError" in error_message:
                suggestions.append("Verify the module is installed and the import path is correct.")

        if not suggestions:
            suggestions.append("Review logic flow and add print statements to trace execution.")

        debug_notes = '\n'.join(f"# DEBUG: {s}" for s in suggestions)
        return f"{debug_notes}\n\n{code}"


_programming_assistant = None


def get_programming_assistant() -> ProgrammingAssistant:
    """Get or create the singleton ProgrammingAssistant instance"""
    global _programming_assistant
    if _programming_assistant is None:
        _programming_assistant = ProgrammingAssistant()
    return _programming_assistant


def register_tools(registry) -> None:
    """Register programming assistant tools with the agent registry"""
    assistant = get_programming_assistant()

    registry.register("tools_analyze_prompt", assistant.analyze_prompt)
    registry.register("tools_generate_code", assistant.generate_code)
    registry.register("tools_annotate_code", assistant.annotate_code)
    registry.register("tools_review_code", assistant.review_code)
    registry.register("tools_debug_code", assistant.debug_code)
