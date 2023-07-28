import unittest

import uncurl


class TestCurlToRequests(unittest.TestCase):

    def test_parse(self):
        file_content = open('curl.txt', 'r').read()
        parsed = uncurl.parse(file_content)
        print(parsed)