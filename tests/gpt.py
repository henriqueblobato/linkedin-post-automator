import unittest
from unittest.mock import Mock, patch
import openai
from main import ask_chatgpt


class TestAskChatGPT(unittest.TestCase):
    @patch('main.openai.ChatCompletion.create')
    def test_ask_chatgpt_success(self, mock_chat_completion_create):
        config = {
            "gpt_preamble": "Welcome to ChatGPT!",
            "bio": "I am an AI language model."
        }

        content = ["Tell me a joke.", "What's the weather like today?"]

        response = {
            "choices": [
                {
                    "message": {
                        "content": "The joke is: Knock, knock!"
                    }
                }
            ],
            "usage": {
                "completion": 1,
                "model": 1,
                "prompt": 1,
            }
        }

        mock_chat_completion_create.return_value = Mock(**response)
        message_mock = Mock()
        message_mock.__getitem__ = Mock(return_value="The joke is: Knock, knock!")
        mock_chat_completion_create.return_value.choices = [message_mock]
        mock_chat_completion_create.__getitem__ = Mock
        expected_result = "The joke is: Knock, knock!"

        result = ask_chatgpt(config, content)

        self.assertEqual(result, expected_result)

        # Check the usage in the response
        self.assertEqual(response["usage"]["completion"], 1)
        self.assertEqual(response["usage"]["model"], 1)
        self.assertEqual(response["usage"]["prompt"], 1)

    @patch('main.openai.ChatCompletion.create')
    def test_ask_chatgpt_rate_limit(self, mock_chat_completion_create):
        config = {
            "gpt_preamble": "Welcome to ChatGPT!",
            "bio": "I am an AI language model."
        }

        content = ["Tell me a joke.", "What's the weather like today?"]

        mock_chat_completion_create.side_effect = openai.error.RateLimitError("Rate limit exceeded.")

        with patch('time.sleep') as mock_sleep:
            mock_sleep.side_effect = None

            result = ask_chatgpt(config, content)

            self.assertEqual(mock_sleep.call_count, 1)
            self.assertIn("Rate limit exceeded. Retrying in 1 seconds...", mock_sleep.call_args[0][0])
            self.assertEqual(result, "")

    @patch('main.openai.ChatCompletion.create')
    def test_ask_chatgpt_service_unavailable(self, mock_chat_completion_create):
        config = {
            "gpt_preamble": "Welcome to ChatGPT!",
            "bio": "I am an AI language model."
        }

        content = ["Tell me a joke.", "What's the weather like today?"]

        mock_chat_completion_create.side_effect = openai.error.ServiceUnavailableError("Server is overloaded.")

        with patch('time.sleep') as mock_sleep:
            mock_sleep.side_effect = None

            result = ask_chatgpt(config, content)

            self.assertEqual(mock_sleep.call_count, 1)
            self.assertIn("The server is overloaded or not ready yet.  Retrying in 1 seconds...", mock_sleep.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
