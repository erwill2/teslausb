import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'run')))
import send_sns

class TestSendSns(unittest.TestCase):
    @patch('send_sns.boto3.client')
    def test_send_sns_success(self, mock_boto3_client):
        # Setup mock
        mock_sns = MagicMock()
        mock_boto3_client.return_value = mock_sns
        mock_sns.publish.return_value = {'MessageId': '12345'}

        # Call function
        topic = 'arn:aws:sns:us-east-1:123456789012:MyTopic'
        subject = 'Test Subject'
        message = 'Test Message'

        response = send_sns.send_sns(topic, subject, message)

        # Verify
        mock_boto3_client.assert_called_once_with('sns')
        mock_sns.publish.assert_called_once_with(
            TopicArn=topic,
            Message=message,
            Subject=subject
        )
        self.assertEqual(response, {'MessageId': '12345'})

    @patch('send_sns.boto3.client')
    def test_send_sns_boto_error(self, mock_boto3_client):
        # Setup mock to raise exception
        mock_sns = MagicMock()
        mock_boto3_client.return_value = mock_sns
        mock_sns.publish.side_effect = Exception("AWS Error")

        # Call function and verify it propagates exception
        with self.assertRaises(Exception) as context:
            send_sns.send_sns('topic', 'subject', 'message')

        self.assertTrue('AWS Error' in str(context.exception))
        mock_sns.publish.assert_called_once_with(
            TopicArn='topic',
            Message='message',
            Subject='subject'
        )

    @patch('sys.argv', ['send_sns.py', '-t', 'test-topic', '-m', 'test-message', '-s', 'test-subject'])
    @patch('boto3.client')
    def test_main_execution(self, mock_boto3_client):
        import runpy
        mock_sns = MagicMock()
        mock_boto3_client.return_value = mock_sns

        # Verify the actual call down to boto3 through the __main__ block
        with patch.dict('os.environ', {'AWS_DEFAULT_REGION': 'us-east-1'}):
            runpy.run_path(os.path.join(os.path.dirname(__file__), '..', 'run', 'send_sns.py'), run_name="__main__")

        # Verify
        mock_boto3_client.assert_called_once_with('sns')
        mock_sns.publish.assert_called_once_with(
            TopicArn='test-topic',
            Message='test-message',
            Subject='test-subject'
        )

if __name__ == '__main__':
    unittest.main()
