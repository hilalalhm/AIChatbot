from app.services.context_service import ContextManager


def _msg(role, content):
    return type("M", (), {"role": role, "content": content})()


def test_build_context_keeps_current_message():
    cm = ContextManager(max_tokens=4000, recent_limit=10)
    recent = [
        _msg("user", "Saya sedang membuat aplikasi Telegram AI."),
        _msg("assistant", "Gunakan FastAPI sebagai backend."),
        _msg("user", "Bagaimana dengan database?"),
        _msg("assistant", "Gunakan PostgreSQL."),
    ]
    snap = cm.build_context(recent, "Sekarang buat struktur databasenya.",
                            summary="User is building a Telegram AI app.")
    assert snap.current_message == "Sekarang buat struktur databasenya."
    assert snap.summary == "User is building a Telegram AI app."
    assert len(snap.recent_messages) == 4


def test_build_context_respects_token_budget():
    cm = ContextManager(max_tokens=200, recent_limit=100)
    big_content = "x" * 1000
    recent = [_msg("user", big_content), _msg("assistant", big_content)]
    snap = cm.build_context(recent, "short", summary="")
    # Current message must always be present
    assert snap.current_message == "short"
    # Recent messages should be trimmed to fit budget
    total = sum(len(m.content) for m in snap.recent_messages)
    assert total <= 200


def test_context_snapshot_to_provider_messages():
    cm = ContextManager(max_tokens=4000)
    recent = [_msg("user", "hello")]
    snap = cm.build_context(recent, "question", summary="sum", memory="mem")
    messages = snap.to_provider_messages()
    assert messages[-1] == {"role": "user", "content": "question"}
    # Summary and memory included as system messages
    contents = " ".join(m["content"] for m in messages)
    assert "sum" in contents
    assert "mem" in contents
