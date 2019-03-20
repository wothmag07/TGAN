from unittest import TestCase
from unittest.mock import ANY, MagicMock, patch

import numpy as np
import pandas as pd
from numpy.testing import assert_allclose, assert_equal

from tgan import dataprocess


class TestDataProcess(TestCase):

    def test_check_metadata_valid_input(self):
        """If metadata is valid, the function does nothing."""
        # Setup
        metadata = {
            'details': [
                {
                    'type': 'category'
                },
                {
                    'type': 'value'
                }
            ]
        }

        # Run
        result = dataprocess.check_metadata(metadata)

        # Check
        assert result is None

    def test_check_metadata_raises_invalid_input(self):
        """ """
        # Setup
        metadata = {
            'details': [
                {
                    'type': 'category'
                },
                {
                    'type': 'value'
                }
            ]
        }

        try:
            # Run
            dataprocess.check_metadata(metadata)
        except AssertionError as error:
            # Check
            assert error.args[0] == 'The given metadata contains unsupported types.'

    def test_check_inputs_valid_input(self):
        """When the input is a valid np.ndarray, the function is called as is."""
        # Setup
        function = MagicMock(return_value='result')
        instance = MagicMock()
        data = np.zeros((5, 1))

        # Run
        decorated = dataprocess.check_inputs(function)
        result = decorated(instance, data)

        # Check
        assert result == 'result'
        function.assert_called_once_with(instance, data)
        assert len(instance.call_args_list) == 0
        assert len(instance.method_calls) == 0

    def test_check_inputs_invalid_type(self):
        """If the input of the decorated function is not a np.ndarray an exception is raised."""
        # Setup
        function = MagicMock(return_value='result')
        instance = MagicMock()
        data = 'some invalid data'
        expected_message = 'The argument `data` must be a numpy.ndarray with shape (n, 1).'

        # Run
        decorated = dataprocess.check_inputs(function)
        try:
            decorated(instance, data)

        except ValueError as error:
            # Check
            error.args[0] == expected_message

        assert len(function.call_args_list) == 0
        assert len(instance.call_args_list) == 0
        assert len(instance.method_calls) == 0

    def test_check_inputs_invalid_shape(self):
        """If the input of the decorated function has an invalid shape an exception is raised."""
        # Setup
        function = MagicMock(return_value='result')
        instance = MagicMock()
        data = np.array(['some array', 'of invalid shape'])
        expected_message = 'The argument `data` must be a numpy.ndarray with shape (n, 1).'

        # Run
        decorated = dataprocess.check_inputs(function)
        try:
            decorated(instance, data)

        except ValueError as error:
            # Check
            error.args[0] == expected_message

        assert len(function.call_args_list) == 0
        assert len(instance.call_args_list) == 0
        assert len(instance.method_calls) == 0

    @patch('tgan.dataprocess.np.random.rand', autospec=True)
    @patch('tgan.dataprocess.pd.DataFrame.to_csv', autospec=True)
    @patch('tgan.dataprocess.pd.read_csv', autospec=True)
    def test_split_csv(self, read_mock, csv_mock, rand_mock):
        """Split a csv file in two and save the parts."""
        # Setup
        csv_filename = 'path to csv'
        csv_out1 = 'path to split csv 1'
        csv_out2 = 'path to split csv 2'
        ratio = 0.5

        read_mock.return_value = pd.DataFrame(index=range(5), columns=list('ABC'))
        rand_mock.return_value = np.array([0.1, 0.3, 0.5, 0.7, 0.9])

        kwargs = {
            'header': False,
            'index': False
        }
        expected_csv_mock_call_args_list = [
            ((ANY, 'path to split csv 1',), kwargs),
            ((ANY, 'path to split csv 2',), kwargs)
        ]

        # Run
        result = dataprocess.split_csv(csv_filename, csv_out1, csv_out2, ratio)

        # Check - Result
        assert result is None

        # Check - pd.read_csv mock
        read_mock.assert_called_once_with('path to csv', header=-1)
        # Check - np.random rand mock
        rand_mock.assert_called_once_with(5)
        # Check - pd.DataFrame.to_csv mock
        assert csv_mock.call_args_list == expected_csv_mock_call_args_list

    @patch('tgan.dataprocess.np.savez', autospec=True)
    @patch('tgan.dataprocess.json.dumps', autospec=True)
    @patch('tgan.dataprocess.CategoricalTransformer', autospec=True)
    @patch('tgan.dataprocess.pd.read_csv', autospec=True)
    def test_csv_to_npz_categorical_column(
        self, read_mock, transformer_mock, json_mock, savez_mock
    ):
        """When a column is categorical its values are mapped to integers."""
        # Setup
        csv_filename = 'Path to load the csv from.'
        npz_filename = 'Path to save the numpy arrays.'
        continuous_cols = []

        read_mock.return_value = pd.DataFrame(['A', 'B', 'C', 'D', 'A', 'B', 'C', 'D'])
        json_mock.return_value = 'string with a JSON'
        instance_mock = MagicMock(**{
            'transform.return_value': (
                np.array([[0], [1], [2], [3], [0], [1], [2], [3]]),
                ['A', 'B', 'C', 'D'],
                4
            )
        })
        transformer_mock.return_value = instance_mock

        expected_info = {
            'num_features': 1,
            'details': [{
                'type': 'category',
                'mapping': ['A', 'B', 'C', 'D'],
                'n': 4
            }]
        }

        # Run
        result = dataprocess.csv_to_npz(csv_filename, npz_filename, continuous_cols)

        # Check - Result
        assert result is None

        # Check pd.read_csv mock
        read_mock.assert_called_once_with('Path to load the csv from.', header=-1)

        # Check json.dumps mock
        json_mock.assert_called_once_with(expected_info)

        # Check np.savez mock
        assert len(savez_mock.call_args_list) == 1
        call_args, call_kwargs = savez_mock.call_args_list[0]
        assert call_args == ('Path to save the numpy arrays.',)
        assert call_kwargs['info'] == 'string with a JSON'
        assert_equal(
            call_kwargs['f00'],
            np.array([[0], [1], [2], [3], [0], [1], [2], [3]])
        )
        assert len(call_kwargs.keys()) == 2

        # Check CategoricalTransformer mock
        transformer_mock.assert_called_once_with()

        # Check CategoricalTransformer instance mock
        assert len(instance_mock.transform.call_args_list) == 1
        call_args, call_kwargs = instance_mock.transform.call_args_list[0]
        assert call_kwargs == {}
        assert_equal(call_args, (np.array([['A', 'B', 'C', 'D', 'A', 'B', 'C', 'D']], )))

    @patch('tgan.dataprocess.np.savez', autospec=True)
    @patch('tgan.dataprocess.json.dumps', autospec=True)
    @patch('tgan.dataprocess.MultiModalNumberTransformer', autospec=True)
    @patch('tgan.dataprocess.pd.read_csv', autospec=True)
    def test_csv_to_npz_value_column(self, read_mock, transformer_mock, json_mock, savez_mock):
        """When a column is continous its values are clustered."""
        # Setup
        csv_filename = 'Path to load the csv from.'
        npz_filename = 'Path to save the numpy arrays.'
        continuous_cols = [0]

        read_mock.return_value = pd.DataFrame(list(range(5)))
        instance_mock = MagicMock(**{
            'transform.return_value': (
                np.array([['feature_1'], ['feature_2']]),
                np.array([['prob_1'], ['prob_2']]),
                'means returned by value_clustering',
                'stds returned by value_clustering',
            )
        })
        transformer_mock.return_value = instance_mock
        json_mock.return_value = 'string with a JSON'

        expected_call_kwargs_f00 = np.array([
            ['feature_1', 'prob_1'],
            ['feature_2', 'prob_2']
        ])

        expected_info = {
            'num_features': 1,
            'details': [{
                'type': 'value',
                'means': 'means returned by value_clustering',
                'stds': 'stds returned by value_clustering',
                'n': 5
            }]
        }

        # Run
        result = dataprocess.csv_to_npz(csv_filename, npz_filename, continuous_cols)

        # Check
        assert result is None

        read_mock.assert_called_once_with('Path to load the csv from.', header=-1)
        json_mock.assert_called_once_with(expected_info)

        assert len(savez_mock.call_args_list) == 1
        call_args, call_kwargs = savez_mock.call_args_list[0]
        assert call_args == ('Path to save the numpy arrays.', )
        assert call_kwargs['info'] == 'string with a JSON'
        assert_equal(call_kwargs['f00'], expected_call_kwargs_f00)
        assert len(call_kwargs.keys()) == 2

        transformer_mock.assert_called_once_with()
        assert len(instance_mock.call_args_list) == 0
        assert len(instance_mock.transform.call_args_list) == 1
        call_args, call_kwargs = instance_mock.transform.call_args_list[0]

        assert len(call_args) == 1
        assert_equal(call_args[0], np.array([[0], [1], [2], [3], [4]]))
        assert call_kwargs == {}

    @patch('tgan.dataprocess.np.load', autospec=True)
    @patch('tgan.dataprocess.json.loads', autospec=True)
    @patch('tgan.dataprocess.MultiModalNumberTransformer', autospec=True)
    @patch('tgan.dataprocess.pd.DataFrame.to_csv', autospec=True)
    def test_npz_to_csv_value_column(self, csv_mock, transformer_mock, json_mock, load_mock):
        """ """
        # Setup
        npfilename = 'Path to the origin npz file.'
        csvfilename = 'Path to the destination csv file'

        load_mock.return_value = {
            'info': 'Metadata for the given array.',
            'f00': np.array(['stored', 'values'])
        }

        json_mock.return_value = {
            'num_features': 1,
            'details': [{
                'type': 'value',
                'means': 'means returned by value_clustering',
                'stds': 'stds returned by value_clustering',
                'n': 5
            }]
        }
        instance_mock = MagicMock(**{
            'reverse_transform.return_value': np.array(['result of', '_rev_feature'])
        })
        transformer_mock.return_value = instance_mock

        # Run
        result = dataprocess.npz_to_csv(npfilename, csvfilename)

        # Check
        assert result is None

        load_mock.assert_called_once_with('Path to the origin npz file.')
        json_mock.assert_called_once_with('Metadata for the given array.')

        assert len(csv_mock.call_args_list) == 1
        call_args, call_kwargs = csv_mock.call_args_list[0]
        len(call_args) == 2
        assert call_args[0].equals(pd.DataFrame(['result of', '_rev_feature']))
        assert call_args[1] == 'Path to the destination csv file'
        assert call_kwargs == {'index': False, 'header': False}

        transformer_mock.assert_called_once_with()

        assert len(instance_mock.reverse_transform.call_args_list) == 1
        call_args, call_kwargs = instance_mock.reverse_transform.call_args_list[0]

        assert len(call_args) == 2
        assert_equal(call_args[0], np.array(['stored', 'values']))
        assert call_args[1] == {
            'type': 'value',
            'means': 'means returned by value_clustering',
            'stds': 'stds returned by value_clustering',
            'n': 5
        }
        assert call_kwargs == {}

    @patch('tgan.dataprocess.np.load', autospec=True)
    @patch('tgan.dataprocess.json.loads', autospec=True)
    @patch('tgan.dataprocess.CategoricalTransformer', autospec=True)
    @patch('tgan.dataprocess.pd.DataFrame.to_csv', autospec=True)
    def test_npz_to_csv_categorical_column(self, csv_mock, transformer_mock, json_mock, load_mock):
        """ """
        # Setup
        npfilename = 'Path to the origin npz file.'
        csvfilename = 'Path to the destination csv file'

        load_mock.return_value = {
            'info': 'Metadata for the given array.',
            'f00': np.array(['stored', 'values'])
        }

        json_mock.return_value = {
            'num_features': 1,
            'details': [{
                'type': 'category',
                'means': 'means returned by value_clustering',
                'stds': 'stds returned by value_clustering',
                'n': 5
            }]
        }
        instance_mock = MagicMock(**{
            'reverse_transform.return_value': np.array(['result of', '_rev_feature'])
        })
        transformer_mock.return_value = instance_mock

        # Run
        result = dataprocess.npz_to_csv(npfilename, csvfilename)

        # Check - Result
        assert result is None

        load_mock.assert_called_once_with('Path to the origin npz file.')
        json_mock.assert_called_once_with('Metadata for the given array.')

        assert len(csv_mock.call_args_list) == 1
        call_args, call_kwargs = csv_mock.call_args_list[0]
        len(call_args) == 2
        assert call_args[0].equals(pd.DataFrame(['result of', '_rev_feature']))
        assert call_args[1] == 'Path to the destination csv file'
        assert call_kwargs == {'index': False, 'header': False}

        transformer_mock.assert_called_once_with()

        assert len(instance_mock.reverse_transform.call_args_list) == 1
        call_args, call_kwargs = instance_mock.reverse_transform.call_args_list[0]

        assert len(call_args) == 2
        assert_equal(call_args[0], np.array(['stored', 'values']))
        assert call_args[1] == {
            'type': 'category',
            'means': 'means returned by value_clustering',
            'stds': 'stds returned by value_clustering',
            'n': 5
        }
        assert call_kwargs == {}


