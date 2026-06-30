import sys
import os
import unittest
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../run')))

import tesla_api

class TestTeslaApi(unittest.TestCase):
    def setUp(self):
        # Save original value to restore later
        self.original_vehicle_id = tesla_api.tesla_api_json.get('vehicle_id')
        self.original_id = tesla_api.tesla_api_json.get('id')
        tesla_api.tesla_api_json['vehicle_id'] = 123
        tesla_api.tesla_api_json['id'] = 987

    def tearDown(self):
        # Restore original value
        tesla_api.tesla_api_json['vehicle_id'] = self.original_vehicle_id
        tesla_api.tesla_api_json['id'] = self.original_id

    @patch('tesla_api.list_vehicles')
    def test_get_vehicle_online_state_vehicle_found(self, mock_list_vehicles):
        mock_list_vehicles.return_value = {
            'response': [
                {'vehicle_id': 999, 'state': 'offline'},
                {'vehicle_id': 123, 'state': 'online'},
                {'vehicle_id': 456, 'state': 'asleep'}
            ]
        }
        self.assertEqual(tesla_api.get_vehicle_online_state(), 'online')

    @patch('tesla_api._error')
    @patch('sys.exit')
    @patch('tesla_api.list_vehicles')
    def test_get_vehicle_online_state_empty_list(self, mock_list_vehicles, mock_sys_exit, mock_error):
        mock_list_vehicles.return_value = {
            'response': []
        }

        # When sys.exit is called, we don't want to actually exit. We can simulate it
        # by raising an exception, or just letting the mock record the call.
        # However, if we just let the mock record it, the function will continue and implicitly return None.
        # But `sys.exit` stops execution, so to properly test we should make the mock raise SystemExit.
        mock_sys_exit.side_effect = SystemExit(1)

        with self.assertRaises(SystemExit) as cm:
            tesla_api.get_vehicle_online_state()

        self.assertEqual(cm.exception.code, 1)
        mock_error.assert_called_once_with("Could not find vehicle")
        mock_sys_exit.assert_called_once_with(1)

    @patch('tesla_api._error')
    @patch('sys.exit')
    @patch('tesla_api.list_vehicles')
    def test_get_vehicle_online_state_vehicle_not_found(self, mock_list_vehicles, mock_sys_exit, mock_error):
        mock_list_vehicles.return_value = {
            'response': [
                {'vehicle_id': 999, 'state': 'offline'},
                {'vehicle_id': 456, 'state': 'asleep'}
            ]
        }

        mock_sys_exit.side_effect = SystemExit(1)

        with self.assertRaises(SystemExit) as cm:
            tesla_api.get_vehicle_online_state()

        self.assertEqual(cm.exception.code, 1)
        mock_error.assert_called_once_with("Could not find vehicle")
        mock_sys_exit.assert_called_once_with(1)

    @patch('tesla_api._execute_request')
    def test_set_charge_limit(self, mock_execute_request):
        mock_execute_request.return_value = {'response': {'result': True, 'reason': ''}}

        result = tesla_api.set_charge_limit(80)

        mock_execute_request.assert_called_once_with(
            '{}/{}/command/set_charge_limit'.format(tesla_api.base_url, 987),
            method='POST',
            data={'percent': 80}
        )
        self.assertEqual(result, {'response': {'result': True, 'reason': ''}})

if __name__ == '__main__':
    unittest.main()
