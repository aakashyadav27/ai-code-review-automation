"""
Base agent class for code review agents.
Provides common functionality for all specialized agents.
"""
import os
from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum
import google.generativeai as genai


class IssueSeverity(str, Enum):
    """Severity levels for code issues."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class CodeIssue:
    """Represents a single code issue found during review."""
    file_path: str
    line_start: int
    line_end: Optional[int]
    severity: IssueSeverity
    category: str  # style, security, performance, logic
    title: str
    description: str
    suggestion: Optional[str] = None
    code_snippet: Optional[str] = None


@dataclass
class FileReview:
    """Review results for a single file."""
    file_path: str
    issues: List[CodeIssue]
    summary: str


class BaseAgent(ABC):
    """
    Base class for all code review agents.
    Each agent specializes in a specific type of code analysis.
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize the agent.
        
        Args:
            api_key: Optional single API key. If None, uses multi-provider with fallback.
        """
        self._single_key = api_key
        self._llm_client = None
        
        if api_key:
            # Use single Gemini key directly
            genai.configure(api_key=api_key)
            self._model = genai.GenerativeModel("gemini-2.0-flash")
        else:
            # Use multi-provider LLM client (Gemini + Groq fallback)
            from agents.llm_client import get_llm_client
            self._llm_client = get_llm_client()
    
    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Return the name of this agent (e.g., 'style', 'security')."""
        pass
    
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return the system prompt that defines this agent's behavior."""
        pass
    
    def _build_prompt(self, code: str, file_path: str, context: str = "") -> str:
        """
        Build the full prompt for the LLM.
        
        Args:
            code: The code to review
            file_path: Path of the file being reviewed
            context: Additional context (e.g., PR description)
        """
        return f"""{self.system_prompt}

## File Information
- **File Path**: {file_path}
- **Language**: {self._detect_language(file_path)}

## Additional Context
{context if context else "No additional context provided."}

## Code to Review
```
{code}
```

## Response Format
Respond with a JSON array of issues found. Each issue should have:
- "line_start": integer (1-indexed line number where issue starts)
- "line_end": integer or null (line where issue ends, null if single line)
- "severity": one of "critical", "high", "medium", "low", "info"
- "title": short title describing the issue (max 100 chars)
- "description": detailed explanation of the issue
- "suggestion": how to fix the issue (optional)
- "code_snippet": the problematic code snippet (optional)

If no issues are found, return an empty array: []

Return ONLY the JSON array, no other text.
"""
    
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        ext_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".jsx": "JavaScript (React)",
            ".tsx": "TypeScript (React)",
            ".go": "Go",
            ".rs": "Rust",
            ".java": "Java",
            ".rb": "Ruby",
            ".php": "PHP",
            ".c": "C",
            ".cpp": "C++",
            ".cs": "C#",
            ".swift": "Swift",
            ".kt": "Kotlin",
        }
        for ext, lang in ext_map.items():
            if file_path.endswith(ext):
                return lang
        return "Unknown"
    
    def _parse_response(self, response_text: str, file_path: str) -> List[CodeIssue]:
        """
        Parse LLM response into CodeIssue objects.
        
        Args:
            response_text: Raw text response from LLM
            file_path: Path of the file being reviewed
        """
        import json
        
        # Debug: print raw response
        if os.environ.get("DEBUG"):
            print(f"\n[DEBUG] Raw LLM response:\n{response_text[:500]}...")
        
        # Try to extract JSON from the response
        try:
            # Handle cases where LLM might wrap in markdown code blocks
            text = response_text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            
            # Also try to find JSON array in the response
            text = text.strip()
            if not text.startswith("["):
                # Try to find the JSON array
                start_idx = text.find("[")
                end_idx = text.rfind("]")
                if start_idx != -1 and end_idx != -1:
                    text = text[start_idx:end_idx + 1]
            
            issues_data = json.loads(text.strip())
            
            if not isinstance(issues_data, list):
                return []
            
            issues = []
            for item in issues_data:
                try:
                    issue = CodeIssue(
                        file_path=file_path,
                        line_start=item.get("line_start", 1),
                        line_end=item.get("line_end"),
                        severity=IssueSeverity(item.get("severity", "info").lower()),
                        category=self.agent_name,
                        title=item.get("title", "Issue found"),
                        description=item.get("description", ""),
                        suggestion=item.get("suggestion"),
                        code_snippet=item.get("code_snippet")
                    )
                    issues.append(issue)
                except (KeyError, ValueError) as e:
                    # Skip malformed issues
                    continue
            
            return issues
            
        except json.JSONDecodeError as e:
            # If parsing fails, print debug info and return empty list
            if os.environ.get("DEBUG"):
                print(f"\n[DEBUG] JSON parse error: {e}")
                print(f"[DEBUG] Attempted to parse: {text[:200]}...")
            return []
    
    async def review_code(
        self, 
        code: str, 
        file_path: str, 
        context: str = ""
    ) -> FileReview:
        """
        Review code and return issues found.
        
        Args:
            code: The code content to review
            file_path: Path of the file
            context: Additional context (PR description, etc.)
            
        Returns:
            FileReview object with issues and summary
        """
        prompt = self._build_prompt(code, file_path, context)
        
        try:
            # Use appropriate LLM based on configuration
            if self._single_key:
                response = self._model.generate_content(prompt)
                response_text = response.text
            else:
                # Use multi-provider LLM client with fallback
                response = self._llm_client.generate(prompt)
                response_text = response.text
            
            issues = self._parse_response(response_text, file_path)
            
            # Generate summary
            if issues:
                severity_counts = {}
                for issue in issues:
                    severity_counts[issue.severity.value] = severity_counts.get(
                        issue.severity.value, 0
                    ) + 1
                summary = f"Found {len(issues)} {self.agent_name} issue(s): " + \
                    ", ".join(f"{v} {k}" for k, v in severity_counts.items())
            else:
                summary = f"No {self.agent_name} issues found."
            
            return FileReview(
                file_path=file_path,
                issues=issues,
                summary=summary
            )
            
        except Exception as e:
            # Return empty review on error
            return FileReview(
                file_path=file_path,
                issues=[],
                summary=f"Error during {self.agent_name} review: {str(e)}"
            )
    
    async def review_files(
        self,
        files: List[dict],  # [{"path": str, "content": str}]
        context: str = ""
    ) -> List[FileReview]:
        """
        Review multiple files.
        
        Args:
            files: List of file dicts with 'path' and 'content' keys
            context: Additional context for all files
            
        Returns:
            List of FileReview objects
        """
        reviews = []
        for file_info in files:
            review = await self.review_code(
                code=file_info["content"],
                file_path=file_info["path"],
                context=context
            )
            reviews.append(review)
        return reviews
