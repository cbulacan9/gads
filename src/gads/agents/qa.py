"""
QA Agent for GADS

Testing, validation, and quality assurance.
Uses local Ollama models for review and validation tasks.
"""

from __future__ import annotations

from typing import Any

from .base import BaseAgent, AgentResponse


class QAAgent(BaseAgent):
    """
    The QA agent handles testing and validation.
    
    Responsibilities:
    - Code review and validation
    - Test case generation
    - Bug identification
    - Quality assurance checks
    """
    
    def _default_system_prompt(self) -> str:
        return """You are the QA agent in the GADS (Godot Agentic Development System).

Your role is to ensure quality through testing and validation for Godot 4.x game projects.

## Responsibilities

1. **Code Review**
   - Check GDScript for errors and anti-patterns
   - Verify Godot best practices
   - Identify potential bugs
   - Suggest improvements

2. **Test Case Generation**
   - Create test scenarios
   - Define edge cases
   - Plan regression tests
   - Document expected behavior

3. **Validation**
   - Verify implementation matches design
   - Check asset specifications
   - Validate scene structure
   - Ensure consistency

4. **Quality Checks**
   - Performance considerations
   - Memory management
   - Input handling
   - Error handling

## Output Format

For code review:
- **Issues Found**: List with severity (Critical/Warning/Info)
- **Suggestions**: Improvements to consider
- **Verdict**: Pass/Fail/Needs Work

For test cases:
- **Test Name**: Descriptive identifier
- **Setup**: Initial conditions
- **Steps**: Actions to perform
- **Expected**: What should happen

Always be thorough but constructive in feedback.
"""
    
    async def execute(
        self,
        user_input: str,
        context: dict[str, Any],
        history: list[dict[str, str]] | None = None,
    ) -> AgentResponse:
        """Execute QA tasks."""
        messages = []
        
        if history:
            messages.extend(history[-10:])
        
        messages.append({"role": "user", "content": user_input})
        
        response_text, usage = await self._call_llm(messages)
        
        artifacts = self._extract_qa_artifacts(response_text)
        
        return AgentResponse(
            content=response_text,
            agent_name=self.name,
            model=self.config.model,
            artifacts=artifacts,
            usage=usage,
        )
    
    def _extract_qa_artifacts(self, response: str) -> dict[str, Any]:
        """Extract QA-related artifacts from response."""
        artifacts = {}
        
        response_lower = response.lower()
        
        if "critical" in response_lower:
            artifacts["has_critical_issues"] = True
        
        if "pass" in response_lower or "approved" in response_lower:
            artifacts["verdict"] = "pass"
        elif "fail" in response_lower:
            artifacts["verdict"] = "fail"
        
        return artifacts
