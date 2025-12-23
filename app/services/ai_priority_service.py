"""AI service for task prioritization using OpenAI."""

from typing import Protocol

from app.db.models import Priority


class AIPriorityService(Protocol):
    """Protocol for AI priority service implementations."""

    async def suggest_priority(
        self, title: str, description: str | None
    ) -> tuple[Priority, str]:
        """
        Suggest priority and reason for a task based on its content.
        
        Args:
            title: Task title
            description: Optional task description
            
        Returns:
            Tuple of (Priority, reason_string)
        """
        ...


class OpenAIPriorityService:
    """OpenAI-based implementation of AI priority service."""

    def __init__(self, api_key: str) -> None:
        """Initialize OpenAI service with API key."""
        self.api_key = api_key
        self._client = None

    async def suggest_priority(
        self, title: str, description: str | None
    ) -> tuple[Priority, str]:
        """
        Suggest priority using OpenAI API.
        
        Args:
            title: Task title
            description: Optional task description
            
        Returns:
            Tuple of (Priority, reason_string)
        """
        if not self.api_key:
            return Priority.MEDIUM, "AI service not configured"

        try:
            from openai import OpenAI

            if self._client is None:
                self._client = OpenAI(api_key=self.api_key)

            content = f"Title: {title}"
            if description:
                content += f"\nDescription: {description}"

            response = self._client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a task prioritization assistant. Analyze tasks and suggest priority (low, medium, high) with a brief reason.",
                    },
                    {
                        "role": "user",
                        "content": f"{content}\n\nSuggest priority and reason in format: PRIORITY: <low|medium|high>\nREASON: <brief explanation>",
                    },
                ],
                max_tokens=100,
                temperature=0.3,
            )

            result = response.choices[0].message.content or ""
            priority_str = Priority.MEDIUM
            reason = "AI analysis completed"

            for line in result.split("\n"):
                if line.startswith("PRIORITY:"):
                    priority_text = line.split(":")[1].strip().lower()
                    if priority_text in ["low", "medium", "high"]:
                        priority_str = Priority(priority_text)
                elif line.startswith("REASON:"):
                    reason = line.split(":", 1)[1].strip()

            return priority_str, reason

        except Exception:
            return Priority.MEDIUM, "AI service unavailable, using default priority"


class MockAIPriorityService:
    """Mock implementation for testing or when OpenAI is unavailable."""

    async def suggest_priority(
        self, title: str, description: str | None
    ) -> tuple[Priority, str]:
        """
        Mock priority suggestion based on simple heuristics.
        
        Args:
            title: Task title
            description: Optional task description
            
        Returns:
            Tuple of (Priority, reason_string)
        """
        content = title.lower()
        if description:
            content += " " + description.lower()

        if any(word in content for word in ["urgent", "critical", "asap", "important"]):
            return Priority.HIGH, "Contains urgent keywords"
        elif any(word in content for word in ["low", "minor", "later"]):
            return Priority.LOW, "Contains low-priority keywords"
        else:
            return Priority.MEDIUM, "Default priority based on content analysis"

