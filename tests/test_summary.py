from app.context.summarizer import Summarizer
from app.context.memory import estimate_tokens


def test_should_summarize():
    s = Summarizer()
    short = "short text"
    long_text = "x" * 40000  # ~10000 tokens
    assert s.should_summarize(short, trigger_tokens=8000) is False
    assert s.should_summarize(long_text, trigger_tokens=8000) is True


def test_estimate_tokens():
    assert estimate_tokens("") == 0
    assert estimate_tokens("word") == 1
    assert estimate_tokens("x" * 100) == 25


def test_summarizer_without_fn_bounds_transcript():
    s = Summarizer(max_chars=50)
    result = s.summarize("a" * 1000)
    assert len(result) <= 50


def test_summarizer_with_fn():
    def fake_summarize(text):
        return "SUMMARY_RESULT"

    s = Summarizer(summarize_fn=fake_summarize)
    assert s.summarize("whatever") == "SUMMARY_RESULT"