class TestMultiModelNumberTransformer(TestCase):

    def test___init__(self):
        """On init, constructor arguments are set as attributes."""
        # Setup / Run
        num_modes = 10
        instance = dataprocess.MultiModalNumberTransformer(num_modes=num_modes)

        # Check
        assert instance.num_modes == 10

    @patch('tgan.dataprocess.GaussianMixture', autospec=True)
    def test_transform(self, gaussian_mock):
        """transform cluster the values using a Gaussian Mixture model."""
        # Setup
        data = np.array([
            [0.1],
            [0.5],
            [1.0]
        ])
        num_modes = 2

        instance = dataprocess.MultiModalNumberTransformer(num_modes)

        model_mock_spec = {
            'fit.return_value': None,
            'means_': np.array([[0.0], [1.0]]),
            'covariances_': np.array([[[4.0], [1.0]]]),
            'predict_proba.return_value': np.array([
                [0.1, 0.2],
                [0.2, 0.1],
                [0.1, 0.2]
            ])
        }

        model_mock = MagicMock(**model_mock_spec)
        gaussian_mock.return_value = model_mock

        expected_features = np.array([
            [-0.45],
            [0.125],
            [0.000]
        ])
        expected_probabilities = np.array([
            [0.1, 0.2],
            [0.2, 0.1],
            [0.1, 0.2]
        ])
        expected_means = np.array([0.0, 1.0])  # Reshape from model_mock.means_
        expected_stds = np.array([2.0, 1.0])   # Reshape and sqrt from model_mock.covariances_

        # Run
        result = instance.transform(data)
        features, probabilities, means, stds = result

        # Check
        assert_equal(features, expected_features)
        assert_equal(probabilities, expected_probabilities)
        assert_equal(means, expected_means)
        assert_equal(stds, expected_stds)

        gaussian_mock.assert_called_once_with(2)
        model_mock.fit.assert_called_once_with(data)
        model_mock.predict_proba.assert_called_once_with(data)

    def test_reverse_transform(self):
        """reverse_transform reverses the clustering."""
        # Setup
        data = np.array([
            [-0.45, 0.1, 0.2],
            [0.125, 0.2, 0.1],
            [0.000, 0.1, 0.2]

        ])

        info = {
            'type': 'value',
            'means': np.array([0.0, 1.0]),
            'stds': np.array([2.0, 1.0]),
        }

        instance = dataprocess.MultiModalNumberTransformer()

        expected_result = np.array([0.1, 0.5, 1.0])

        # Run
        result = instance.reverse_transform(data, info)

        # Check
        assert_allclose(result, expected_result)  # Minor difference due to floating point.


class TestCategoricalTransformer(TestCase):

    def test_transform(self):
        """transform maps categorical values into integers."""
        # Setup
        data = np.array(['A', 'B', 'C', 'D', 'A', 'B', 'C', 'D'])
        instance = dataprocess.CategoricalTransformer()

        expected_features = np.array([[0], [1], [2], [3], [0], [1], [2], [3]])
        expected_unique_values = ['A', 'B', 'C', 'D']
        expected_n = 4

        # Run
        result = instance.transform(data)
        features, unique_values, n = result

        # Check
        assert_equal(features, expected_features)
        assert unique_values == expected_unique_values
        assert n == expected_n

    def test_reverse_transform(self):
        """reverse_transform maps transformed categorical values back to their original values."""
        # Setup
        data = np.array([[0], [1], [2], [1], [0]])
        info = {
            'type': 'category',
            'mapping': ['A', 'B', 'C']
        }

        expected_result = ['A', 'B', 'C', 'B', 'A']
        instance = dataprocess.CategoricalTransformer()

        # Run
        result = instance.reverse_transform(data, info)

        # Check
        assert result == expected_result
