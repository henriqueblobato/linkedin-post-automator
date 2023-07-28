import unittest
from unittest.mock import Mock, patch

from main import post_linkedin


class TestPostLinkedIn(unittest.TestCase):
    def setUp(self):
        self.payload_text = "Test payload text"
        self.cookies_conf = {
            "li_at": "your_li_at_value",
            "JSESSIONID": "your_jsessionid_value"
        }

    @patch('main.get_session')
    def test_post_linkedin_success(self, mock_get_session):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"someKey": "expectedValue"}

        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_get_session.return_value = mock_session

        post_linkedin(self.payload_text, self.cookies_conf)

        expected_cookie_value = "li_at=your_li_at_value; JSESSIONID=\"your_jsessionid_value\""
        expected_headers = {
            "accept": "application/vnd.linkedin.normalized+json+2.1",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/json; charset=UTF-8",
            "csrf-token": "your_jsessionid_value",
            "referrer-policy": "strict-origin-when-cross-origin, strict-origin-when-cross-origin",
            "origin": "https://www.linkedin.com",
            "Referrer": "https://www.linkedin.com/feed/",
            "Referrer-Policy": "strict-origin-when-cross-origin, strict-origin-when-cross-origin",
            "cookie": expected_cookie_value
        }
        mock_session.post.assert_called_once_with(
            "https://www.linkedin.com/voyager/api/contentcreation/normShares",
            headers=expected_headers,
            data={
                "visibleToConnectionsOnly": False,
                "externalAudienceProviders": [],
                "commentaryV2": {
                    "text": self.payload_text,
                    "attributes": []
                },
                "origin": "FEED",
                "allowedCommentersScope": "ALL",
                "postState": "PUBLISHED",
                "media": []
            }
        )

    @patch('main.get_session')
    def test_post_linkedin_failure(self, mock_get_session):
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("Mocked error")

        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_get_session.return_value = mock_session

        with self.assertRaises(Exception):
            post_linkedin(self.payload_text, self.cookies_conf)


if __name__ == "__main__":
    unittest.main()
