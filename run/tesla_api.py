#!/usr/bin/python3
import argparse
import base64
import json
import os
import random
import requests
import teslapy
import time
import sys
from datetime import datetime
# Only used for debugging.

class TeslaAPI:
    def __init__(self):
        self.list_url = 'https://owner-api.teslamotors.com/api/1/products'
        self.base_url = 'https://owner-api.teslamotors.com/api/1/vehicles'
        self.SETTINGS = {
            'DEBUG': False,
            'refresh_token': False,
            'tesla_email': 'dummy@local',
            'tesla_password': '',
            'tesla_access_token': '',
            'tesla_vin': '',
        }
        self.date_format = '%Y-%m-%d %H:%M:%S'
        self.tesla_api_json = {
            'access_token': '',
            'refresh_token': '',
            'id': 0,
            'vehicle_id': 0,
        }
        self.mutable_dir = '/mutable'

    def _invalidate_access_token(self):
        if not self.tesla_api_json.get('refresh_token') or self.tesla_api_json['refresh_token'] == '':
            self.tesla_api_json['refresh_token'] = self.SETTINGS['refresh_token']
        self.tesla_api_json['access_token'] = None
        self._write_tesla_api_json()


    def _execute_request(self, url=None, method=None, data=None, require_vehicle_online=True):
        """
        Wrapper around requests to the Tesla REST Service which ensures the vehicle is online before proceeding
        :param url: the url to send the request to
        :param method: the request method ('GET' or 'POST')
        :param data: the request data (optional)
        :return: JSON response
        """
        if require_vehicle_online:
            vehicle_online = False
            auth_retries = 0
            while not vehicle_online:
                self._log("Attempting to wake up Vehicle (ID:{})".format(self.tesla_api_json['id']))
                result = self._rest_request(
                    '{}/{}/wake_up'.format(self.base_url, self.tesla_api_json['id']),
                    method='POST'
                )

                # Tesla REST Service sometimes misbehaves... this seems to be caused by an invalid/expired auth token
                if result.get('response') is None:
                    if auth_retries < 3:
                        self._error(f"Error: Tesla REST Service returned an invalid response, invalidating token and retrying: {result}")
                        self._invalidate_access_token()
                        auth_retries += 1
                        continue
                    self._error(f"Fatal Error: Tesla REST Service returned an invalid response: {result}")
                    sys.exit(1)

                vehicle_online = result['response']['state'] == "online"
                if vehicle_online:
                    self._log("Vehicle (ID:{}) is Online".format(self.tesla_api_json['id']))
                else:
                    self._log("Vehicle (ID:{}) is Asleep; Waiting 5 seconds before retry...".format(self.tesla_api_json['id']))
                    time.sleep(5)

        if url is None:
            return result['response']['state']

        json_response = self._rest_request(url, method, data)

        # Error handling
        error = json_response.get('error')
        if error:
            # Log error and die
            self._error(json.dumps(json_response, indent=2))
            sys.exit(1)

        return json_response


    def _rest_request(self, url, method=None, data=None):
        """
        Executes a REST request
        :param url: the url to send the request to
        :param method: the request method ('GET' or 'POST')
        :param data: the request data (optional)
        :return: JSON response
        """
        # set default method value
        if method is None:
            method = 'GET'
        # set default data value
        if data is None:
            data = {}
        headers = {
          'Authorization': 'Bearer {}'.format(self._get_api_token()),
          'User-Agent': 'github.com/marcone/teslausb',
        }

        self._log("Sending {} Request: {}; Data: {}".format(method, url, data))
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers)
        elif method.upper() == 'POST':
            response = requests.post(url, headers=headers, data=data)
        else:
            raise ValueError('Unsupported Request Method: {}'.format(method))
        if not response.text:
            self._error("Fatal Error: Tesla REST Service failed to return a response, access token may have expired")
            sys.exit(1)
        if  'invalid bearer token' in response.text:
            self._error("Invalid Access token, removing from cache...")
            self._invalidate_access_token()
        json_response = response.json()

        # log full JSON response for debugging
        self._log(json.dumps(json_response, indent=2))

        return json_response


    def _get_api_token(self):
        """
        Retrieves the API access token, either from /mutable/tesla_api.json,
        self.SETTINGS, or from the Tesla API by using the credentials in self.SETTINGS.
        If those are also not available, kill the script, since it can't continue.
        """
        os.chdir(self.mutable_dir)
        # If the token was already saved, work with that.
        if self.tesla_api_json['access_token']:
            # Due to what appears to be a bug with the fake-hwclock service,
            # sometimes the system thinks it's still November 2016. If that's the
            # case, we can't accurately determine the age of the token, so we just
            # use it. Later executions of the script should run after the date has
            # updated correctly, at which point we can properly compare the dates.
            now = datetime.now()
            if now.year < 2019: # This script was written in 2019.
                return self.tesla_api_json['access_token']

            if not self.SETTINGS.get('refresh_token'):
                self._log('No refreshing token available. Using existing access token.')
                return self.tesla_api_json['access_token']

            tesla = teslapy.Tesla(self.SETTINGS['tesla_email'], None)
            # For some reason, the `expires_at` timestamp doesn't exactly match the `exp` field in the JWT body.
            # The `expires_at` is typically about 1 minute ahead of the `exp` value in the JWT payload.
            # Access token usually expires after a few hours, so refresh the token if it has less than `expiration_buffer_s` seconds remaining.
            expiration_buffer_s = 60 * 30
            if tesla.expires_at <= time.time() - expiration_buffer_s:
                self._log("Refreshing expired access token...")
                tesla.token['refresh_token'] = self.SETTINGS.get('refresh_token')
                tesla.refresh_token()

            if self.tesla_api_json['access_token'] != tesla.token.get('access_token'):
                self._log("Syncing access token...")
                self.tesla_api_json['access_token'] = tesla.token.get('access_token')
                self._write_tesla_api_json()
            return self.tesla_api_json['access_token']

        # If the access token is not already stored in self.tesla_api_json AND
        # the user provided a refresh_token force it into the client to get a proper token
        elif self.tesla_api_json['refresh_token']:
            tesla = teslapy.Tesla(self.SETTINGS['tesla_email'], None)
            self._log('Force setting a refresh token')
            tesla.access_token = "DUMMY"
            tesla.token['refresh_token'] = self.tesla_api_json['refresh_token']
            tesla.refresh_token()
            self.tesla_api_json['access_token'] = tesla.token.get('access_token')
            # if the refresh token is changed we store the new one, never saw it happen but...
            self.tesla_api_json['refresh_token'] = tesla.token['refresh_token']
            self._write_tesla_api_json()
            return self.tesla_api_json['access_token']

        self._error('Unable to perform Tesla API functions: no credentials or token.')
        sys.exit(1)


    def _get_id(self):
        """
        Put the vehicle's ID into self.tesla_api_json['id'].
        """
        # If it was already set by self._load_tesla_api_json(), and a new
        # VIN or name wasn't specified on the command line, we're done.
        if self.tesla_api_json['id'] and self.tesla_api_json['vehicle_id']:
          if self.SETTINGS['tesla_name'] == '' and self.SETTINGS['tesla_vin'] == '':
            return

        # Call self.list_vehicles() and use the provided name or VIN to get the vehicle ID.
        result = self.list_vehicles()
        for vehicle_dict in result['response']:
            if ( ( self.SETTINGS['tesla_vin'] != '' and vehicle_dict['vin'] == self.SETTINGS['tesla_vin'] )
              or ( self.SETTINGS['tesla_name'] != '' and vehicle_dict['display_name'] == self.SETTINGS['tesla_name'] )
              or ( self.SETTINGS['tesla_vin'] == '' and self.SETTINGS['tesla_name'] == '')):
                self.tesla_api_json['id'] = vehicle_dict['id_s']
                self.tesla_api_json['vehicle_id'] = vehicle_dict['vehicle_id']
                self._log('Retrieved Vehicle ID from Tesla API.')
                self._write_tesla_api_json()
                return

        self._error('Unable to retrieve vehicle ID: Unknown name or VIN. Cannot continue.')
        sys.exit(1)


    def _load_tesla_api_json(self):
        """
        Load the data stored in /mutable/tesla_api.json, if it exists.
        If it doesn't exist, write a file to that location with default values.
        """
        try:
            with open(self.mutable_dir + '/tesla_api.json', 'r') as f:
                self._log('Loading mutable data from disk...')
                json_string = f.read()
        except FileNotFoundError:
            # Write a dict with the default data to the file.
            self._log("Mutable data didn't exist, writing defaults...")
            self._write_tesla_api_json()
        else:
            def datetime_parser(dct):
                # Converts any string with the appropriate format in the parsed JSON
                # dict into a datetime object.
                for k, v in dct.items():
                    try:
                        dct[k] = datetime.strptime(v, self.date_format)
                    except (TypeError, ValueError):
                        pass
                return dct

            # Need to declare this as a global since we assign to it directly.

            self.tesla_api_json = json.loads(json_string, object_hook=datetime_parser)


    def _write_tesla_api_json(self):
        """
        Write the contents of the self.tesla_api_json dict to /mutable/tesla_api.json.
        """
        def convert_dt(obj):
            # Converts datetime objects into 'YYYY-MM-DD HH:MM:SS' strings, since
            # json.dumps() can't serialize them itself.
            if isinstance(obj, datetime):
                return obj.strftime(self.date_format)

        with open(self.mutable_dir + '/tesla_api.json', 'w') as f:
            self._log('Writing ' + self.mutable_dir + '/tesla_api.json...')
            json_string = json.dumps(self.tesla_api_json, indent=2, default=convert_dt)
            f.write(json_string)


    def _get_log_timestamp(self):
        # I can't figure out how to get a timezone aware version of now() in
        # Python 2.7 without pytz, so I kludged this together. It outputs the
        # same timestamp format as the other logging done by TeslaUSB's code.
        zone = time.tzname[time.daylight]
        return datetime.now().strftime('%a %d %b %H:%M:%S {} %Y'.format(zone))


    def _log(self, msg, flush=True):
        if self.SETTINGS['DEBUG']:
            print("{}: {}".format(self._get_log_timestamp(), msg), flush=flush)


    def _error(self, msg, flush=True):
        """
        It's self._log(), but for errors, so it always prints.
        """
        print("{}: {}".format(self._get_log_timestamp(), msg), file=sys.stderr, flush=flush)


    ######################################
    # API GET Functions
    ######################################

    def list_vehicles(self):
        return self._execute_request(self.list_url, None, None, False)


    def get_service_data(self):
        return self._execute_request(
            '{}/{}/service_data'.format(self.base_url, self.tesla_api_json['id'])
        )


    def get_vehicle_summary(self):
        return self._execute_request(
            '{}/{}'.format(self.base_url, self.tesla_api_json['id'])
        )


    def get_vehicle_legacy_data(self):
        return self._execute_request(
            '{}/{}/data'.format(self.base_url, self.tesla_api_json['id'])
        )


    def get_nearby_charging(self):
        return self._execute_request(
            '{}/{}//nearby_charging_sites'.format(self.base_url, self.tesla_api_json['id'])
        )


    def get_vehicle_data(self):
        return self._execute_request(
            '{}/{}/vehicle_data'.format(self.base_url, self.tesla_api_json['id'])
        )


    def get_vehicle_online_state(self):
        # list_vehicles gets the state of each vehicle without waking them up
        result = self.list_vehicles()
        vehicle = next(
            (v for v in result['response'] if v['vehicle_id'] == self.tesla_api_json['vehicle_id']),
            None
        )
        if vehicle is not None:
            return vehicle['state']
        self._error("Could not find vehicle")
        sys.exit(1)


    def is_vehicle_online(self):
        return self.get_vehicle_online_state() == "online"


    def get_charge_state(self):
        return self._execute_request(
            '{}/{}/data_request/charge_state'.format(self.base_url, self.tesla_api_json['id'])
        )


    def get_climate_state(self):
        return self._execute_request(
            '{}/{}/data_request/climate_state'.format(self.base_url, self.tesla_api_json['id'])
        )


    def get_drive_state(self):
        return self._execute_request(
            '{}/{}/data_request/drive_state'.format(self.base_url, self.tesla_api_json['id'])
        )


    def get_gui_settings(self):
        return self._execute_request(
            '{}/{}/data_request/gui_settings'.format(self.base_url, self.tesla_api_json['id'])
        )


    def get_vehicle_state(self):
        return self._execute_request(
            '{}/{}/data_request/vehicle_state'.format(self.base_url, self.tesla_api_json['id'])
        )


    ######################################
    # Custom Functions
    ######################################

    def get_odometer(self):
        data = self.get_vehicle_state()
        return int(data['response']['odometer'])


    def is_car_locked(self):
        data = self.get_vehicle_state()
        return data['response']['locked']


    def is_sentry_mode_enabled(self):
        data = self.get_vehicle_state()
        return data['response']['sentry_mode']


    '''
    This accesses the streaming endpoint, but doesn't
    stick around to wait for continuous results.
    '''

    def streaming_ping(self):
        # the car needs to be awake for the streaming endpoint to work
        self.wake_up_vehicle()

        headers = {
          'User-Agent': 'github.com/marcone/teslausb',
          'Authorization': 'Bearer {}'.format(self._get_api_token()),
          'Connection': 'Upgrade',
          'Upgrade': 'websocket',
          'Sec-WebSocket-Key': base64.b64encode(bytes([random.randrange(0, 256) for _ in range(0, 16)])).decode('utf-8'),
          'Sec-WebSocket-Version': '13',
        }

        url = 'https://streaming.vn.teslamotors.com/connect/{}'.format(self.tesla_api_json['vehicle_id'])

        self._log("Sending streaming request")
        response = requests.get(url, headers=headers, stream=True)
        if not response:
            self._error("Fatal Error: Tesla REST Service failed to return a response, access token may have expired")
            sys.exit(1)

        return response


    ######################################
    # API POST Functions
    ######################################

    def wake_up_vehicle(self):
        self._log('Sending wakeup API command...')
        return self._execute_request()


    def set_charge_limit(self, percent):
        return self._execute_request(
            '{}/{}/command/set_charge_limit'.format(self.base_url, self.tesla_api_json['id']),
            method='POST',
            data={'percent': percent}
        )


    def actuate_trunk(self):
        result = self._execute_request(
            '{}/{}/command/actuate_trunk'.format(self.base_url, self.tesla_api_json['id']),
            method='POST',
            data={'which_trunk': 'rear'}
        )
        return result['response']['result']


    def actuate_frunk(self):
        result = self._execute_request(
            '{}/{}/command/actuate_trunk'.format(self.base_url, self.tesla_api_json['id']),
            method='POST',
            data={'which_trunk': 'front'}
        )
        return result['response']['result']


    def flash_lights(self):
        result = self._execute_request(
            '{}/{}/command/flash_lights'.format(self.base_url, self.tesla_api_json['id']),
            method='POST'
        )
        return result['response']['result']


    def set_sentry_mode(self, enabled: bool):
        """
        Activates or deactivates Sentry Mode based on the 'enabled' parameter
        :param enabled: True to Enable Sentry Mode; False to Disable Sentry Mode
        :return: True if the command was successful
        """
        self._log("Setting Sentry Mode Enabled: {}".format(enabled))
        result = self._execute_request(
            '{}/{}/command/set_sentry_mode'.format(self.base_url, self.tesla_api_json['id']),
            method='POST',
            data={'on': enabled}
        )
        return result['response']['result']


    def enable_sentry_mode(self):
        """
        Enables Sentry Mode
        :return: Human-friendly String indicating command success/failure
        """
        if self.set_sentry_mode(True):
            return "Success: Sentry Mode Enabled"
        else:
            return "Failed to Enable Sentry Mode"


    def disable_sentry_mode(self):
        """
        Disables Sentry Mode
        :return: Human-friendly String indicating command success/failure
        """
        if self.set_sentry_mode(False):
            return "Success: Sentry Mode Disabled"
        else:
            return "Failed to Disable Sentry Mode"


    def toggle_sentry_mode(self):
        """
        Activates Sentry Mode if it is currently off, disables it if it is currently on
        :return: True if the command was successful
        """
        if self.is_sentry_mode_enabled():
            return self.disable_sentry_mode()
        else:
            return self.enable_sentry_mode()


    ######################################
    # Utility Functions
    ######################################


