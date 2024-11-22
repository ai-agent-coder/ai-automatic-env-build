import sys
import argparse
import autogen
from typing import Dict, List
import os
import pytest
import ast
import requests
import json

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Generate and test code projects')
    parser.add_argument(
        '--requirements', '-r',
        type=str,
        required=True,
        help='Path to requirements file or direct requirements string'
    )
    parser.add_argument(
        '--workspace', '-w',
        type=str,
        default='coding_workspace',
        help='Directory for generated code and tests (default: coding_workspace)'
    )
    parser.add_argument(
        '--api-key',
        type=str,
        help='OpenRouter API key (optional, can also use OPENROUTER_API_KEY env var)'
    )
    return parser.parse_args()

class OpenRouterLLM:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        
    def generate_response(self, messages: List[Dict]) -> str:
        """
        Generate a response using the OpenRouter API.
        
        Args:
            messages: List of message dictionaries with role and content
        Returns:
            str: Generated response
        """
        try:
            response = requests.post(
                url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}"
                },
                data=json.dumps({
                    "model": "anthropic/claude-3.5-sonnet",
                    "messages": messages,
                    "top_p": 1,
                    "temperature": 0.1,  # Lower temperature for code generation
                    "frequency_penalty": 0,
                    "presence_penalty": 0,
                    "repetition_penalty": 1,
                    "top_k": 0,
                })
            )
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            raise Exception(f"Error generating response: {str(e)}")

class CodeProject:
    def __init__(self, workspace_dir: str, api_key: str):
        self.workspace_dir = workspace_dir
        self.llm = OpenRouterLLM(api_key)
        
    def get_llm_response(self, role: str, prompt: str) -> str:
        """Get response from LLM based on role and prompt."""
        system_messages = {
            "code_writer": "You are a skilled Python developer. Write clean, efficient, and well-documented code.",
            "code_reviewer": "You are a code reviewer. Analyze code for best practices, potential issues, and improvements.",
            "test_writer": "You are a test engineer. Write comprehensive unit tests and integration tests."
        }
        
        messages = [
            {"role": "system", "content": system_messages[role]},
            {"role": "user", "content": prompt}
        ]
        
        return self.llm.generate_response(messages)

    def validate_python_code(self, code: str) -> bool:
        """Validate if the code is syntactically correct Python code."""
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False
        
    def write_code_to_file(self, code: str, filename: str):
        """Write code to a file in the workspace directory."""
        os.makedirs(self.workspace_dir, exist_ok=True)
        with open(os.path.join(self.workspace_dir, filename), "w") as f:
            f.write(code)

    def extract_code_from_response(self, response: str) -> str:
        """Extract code blocks from LLM response."""
        code_blocks = [
            block for block in response.split("```python")
            if block.strip() and "```" in block
        ]
        
        if not code_blocks:
            raise ValueError("No code was generated")
            
        return code_blocks[0].split("```")[0].strip()

    def generate_project(self, requirements: str):
        """
        Generate a complete project based on requirements.
        
        Args:
            requirements (str): Project requirements and specifications
        """
        # Generate initial code
        code_response = self.get_llm_response(
            "code_writer",
            f"Generate Python code based on these requirements: {requirements}"
        )
        
        code = self.extract_code_from_response(code_response)
        
        if not self.validate_python_code(code):
            raise ValueError("Generated code is not valid Python")

        # Write the code to a file
        self.write_code_to_file(code, "main.py")

        # Get code review
        review_response = self.get_llm_response(
            "code_reviewer",
            f"Review this Python code:\n```python\n{code}\n```"
        )
        print("\nCode Review:")
        print(review_response)

        # Generate tests
        test_response = self.get_llm_response(
            "test_writer",
            f"Write unit tests for this code:\n```python\n{code}\n```"
        )
        
        test_code = self.extract_code_from_response(test_response)
        self.write_code_to_file(test_code, "test_main.py")

    def run_tests(self):
        """Run the generated tests using pytest."""
        try:
            pytest.main([os.path.join(self.workspace_dir, "test_main.py"), "-v"])
        except Exception as e:
            print(f"Error running tests: {e}")

class ProjectManager:
    def __init__(self, workspace_dir: str, api_key: str):
        self.project = CodeProject(workspace_dir, api_key)

    def create_project(self, requirements: str):
        """
        Create a new project with the given requirements.
        
        Args:
            requirements (str): Project requirements and specifications
        """
        try:
            print("Generating project...")
            self.project.generate_project(requirements)
            
            print("\nRunning tests...")
            self.project.run_tests()
            
            print("\nProject generation completed!")
            
        except Exception as e:
            print(f"Error creating project: {e}")

def read_requirements(requirements_path: str) -> str:
    """Read requirements from file if path is provided, otherwise return the string directly."""
    if os.path.isfile(requirements_path):
        with open(requirements_path, 'r') as f:
            return f.read()
    return requirements_path

def main():
    args = parse_arguments()
    
    # Get API key from command line or environment
    api_key = args.api_key or os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        print("Error: OpenRouter API key not provided. Use --api-key or set OPENROUTER_API_KEY environment variable.")
        sys.exit(1)
    
    # Read requirements
    requirements = read_requirements(args.requirements)
    
    # Create and run project
    manager = ProjectManager(args.workspace, api_key)
    manager.create_project(requirements)

if __name__ == "__main__":
    main()
