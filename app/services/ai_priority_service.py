"""AI service for task prioritization using OpenAI."""

from typing import Dict, Protocol, Tuple

from app.db.models import Priority


class AIPriorityService(Protocol):
    """Protocol for AI priority service implementations."""

    async def suggest_priority(
        self, title: str, description: str | None
    ) -> tuple[Priority, str | None]:
        """
        Suggest priority and reason for a task based on its content.

        Args:
            title: Task title
            description: Optional task description

        Returns:
            Tuple of (Priority, reason_string or None)
        """
        ...


PriorityCacheKey = str
PriorityCacheValue = Tuple[Priority, str | None]

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
    ) -> tuple[Priority, str | None]:
        """
        Suggest priority using OpenAI API.

        Args:
            title: Task title
            description: Optional task description

        Returns:
            Tuple of (Priority, reason_string or None)
        """
        cache_key = _build_cache_key(title, description)
        if cache_key in _PRIORITY_CACHE:
            return _PRIORITY_CACHE[cache_key]

        if not self.api_key:
            result = (Priority.MEDIUM, None)
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
                        "content": (
                            "You are a task prioritization assistant. Analyze tasks and suggest priority "
                            "(low, medium, high) with a clear, natural language explanation. "
                            "Your explanation should mention specific keywords, factors, or context that influenced "
                            "the decision. Examples: 'Wysoki priorytet: zadanie zawiera słowa kluczowe 'pilne', "
                            "'deadline', oraz jest związane z terminem' or 'Średni priorytet: zadanie dotyczy "
                            "codziennych obowiązków bez określonego terminu'."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"{content}\n\n"
                            "Suggest priority and reason in format:\n"
                            "PRIORITY: <low|medium|high>\n"
                            "REASON: <natural language explanation mentioning key factors, keywords, or context>"
                        ),
                    },
                ],
                max_tokens=150,
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
            result = (Priority.MEDIUM, None)
            _PRIORITY_CACHE[cache_key] = result
            return result


class MockAIPriorityService:
    """Mock implementation for testing or when OpenAI is unavailable."""

    async def suggest_priority(
        self, title: str, description: str | None
    ) -> tuple[Priority, str | None]:
        """
        Mock priority suggestion based on simple heuristics.

        Args:
            title: Task title
            description: Optional task description

        Returns:
            Tuple of (Priority, reason_string or None)
        """
        cache_key = _build_cache_key(title, description)
        if cache_key in _PRIORITY_CACHE:
            return _PRIORITY_CACHE[cache_key]

        content = title.lower()
        if description:
            content += " " + description.lower()

        # Special handling: important exams in short time should be high priority
        exam_keywords = ["egzamin", "exam"]
        time_keywords = ["jutro", "dzisiaj", "dzis", "today", "tomorrow"]
        importance_keywords = [
            "bardzo ważny",
            "bardzo wazny",
            "ważny",
            "wazny",
            "critical",
            "important",
        ]

        is_exam_related = any(keyword in content for keyword in exam_keywords)
        is_time_sensitive = any(keyword in content for keyword in time_keywords)
        is_marked_important = any(keyword in content for keyword in importance_keywords)

        if is_exam_related and (is_time_sensitive or is_marked_important):
            result = (
                Priority.HIGH,
                "Wysoki priorytet: zadanie dotyczy ważnego egzaminu w krótkim terminie "
                "(słowa kluczowe: egzamin, jutro/bardzo ważny).",
            )
        else:
            # Find matching keywords for better explanations
            urgent_keywords = [
                word
                for word in [
                    "urgent",
                    "critical",
                    "asap",
                    "important",
                    "pilne",
                    "deadline",
                ]
                if word in content
            ]
            low_keywords = [
                word
                for word in [
                    "low",
                    "minor",
                    "later",
                    "opcjonalne",
                    "później",
                ]
                if word in content
            ]

            if urgent_keywords:
                keywords_str = ", ".join([f"'{kw}'" for kw in urgent_keywords[:3]])
                result = (
                    Priority.HIGH,
                    "Wysoki priorytet: zadanie zawiera słowa kluczowe "
                    f"{keywords_str}, oraz jest związane z terminem",
                )
            elif low_keywords:
                keywords_str = ", ".join([f"'{kw}'" for kw in low_keywords[:3]])
                result = (
                    Priority.LOW,
                    "Niski priorytet: zadanie ma charakter opcjonalny i może być "
                    f"wykonane później (słowa kluczowe: {keywords_str})",
                )
            else:
                result = (
                    Priority.MEDIUM,
                    "Średni priorytet: zadanie dotyczy codziennych obowiązków "
                    "bez określonego terminu",
                )

        _PRIORITY_CACHE[cache_key] = result
        return result

