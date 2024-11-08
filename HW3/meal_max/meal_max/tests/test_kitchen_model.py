from contextlib import contextmanager
import re
import sqlite3

import pytest

from meal_max.models.kitchen_model import (
    Meal,
    create_meal,
    delete_meal,
    get_leaderboard,
    get_meal_by_id,
    get_meal_by_name,
    update_meal_stats
)


######################################################
#
#    Fixtures
#
######################################################


def normalize_whitespace(sql_query: str) -> str:
    return re.sub(r'\s+', ' ', sql_query).strip()


# Mocking the database connection for tests
@pytest.fixture
def mock_cursor(mocker):
    mock_conn = mocker.Mock()
    mock_cursor = mocker.Mock()

    # Mock the connection's cursor
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = None  # Default return for queries
    mock_cursor.fetchall.return_value = []
    mock_conn.commit.return_value = None

    # Mock the get_db_connection context manager from sql_utils
    @contextmanager
    def mock_get_db_connection():
        yield mock_conn  # Yield the mocked connection object

    mocker.patch("meal_max.models.kitchen_model.get_db_connection", mock_get_db_connection)

    return mock_cursor  # Return the mock cursor so we can set expectations per test


######################################################
#
#    Test Meal Class
#
######################################################


def test_meal_creation():
    """Test creating a valid Meal object."""
    meal = Meal(id=1, meal="Pizza", cuisine="Italian", price=15.99, difficulty="MED")
    assert meal.id == 1
    assert meal.meal == "Pizza"
    assert meal.cuisine == "Italian"
    assert meal.price == 15.99
    assert meal.difficulty == "MED"


def test_meal_invalid_price():
    """Test creating a Meal with invalid price."""
    with pytest.raises(ValueError, match="Price must be a positive value."):
        Meal(id=1, meal="Pizza", cuisine="Italian", price=-15.99, difficulty="MED")


def test_meal_invalid_difficulty():
    """Test creating a Meal with invalid difficulty."""
    with pytest.raises(ValueError, match="Difficulty must be 'LOW', 'MED', or 'HIGH'."):
        Meal(id=1, meal="Pizza", cuisine="Italian", price=15.99, difficulty="INVALID")


######################################################
#
#    Add and delete
#
######################################################

def test_create_meal(mock_cursor):
    """Test for creating a new meal."""
    create_meal("Pizza", "Italian", 15.99, "MED")

    expected_query = normalize_whitespace("""
        INSERT INTO meals (meal, cuisine, price, difficulty)
        VALUES (?, ?, ?, ?)
    """)

    actual_query = normalize_whitespace(mock_cursor.execute.call_args[0][0])

    # Assert that the SQL query is correct
    assert actual_query == expected_query, "The SQL query did not match the expected structure."

    # Extract the arguments used in the SQL call (second element of call_args)
    actual_arguments = mock_cursor.execute.call_args[0][1]

    # Assert that the SQL query was executed with the correct arguments
    expected_arguments = ("Pizza", "Italian", 15.99, "MED")
    assert actual_arguments == expected_arguments, f"The SQL query arguments did not match. Expected {expected_arguments}, got {actual_arguments}."


def test_create_meal_duplicate(mock_cursor):
    """Test for creating a duplicate meal (should raise an error)."""
    mock_cursor.execute.side_effect = sqlite3.IntegrityError()

    with pytest.raises(ValueError, match="Meal with name 'Pizza' already exists"):
        create_meal("Pizza", "Italian", 15.99, "MED")


def test_create_meal_invalid_price():
    """Test creating a meal with invalid price."""
    with pytest.raises(ValueError, match="Invalid price: -15.99. Price must be a positive number."):
        create_meal("Pizza", "Italian", -15.99, "MED")

    with pytest.raises(ValueError, match="Invalid price: invalid. Price must be a positive number."):
        create_meal("Pizza", "Italian", "invalid", "MED")


def test_create_meal_invalid_difficulty():
    """Test creating a meal with invalid difficulty."""
    with pytest.raises(ValueError, match="Invalid difficulty level: INVALID. Must be 'LOW', 'MED', or 'HIGH'."):
        create_meal("Pizza", "Italian", 15.99, "INVALID")