def _get_api_functions():
    function_names = []
    for name in dir(TeslaAPI):
        if callable(getattr(TeslaAPI, name)) and not name.startswith('_'):
            function_names.append(name)
    function_names.sort()
    return '\n'.join(function_names)


def _get_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'function',
        help="The name of the function to run. Available functions are:\n {}".format(_get_api_functions()))
    parser.add_argument(
        '--arguments',
        help="Add arguments to the function by passing comma-separated key:value pairs."
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print debug output."
    )
    parser.add_argument(
        "--refresh_token",
        help="Tesla refresh_token to authenticate."
    )
    parser.add_argument(
        "--vin",
        help="VIN number of the car."
    )
    parser.add_argument(
        "--name",
        help="name of the car."
    )

    return parser


def main():
    args = _get_arg_parser().parse_args()

    api = TeslaAPI()

    api.SETTINGS['DEBUG'] = args.debug
    api.SETTINGS['refresh_token'] = args.refresh_token

    if args.vin:
        api.SETTINGS['tesla_vin'] = args.vin
    else:
        api.SETTINGS['tesla_vin'] = os.environ.get('TESLA_VIN', '')

    if args.refresh_token:
        api.SETTINGS['refresh_token'] = args.refresh_token
    else:
        api.SETTINGS['refresh_token'] = os.environ.get('TESLA_REFRESH_TOKEN', '')

    if args.name:
        api.SETTINGS['tesla_name'] = args.name
    else:
        api.SETTINGS['tesla_name'] = os.environ.get('TESLA_NAME', '')

    api._load_tesla_api_json()

    if not api.tesla_api_json.get('refresh_token') or api.tesla_api_json['refresh_token'] == '':
        api.tesla_api_json['refresh_token'] = api.SETTINGS['refresh_token']
        api._write_tesla_api_json()

    kwargs = {}
    if args.arguments:
        for kwarg_string in [arg.strip() for arg in args.arguments.split(',')]:
            key, value = kwarg_string.split(':')
            kwargs[key] = value
    kwargs_string = ''
    if kwargs:
        kwargs_string = ', '.join(
            '{}={}'.format(key, value) for key, value in kwargs.items()
        )

    api._get_id()

    function = getattr(api, args.function)
    api._log('Calling {}({})...'.format(args.function, kwargs_string))
    result = function(**kwargs)

    is_json = False
    try:
        if isinstance(result, str):
            json.loads(result)
            is_json = True
    except ValueError:
        pass

    if is_json:
        api._log(json.dumps(result, indent=2))
    else:
        print(result, flush=True)


if __name__ == '__main__':
    main()
