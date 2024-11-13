import pytest
from unittest.mock import patch, Mock
from requests.exceptions import Timeout, RequestException
from meal_max.utils.random_utils import get_random

@patch("meal_max.utils.random_utils.requests.get")
def test_get_random_success(mock_get):
    """Test successful retrieval of a random number."""
    # Mock the response of requests.get to return a valid random number string
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.text = "0.47"  # Example valid response
    mock_get.return_value = mock_response

    result = get_random()

    # Verify the response was parsed as a float
    assert result == 0.47
    mock_get.assert_called_once_with(
        "https://www.random.org/decimal-fractions/?num=1&dec=2&col=1&format=plain&rnd=new", timeout=5
    )


@patch("meal_max.utils.random_utils.requests.get")
def test_get_random_invalid_response(mock_get):
    """Test handling of invalid response from random.org."""
    # Mock the response of requests.get to return an invalid number string
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.text = "not_a_number"  # Invalid response for conversion
    mock_get.return_value = mock_response

    # Expect ValueError due to invalid float conversion
    with pytest.raises(ValueError, match="Invalid response from random.org: not_a_number"):
        get_random()


@patch("meal_max.utils.random_utils.requests.get")
def test_get_random_timeout(mock_get):
    """Test handling of a timeout from random.org."""
    # Mock requests.get to raise a Timeout exception
    mock_get.side_effect = Timeout

    # Expect RuntimeError due to timeout
    with pytest.raises(RuntimeError, match="Request to random.org timed out."):
        get_random()


@patch("meal_max.utils.random_utils.requests.get")
def test_get_random_request_exception(mock_get):
    """Test handling of general request failures."""
    # Mock requests.get to raise a general RequestException
    mock_get.side_effect = RequestException("General error")

    # Expect RuntimeError due to a general request failure
    with pytest.raises(RuntimeError, match="Request to random.org failed: General error"):
        get_random()