def test_delete_meal(mock_cursor):
    """Test soft deleting a meal."""
    # Simulate meal exists and is not deleted
    mock_cursor.fetchone.return_value = [False]

    delete_meal(1)

    # Verify correct SQL queries
    expected_select = normalize_whitespace("SELECT deleted FROM meals WHERE id = ?")
    expected_update = normalize_whitespace("UPDATE meals SET deleted = TRUE WHERE id = ?")

    actual_select = normalize_whitespace(mock_cursor.execute.call_args_list[0][0][0])
    actual_update = normalize_whitespace(mock_cursor.execute.call_args_list[1][0][0])

    assert actual_select == expected_select
    assert actual_update == expected_update

    # Verify correct arguments
    assert mock_cursor.execute.call_args_list[0][0][1] == (1,)
    assert mock_cursor.execute.call_args_list[1][0][1] == (1,)


def test_delete_meal_not_found(mock_cursor):
    """Test deleting a non-existent meal."""
    mock_cursor.fetchone.return_value = None

    with pytest.raises(ValueError, match="Meal with ID 999 not found"):
        delete_meal(999)


def test_delete_meal_already_deleted(mock_cursor):
    """Test deleting an already deleted meal."""
    mock_cursor.fetchone.return_value = [True]

    with pytest.raises(ValueError, match="Meal with ID 999 has been deleted"):
        delete_meal(999)

######################################################
#
#    Test Get Methods
#
######################################################


def test_get_meal_by_id(mock_cursor):
    """Test retrieving a meal by ID."""
    mock_cursor.fetchone.return_value = (1, "Pizza", "Italian", 15.99, "MED", False)

    result = get_meal_by_id(1)
    expected = Meal(id=1, meal="Pizza", cuisine="Italian", price=15.99, difficulty="MED")

    assert result == expected

    expected_query = normalize_whitespace(
        "SELECT id, meal, cuisine, price, difficulty, deleted FROM meals WHERE id = ?"
    )
    actual_query = normalize_whitespace(mock_cursor.execute.call_args[0][0])
    assert actual_query == expected_query
    assert mock_cursor.execute.call_args[0][1] == (1,)


def test_get_meal_by_id_not_found(mock_cursor):
    """Test retrieving a non-existent meal by ID."""
    mock_cursor.fetchone.return_value = None

    with pytest.raises(ValueError, match="Meal with ID 999 not found"):
        get_meal_by_id(999)


def test_get_meal_by_id_deleted(mock_cursor):
    """Test retrieving a deleted meal by ID."""
    mock_cursor.fetchone.return_value = (1, "Pizza", "Italian", 15.99, "MED", True)

    with pytest.raises(ValueError, match="Meal with ID 1 has been deleted"):
        get_meal_by_id(1)


def test_get_meal_by_name(mock_cursor):
    """Test retrieving a meal by name."""
    mock_cursor.fetchone.return_value = (1, "Pizza", "Italian", 15.99, "MED", False)

    result = get_meal_by_name("Pizza")
    expected = Meal(id=1, meal="Pizza", cuisine="Italian", price=15.99, difficulty="MED")

    assert result == expected

    expected_query = normalize_whitespace(
        "SELECT id, meal, cuisine, price, difficulty, deleted FROM meals WHERE meal = ?"
    )
    actual_query = normalize_whitespace(mock_cursor.execute.call_args[0][0])
    assert actual_query == expected_query
    assert mock_cursor.execute.call_args[0][1] == ("Pizza",)


def test_get_meal_by_name_not_found(mock_cursor):
    """Test retrieving a non-existent meal by name."""
    mock_cursor.fetchone.return_value = None

    with pytest.raises(ValueError, match="Meal with name NonExistent not found"):
        get_meal_by_name("NonExistent")


def test_get_meal_by_name_deleted(mock_cursor):
    """Test retrieving a deleted meal by name."""
    mock_cursor.fetchone.return_value = (1, "Pizza", "Italian", 15.99, "MED", True)

    with pytest.raises(ValueError, match="Meal with name Pizza has been deleted"):
        get_meal_by_name("Pizza")


