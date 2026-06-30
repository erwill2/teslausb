import sys
import os
import unittest
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../run')))

import tesla_api

class TestTeslaApi(unittest.TestCase):
    def setUp(self):
        self.api = tesla_api.TeslaAPI()
        # Save original value to restore later
        self.original_vehicle_id = self.api.tesla_api_json.get('vehicle_id')
        self.api.tesla_api_json['vehicle_id'] = 123

    def tearDown(self):
        # Restore original value
        self.api.tesla_api_json['vehicle_id'] = self.original_vehicle_id

    def test_get_vehicle_online_state_vehicle_found(self):
        with patch.object(self.api, 'list_vehicles') as mock_list_vehicles:
            mock_list_vehicles.return_value = {
                'response': [
                    {'vehicle_id': 999, 'state': 'offline'},
                    {'vehicle_id': 123, 'state': 'online'},
                    {'vehicle_id': 456, 'state': 'asleep'}
                ]
            }
            self.assertEqual(self.api.get_vehicle_online_state(), 'online')

    def test_get_vehicle_online_state_empty_list(self):
        with patch.object(self.api, 'list_vehicles') as mock_list_vehicles, \
             patch('sys.exit') as mock_sys_exit, \
             patch.object(self.api, '_error') as mock_error:

            mock_list_vehicles.return_value = {
                'response': []
            }

            # When sys.exit is called, we don't want to actually exit. We can simulate it
            # by raising an exception, or just letting the mock record the call.
            # However, if we just let the mock record it, the function will continue and implicitly return None.
            # But `sys.exit` stops execution, so to properly test we should make the mock raise SystemExit.
            mock_sys_exit.side_effect = SystemExit(1)

            with self.assertRaises(SystemExit) as cm:
                self.api.get_vehicle_online_state()

            self.assertEqual(cm.exception.code, 1)
            mock_error.assert_called_once_with("Could not find vehicle")
            mock_sys_exit.assert_called_once_with(1)

    def test_get_vehicle_online_state_vehicle_not_found(self):
        with patch.object(self.api, 'list_vehicles') as mock_list_vehicles, \
             patch('sys.exit') as mock_sys_exit, \
             patch.object(self.api, '_error') as mock_error:

            mock_list_vehicles.return_value = {
                'response': [
                    {'vehicle_id': 999, 'state': 'offline'},
                    {'vehicle_id': 456, 'state': 'asleep'}
                ]
            }

            mock_sys_exit.side_effect = SystemExit(1)

            with self.assertRaises(SystemExit) as cm:
                self.api.get_vehicle_online_state()

            self.assertEqual(cm.exception.code, 1)
            mock_error.assert_called_once_with("Could not find vehicle")
            mock_sys_exit.assert_called_once_with(1)

if __name__ == '__main__':
    unittest.main()
