"""AI service for task prioritization using OpenAI."""

from typing import Dict, Protocol, Tuple

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


PriorityCacheKey = str
PriorityCacheValue = Tuple[Priority, str]

# Simple in-memory cache for priority suggestions.
# Key: normalized "title|description" string
_PRIORITY_CACHE: Dict[PriorityCacheKey, PriorityCacheValue] = {}


def _build_cache_key(title: str, description: str | None) -> PriorityCacheKey:
    normalized_title = title.strip().lower()
    normalized_description = (description or "").strip().lower()
    return f"{normalized_title}|{normalized_description}"


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
        cache_key = _build_cache_key(title, description)
        if cache_key in _PRIORITY_CACHE:
            return _PRIORITY_CACHE[cache_key]

        if not self.api_key:
            result = (Priority.MEDIUM, "AI service not configured")
            _PRIORITY_CACHE[cache_key] = result
            return result

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

            ai_result = response.choices[0].message.content or ""
            priority_value = Priority.MEDIUM
            reason = "AI analysis completed"

            for line in ai_result.split("\n"):
                if line.startswith("PRIORITY:"):
                    priority_text = line.split(":")[1].strip().lower()
                    if priority_text in ["low", "medium", "high"]:
                        priority_value = Priority(priority_text)
                elif line.startswith("REASON:"):
                    reason = line.split(":", 1)[1].strip()

            result: PriorityCacheValue = (priority_value, reason)
            _PRIORITY_CACHE[cache_key] = result
            return result

        except Exception:
            result = (Priority.MEDIUM, "AI service unavailable, using default priority")
            _PRIORITY_CACHE[cache_key] = result
            return result


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
        cache_key = _build_cache_key(title, description)
        if cache_key in _PRIORITY_CACHE:
            return _PRIORITY_CACHE[cache_key]

        content = title.lower()
        if description:
            content += " " + description.lower()

        if any(word in content for word in ["urgent", "critical", "asap", "important"]):
            result: PriorityCacheValue = (Priority.HIGH, "Contains urgent keywords")
        elif any(word in content for word in ["low", "minor", "later"]):
            result = (Priority.LOW, "Contains low-priority keywords")
        else:
            result = (Priority.MEDIUM, "Default priority based on content analysis")

        _PRIORITY_CACHE[cache_key] = result
        return result

