"""Unit tests for AI priority service implementations."""

import pytest

import app.services.ai_priority_service as module
from app.db.models import Priority
from app.services.ai_priority_service import MockAIPriorityService, OpenAIPriorityService


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the shared priority cache before and after each test."""
    module._PRIORITY_CACHE.clear()
    yield
    module._PRIORITY_CACHE.clear()


def make_openai_response(mocker, content: str):
    response = mocker.MagicMock()
    response.choices[0].message.content = content
    return response


# ---------------------------------------------------------------------------
# MockAIPriorityService
# ---------------------------------------------------------------------------


class TestMockAIPriorityService:
    @pytest.fixture
    def service(self):
        return MockAIPriorityService()

    async def test_high_priority_urgent_keywords(self, service):
        priority, reason = await service.suggest_priority("Fix urgent production bug", None)
        assert priority == Priority.HIGH
        assert "urgent" in reason

    async def test_high_priority_deadline_in_description(self, service):
        priority, reason = await service.suggest_priority("Prepare report", "deadline tomorrow")
        assert priority == Priority.HIGH
        assert "deadline" in reason

    async def test_high_priority_exam_tomorrow(self, service):
        priority, reason = await service.suggest_priority("egzamin jutro", None)
        assert priority == Priority.HIGH
        assert reason is not None

    async def test_high_priority_exam_important(self, service):
        # "ważny" is only in importance_keywords, not in urgent_keywords —
        # HIGH here can only come from the exam path, not the urgent-keyword path
        priority, reason = await service.suggest_priority("exam ważny", None)
        assert priority == Priority.HIGH
        assert "egzaminu" in reason  # exam-path has a distinct reason message

    async def test_high_priority_exam_critical(self, service):
        # "dzisiaj" is only in time_keywords, not in urgent_keywords —
        # ensures the exam+time path is exercised, not the urgent-keyword fallback
        priority, reason = await service.suggest_priority("egzamin dzisiaj", None)
        assert priority == Priority.HIGH
        assert "egzaminu" in reason  # exam-path has a distinct reason message

    async def test_low_priority_optional_keywords(self, service):
        priority, reason = await service.suggest_priority("opcjonalne zadanie", None)
        assert priority == Priority.LOW
        assert "opcjonalne" in reason

    async def test_low_priority_later(self, service):
        priority, reason = await service.suggest_priority("do this later", None)
        assert priority == Priority.LOW

    async def test_medium_priority_no_keywords(self, service):
        priority, reason = await service.suggest_priority("Buy groceries", None)
        assert priority == Priority.MEDIUM
        assert reason is not None

    async def test_medium_priority_with_neutral_description(self, service):
        priority, reason = await service.suggest_priority("Weekly meeting", "discuss roadmap")
        assert priority == Priority.MEDIUM

    async def test_description_adds_keywords(self, service):
        """Keyword in description should influence priority even with neutral title."""
        priority, _ = await service.suggest_priority("Task", "this is urgent")
        assert priority == Priority.HIGH

    async def test_cache_hit_returns_same_result(self, service):
        """Second call with same input must hit cache, not recompute."""
        await service.suggest_priority("Buy milk", None)
        key = module._build_cache_key("Buy milk", None)
        module._PRIORITY_CACHE[key] = (Priority.LOW, "cached")

        second = await service.suggest_priority("Buy milk", None)
        assert second == (Priority.LOW, "cached")

    async def test_cache_key_normalization(self, service):
        """Whitespace and case differences map to the same cache key."""
        await service.suggest_priority("  Buy Milk  ", None)
        key = module._build_cache_key("buy milk", None)
        assert key in module._PRIORITY_CACHE

    async def test_result_stored_in_cache(self, service):
        await service.suggest_priority("urgent fix", None)
        key = module._build_cache_key("urgent fix", None)
        assert key in module._PRIORITY_CACHE

    # --- edge cases ---

    async def test_exam_keyword_alone_is_medium(self, service):
        # exam without time/importance modifier must NOT trigger the exam path
        priority, _ = await service.suggest_priority("egzamin", None)
        assert priority == Priority.MEDIUM

    async def test_conflicting_urgent_and_low_keywords_urgent_wins(self, service):
        # urgent is checked before low via if/elif — HIGH should win
        priority, _ = await service.suggest_priority("urgent opcjonalne", None)
        assert priority == Priority.HIGH

    async def test_empty_string_description_same_as_none(self, service):
        # "" is falsy, so content and cache key must be identical to passing None
        result_none = await service.suggest_priority("Buy milk", None)
        module._PRIORITY_CACHE.clear()
        result_empty = await service.suggest_priority("Buy milk", "")
        assert result_none == result_empty

    async def test_substring_false_match_low_in_yellow(self, service):
        # "low" is a substring of "yellow" — documents current substring-match behaviour
        priority, _ = await service.suggest_priority("paint it yellow", None)
        assert priority == Priority.LOW

    async def test_exam_keyword_only_in_description(self, service):
        # exam keyword in description (not title) still triggers exam path
        priority, reason = await service.suggest_priority("Important task dzisiaj", "egzamin")
        assert priority == Priority.HIGH
        assert "egzaminu" in reason


# ---------------------------------------------------------------------------
# OpenAIPriorityService
# ---------------------------------------------------------------------------


class TestOpenAIPriorityService:
    @pytest.fixture
    def service(self):
        return OpenAIPriorityService(api_key="test-key")

    async def test_empty_api_key_returns_medium(self, mocker):
        # Without mock, a missing guard would still return MEDIUM via the exception handler.
        # Asserting OpenAI was never instantiated proves the guard short-circuits correctly.
        mock_openai = mocker.patch("openai.OpenAI")
        service = OpenAIPriorityService(api_key="")
        priority, reason = await service.suggest_priority("any task", None)
        assert priority == Priority.MEDIUM
        assert reason is None
        mock_openai.assert_not_called()

    async def test_empty_api_key_stores_in_cache(self):
        service = OpenAIPriorityService(api_key="")
        await service.suggest_priority("any task", None)
        key = module._build_cache_key("any task", None)
        assert key in module._PRIORITY_CACHE

    async def test_cache_hit_skips_api_call(self, mocker, service):
        key = module._build_cache_key("cached task", None)
        module._PRIORITY_CACHE[key] = (Priority.LOW, "from cache")

        mock_openai = mocker.patch("openai.OpenAI")
        result = await service.suggest_priority("cached task", None)

        mock_openai.assert_not_called()
        assert result == (Priority.LOW, "from cache")

    async def test_parses_high_priority_response(self, mocker, service):
        mock_create = mocker.patch("openai.OpenAI").return_value.chat.completions.create
        mock_create.return_value = make_openai_response(mocker, "PRIORITY: high\nREASON: Contains urgent deadline")

        priority, reason = await service.suggest_priority("Fix bug", None)

        assert priority == Priority.HIGH
        assert reason == "Contains urgent deadline"

    async def test_parses_low_priority_response(self, mocker, service):
        mock_create = mocker.patch("openai.OpenAI").return_value.chat.completions.create
        mock_create.return_value = make_openai_response(mocker, "PRIORITY: low\nREASON: Optional cleanup task")

        priority, reason = await service.suggest_priority("Cleanup", None)

        assert priority == Priority.LOW
        assert reason == "Optional cleanup task"

    async def test_parses_medium_priority_response(self, mocker, service):
        mock_create = mocker.patch("openai.OpenAI").return_value.chat.completions.create
        mock_create.return_value = make_openai_response(mocker, "PRIORITY: medium\nREASON: Routine task")

        priority, reason = await service.suggest_priority("Daily standup", None)

        assert priority == Priority.MEDIUM
        assert reason == "Routine task"

    async def test_unknown_priority_value_defaults_to_medium(self, mocker, service):
        mock_create = mocker.patch("openai.OpenAI").return_value.chat.completions.create
        mock_create.return_value = make_openai_response(mocker, "PRIORITY: unknown\nREASON: something")

        priority, _ = await service.suggest_priority("Some task", None)

        assert priority == Priority.MEDIUM

    async def test_empty_response_content_defaults_to_medium(self, mocker, service):
        mock_create = mocker.patch("openai.OpenAI").return_value.chat.completions.create
        mock_create.return_value = make_openai_response(mocker, "")

        priority, reason = await service.suggest_priority("Some task", None)

        assert priority == Priority.MEDIUM
        assert reason == "AI analysis completed"

    async def test_exception_returns_medium_none(self, mocker, service):
        mock_create = mocker.patch("openai.OpenAI").return_value.chat.completions.create
        mock_create.side_effect = RuntimeError("API down")

        priority, reason = await service.suggest_priority("Some task", None)

        assert priority == Priority.MEDIUM
        assert reason is None

    async def test_exception_result_stored_in_cache(self, mocker, service):
        mock_create = mocker.patch("openai.OpenAI").return_value.chat.completions.create
        mock_create.side_effect = RuntimeError("API down")

        await service.suggest_priority("Some task", None)

        key = module._build_cache_key("Some task", None)
        assert key in module._PRIORITY_CACHE

    async def test_description_included_in_api_content(self, mocker, service):
        mock_create = mocker.patch("openai.OpenAI").return_value.chat.completions.create
        mock_create.return_value = make_openai_response(mocker, "PRIORITY: medium\nREASON: ok")

        await service.suggest_priority("Task", "some description")

        user_message = mock_create.call_args[1]["messages"][1]["content"]
        assert "some description" in user_message

    async def test_client_lazy_initialized_on_first_call(self, mocker, service):
        assert service._client is None
        mock_create = mocker.patch("openai.OpenAI").return_value.chat.completions.create
        mock_create.return_value = make_openai_response(mocker, "PRIORITY: medium\nREASON: ok")

        await service.suggest_priority("Task", None)

        assert service._client is not None

    async def test_result_cached_after_successful_call(self, mocker, service):
        mock_create = mocker.patch("openai.OpenAI").return_value.chat.completions.create
        mock_create.return_value = make_openai_response(mocker, "PRIORITY: high\nREASON: urgent")

        await service.suggest_priority("Important task", None)

        key = module._build_cache_key("Important task", None)
        assert module._PRIORITY_CACHE[key] == (Priority.HIGH, "urgent")

    # --- edge cases ---

    async def test_none_response_content_treated_as_empty(self, mocker, service):
        # response.choices[0].message.content = None is handled by `or ""`
        mock_create = mocker.patch("openai.OpenAI").return_value.chat.completions.create
        response = mocker.MagicMock()
        response.choices[0].message.content = None
        mock_create.return_value = response

        priority, reason = await service.suggest_priority("Some task", None)

        assert priority == Priority.MEDIUM
        assert reason == "AI analysis completed"

    async def test_priority_line_with_no_value_defaults_to_medium(self, mocker, service):
        # "PRIORITY: " (blank after colon) — not in valid list → stays MEDIUM
        mock_create = mocker.patch("openai.OpenAI").return_value.chat.completions.create
        mock_create.return_value = make_openai_response(mocker, "PRIORITY: \nREASON: something")

        priority, _ = await service.suggest_priority("Some task", None)

        assert priority == Priority.MEDIUM

    async def test_reason_with_colon_preserved(self, mocker, service):
        # split(":", 1) ensures only the first colon is consumed
        mock_create = mocker.patch("openai.OpenAI").return_value.chat.completions.create
        mock_create.return_value = make_openai_response(
            mocker, "PRIORITY: high\nREASON: fix: the production: issue"
        )

        _, reason = await service.suggest_priority("Some task", None)

        assert reason == "fix: the production: issue"

    async def test_response_with_no_priority_or_reason_lines(self, mocker, service):
        # Malformed response with no expected lines → defaults kick in
        mock_create = mocker.patch("openai.OpenAI").return_value.chat.completions.create
        mock_create.return_value = make_openai_response(mocker, "Sorry, I cannot help with that.")

        priority, reason = await service.suggest_priority("Some task", None)

        assert priority == Priority.MEDIUM
        assert reason == "AI analysis completed"

    async def test_client_reused_on_second_call(self, mocker, service):
        # OpenAI constructor must be called exactly once across two separate calls
        mock_cls = mocker.patch("openai.OpenAI")
        mock_cls.return_value.chat.completions.create.return_value = make_openai_response(
            mocker, "PRIORITY: medium\nREASON: ok"
        )

        await service.suggest_priority("First task", None)
        await service.suggest_priority("Second task", None)

        mock_cls.assert_called_once()
