from app.telegram.bot import TelegramBot
from app.telegram.chunker import split_message


def test_parse_update_extracts_message():
    bot = TelegramBot(token="fake:token")
    update = {
        "update_id": 1,
        "message": {
            "message_id": 10,
            "from": {"id": 555, "username": "bob", "first_name": "Bob"},
            "chat": {"id": 555},
            "text": "/start",
        },
    }
    parsed = bot.parse_update(update)
    assert parsed is not None
    assert parsed["chat_id"] == 555
    assert parsed["telegram_id"] == 555
    assert parsed["text"] == "/start"


def test_parse_update_ignores_non_text():
    bot = TelegramBot(token="fake:token")
    update = {"update_id": 1, "message": {"from": {"id": 1}, "chat": {"id": 1}}}
    assert bot.parse_update(update) is None


def test_split_message_short():
    chunks = split_message("hello world", 4096)
    assert chunks == ["hello world"]


def test_split_message_long():
    text = " ".join(["word"] * 5000)  # > 4096 chars
    chunks = split_message(text, 4096)
    assert len(chunks) > 1
    # Every chunk <= max_len
    assert all(len(c) <= 4096 for c in chunks)
    # Reconstructed content preserved
    assert "".join(chunks).replace(" ", " ") == text


def test_split_prefers_paragraph_boundary():
    text = ("Para1 " + "a" * 3000 + "\n\n" + "Para2 " + "b" * 3000)
    chunks = split_message(text, 4096)
    assert len(chunks) == 2
    assert len(chunks[0]) <= 4096
    assert "".join(chunks) == text