def test_get_leaderboard(mock_cursor):
    """Test retrieving the leaderboard."""
    mock_cursor.fetchall.return_value = [
        (1, "Pizza", "Italian", 15.99, "MED", 10, 7, 0.7),
        (2, "Burger", "American", 12.99, "LOW", 5, 2, 0.4)
    ]

    result = get_leaderboard()
    expected = [
        {
            'id': 1, 'meal': "Pizza", 'cuisine': "Italian", 'price': 15.99,
            'difficulty': "MED", 'battles': 10, 'wins': 7, 'win_pct': 70.0
        },
        {
            'id': 2, 'meal': "Burger", 'cuisine': "American", 'price': 12.99,
            'difficulty': "LOW", 'battles': 5, 'wins': 2, 'win_pct': 40.0
        }
    ]

    assert result == expected

    expected_query = normalize_whitespace("""
        SELECT id, meal, cuisine, price, difficulty, battles, wins, (wins * 1.0 / battles) AS win_pct
        FROM meals WHERE deleted = false AND battles > 0 ORDER BY wins DESC
    """)
    actual_query = normalize_whitespace(mock_cursor.execute.call_args[0][0])
    assert actual_query == expected_query


def test_get_leaderboard_by_win_pct(mock_cursor):
    """Test retrieving the leaderboard sorted by win percentage."""
    mock_cursor.fetchall.return_value = [
        (1, "Pizza", "Italian", 15.99, "MED", 10, 7, 0.7),
        (2, "Burger", "American", 12.99, "LOW", 5, 2, 0.4)
    ]

    result = get_leaderboard(sort_by="win_pct")  # Call the function to trigger the mock

    expected_query = normalize_whitespace("""
        SELECT id, meal, cuisine, price, difficulty, battles, wins, (wins * 1.0 / battles) AS win_pct
        FROM meals WHERE deleted = false AND battles > 0 ORDER BY win_pct DESC
    """)
    actual_query = normalize_whitespace(mock_cursor.execute.call_args[0][0])
    assert actual_query == expected_query


def test_get_leaderboard_invalid_sort(mock_cursor):
    """Test retrieving the leaderboard with invalid sort parameter."""
    with pytest.raises(ValueError, match="Invalid sort_by parameter: invalid"):
        get_leaderboard(sort_by="invalid")


######################################################
#
#    Test Update Stats
#
######################################################


def test_update_meal_stats(mock_cursor):
    """Test updating meal stats after a battle."""
    mock_cursor.fetchone.return_value = [False]

    update_meal_stats(1, "win")

    expected_query = normalize_whitespace(
        "UPDATE meals SET battles = battles + 1, wins = wins + 1 WHERE id = ?"
    )
    actual_query = normalize_whitespace(mock_cursor.execute.call_args_list[1][0][0])
    assert actual_query == expected_query
    assert mock_cursor.execute.call_args_list[1][0][1] == (1,)


def test_update_meal_stats_loss(mock_cursor):
    """Test updating meal stats after a loss."""
    mock_cursor.fetchone.return_value = [False]

    update_meal_stats(1, "loss")

    expected_query = normalize_whitespace(
        "UPDATE meals SET battles = battles + 1 WHERE id = ?"
    )
    actual_query = normalize_whitespace(mock_cursor.execute.call_args_list[1][0][0])
    assert actual_query == expected_query
    assert mock_cursor.execute.call_args_list[1][0][1] == (1,)


def test_update_meal_stats_invalid_result(mock_cursor):
    """Test updating meal stats with invalid result."""
    mock_cursor.fetchone.return_value = [False]

    with pytest.raises(ValueError, match="Invalid result: invalid. Expected 'win' or 'loss'."):
        update_meal_stats(1, "invalid")


def test_update_meal_stats_deleted(mock_cursor):
    """Test updating stats for a deleted meal."""
    mock_cursor.fetchone.return_value = [True]

    with pytest.raises(ValueError, match="Meal with ID 1 has been deleted"):
        update_meal_stats(1, "win")


def test_update_meal_stats_not_found(mock_cursor):
    """Test updating stats for a non-existent meal."""
    mock_cursor.fetchone.return_value = None

    with pytest.raises(ValueError, match="Meal with ID 999 not found"):
        update_meal_stats(999, "win")
