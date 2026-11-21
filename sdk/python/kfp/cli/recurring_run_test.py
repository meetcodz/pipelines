# Copyright 2026 The Kubeflow Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import unittest
from unittest import mock

from click import testing

from kfp.cli import recurring_run
from kfp.server_api import V2RecurringRun


def _create_mock_recurring_run(
    recurring_run_id: str = 'test-id',
    status: str = 'ENABLED',
    name: str = 'test-job',
) -> V2RecurringRun:
    return V2RecurringRun(
        recurring_run_id=recurring_run_id,
        display_name=name,
        status=status,
        created_at=datetime.datetime(2026, 1, 1, 12, 0, 0),
    )


class TestRecurringRunWaitHelper(unittest.TestCase):
    def test_wait_immediate_success(self):
        mock_client = mock.MagicMock()
        mock_client.get_recurring_run.return_value = _create_mock_recurring_run(
            status='ENABLED'
        )

        result = recurring_run._wait_for_recurring_run_status(
            client_obj=mock_client,
            recurring_run_id='test-id',
            target_status='ENABLED',
            timeout=10,
            sleep_interval=0.01,
        )

        self.assertEqual(result.status, 'ENABLED')
        mock_client.get_recurring_run.assert_called_once_with(
            recurring_run_id='test-id'
        )

    @mock.patch('time.sleep')
    def test_wait_polling_success(self, mock_sleep):
        mock_client = mock.MagicMock()
        mock_client.get_recurring_run.side_effect = [
            _create_mock_recurring_run(status='DISABLED'),
            _create_mock_recurring_run(status='DISABLED'),
            _create_mock_recurring_run(status='ENABLED'),
        ]

        result = recurring_run._wait_for_recurring_run_status(
            client_obj=mock_client,
            recurring_run_id='test-id',
            target_status='ENABLED',
            timeout=10,
            sleep_interval=0.01,
        )

        self.assertEqual(result.status, 'ENABLED')
        self.assertEqual(mock_client.get_recurring_run.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

    @mock.patch('time.sleep')
    def test_wait_timeout(self, mock_sleep):
        mock_client = mock.MagicMock()
        mock_client.get_recurring_run.return_value = _create_mock_recurring_run(
            status='DISABLED'
        )

        with self.assertRaises(TimeoutError) as ctx:
            recurring_run._wait_for_recurring_run_status(
                client_obj=mock_client,
                recurring_run_id='test-id',
                target_status='ENABLED',
                timeout=0,
                sleep_interval=0.01,
            )

        self.assertIn(
            'Timed out after 0 seconds waiting for recurring run test-id',
            str(ctx.exception),
        )


class TestRecurringRunCommands(unittest.TestCase):
    def setUp(self):
        self.runner = testing.CliRunner()
        self.mock_client = mock.MagicMock()

    def test_enable_no_wait(self):
        self.mock_client.get_recurring_run.return_value = (
            _create_mock_recurring_run(status='DISABLED')
        )

        result = self.runner.invoke(
            cli=recurring_run.recurring_run,
            args=['enable', 'test-id'],
            obj={'client': self.mock_client, 'output': 'table'},
            catch_exceptions=False,
        )

        self.assertEqual(result.exit_code, 0)
        self.mock_client.enable_recurring_run.assert_called_once_with(
            recurring_run_id='test-id'
        )
        self.mock_client.get_recurring_run.assert_called_once_with(
            recurring_run_id='test-id'
        )
        self.assertIn('test-id', result.output)
        self.assertIn('DISABLED', result.output)

    @mock.patch('time.sleep')
    def test_enable_with_wait(self, mock_sleep):
        self.mock_client.get_recurring_run.side_effect = [
            _create_mock_recurring_run(status='DISABLED'),
            _create_mock_recurring_run(status='ENABLED'),
        ]

        result = self.runner.invoke(
            cli=recurring_run.recurring_run,
            args=['enable', 'test-id', '--wait'],
            obj={'client': self.mock_client, 'output': 'table'},
            catch_exceptions=False,
        )

        self.assertEqual(result.exit_code, 0)
        self.mock_client.enable_recurring_run.assert_called_once_with(
            recurring_run_id='test-id'
        )
        self.assertEqual(self.mock_client.get_recurring_run.call_count, 2)
        self.assertIn('ENABLED', result.output)

    @mock.patch('time.sleep')
    def test_enable_with_wait_timeout(self, mock_sleep):
        self.mock_client.get_recurring_run.return_value = (
            _create_mock_recurring_run(status='DISABLED')
        )

        result = self.runner.invoke(
            cli=recurring_run.recurring_run,
            args=['enable', 'test-id', '--wait', '--timeout', '0'],
            obj={'client': self.mock_client, 'output': 'table'},
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIsInstance(result.exception, TimeoutError)

    def test_disable_no_wait(self):
        self.mock_client.get_recurring_run.return_value = (
            _create_mock_recurring_run(status='ENABLED')
        )

        result = self.runner.invoke(
            cli=recurring_run.recurring_run,
            args=['disable', 'test-id'],
            obj={'client': self.mock_client, 'output': 'table'},
            catch_exceptions=False,
        )

        self.assertEqual(result.exit_code, 0)
        self.mock_client.disable_recurring_run.assert_called_once_with(
            recurring_run_id='test-id'
        )
        self.mock_client.get_recurring_run.assert_called_once_with(
            recurring_run_id='test-id'
        )
        self.assertIn('test-id', result.output)
        self.assertIn('ENABLED', result.output)

    @mock.patch('time.sleep')
    def test_disable_with_wait(self, mock_sleep):
        self.mock_client.get_recurring_run.side_effect = [
            _create_mock_recurring_run(status='ENABLED'),
            _create_mock_recurring_run(status='DISABLED'),
        ]

        result = self.runner.invoke(
            cli=recurring_run.recurring_run,
            args=['disable', 'test-id', '--wait'],
            obj={'client': self.mock_client, 'output': 'table'},
            catch_exceptions=False,
        )

        self.assertEqual(result.exit_code, 0)
        self.mock_client.disable_recurring_run.assert_called_once_with(
            recurring_run_id='test-id'
        )
        self.assertEqual(self.mock_client.get_recurring_run.call_count, 2)
        self.assertIn('DISABLED', result.output)

    @mock.patch('time.sleep')
    def test_disable_with_wait_timeout(self, mock_sleep):
        self.mock_client.get_recurring_run.return_value = (
            _create_mock_recurring_run(status='ENABLED')
        )

        result = self.runner.invoke(
            cli=recurring_run.recurring_run,
            args=['disable', 'test-id', '--wait', '--timeout', '0'],
            obj={'client': self.mock_client, 'output': 'table'},
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIsInstance(result.exception, TimeoutError)


if __name__ == '__main__':
    unittest.main()
