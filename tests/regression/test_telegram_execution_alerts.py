from unittest.mock import patch
from quant_ecosystem.notifications.telegram_notifier import TelegramNotifier


def test_telegram_send_success():
    notifier = TelegramNotifier()
    notifier.bot_token = "dummy"
    notifier.chat_id = "dummy"

    with patch("requests.post") as post:
        post.return_value.status_code = 200
        assert notifier.send("hello") is True


def test_telegram_disabled():
    notifier = TelegramNotifier()
    notifier.bot_token = ""
    notifier.chat_id = ""

    assert notifier.send("hello") is False