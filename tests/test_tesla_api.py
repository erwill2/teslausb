import unittest
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../run')))

import tesla_api

class TestTeslaApi(unittest.TestCase):

    @patch('tesla_api._execute_request')
    def test_list_vehicles(self, mock_execute_request):
        expected_response = {'response': [{'id': 12345, 'vin': 'TESTVIN123'}]}
        mock_execute_request.return_value = expected_response

        response = tesla_api.list_vehicles()

        mock_execute_request.assert_called_once_with(tesla_api.list_url, None, None, False)
        self.assertEqual(response, expected_response)

if __name__ == '__main__':
    unittest.main()
