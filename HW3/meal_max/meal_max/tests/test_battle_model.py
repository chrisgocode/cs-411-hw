import pytest

from meal_max.models.battle_model import BattleModel
from meal_max.models.kitchen_model import Meal


@pytest.fixture
def battle_model():
    """Fixture to provide a new instance of BattleModel for each test."""
    return BattleModel()


@pytest.fixture
def sample_meal1():
    return Meal(
        id=1,
        meal="Pizza",
        cuisine="Italian",
        price=15.99,
        difficulty="MED"
    )


@pytest.fixture
def sample_meal2():
    return Meal(
        id=2,
        meal="Tacos",
        cuisine="Mexican",
        price=12.99,
        difficulty="LOW"
    )


@pytest.fixture
def mock_get_random(mocker):
    """Mock the get_random function for testing purposes."""
    return mocker.patch("meal_max.models.battle_model.get_random")


@pytest.fixture
def mock_update_meal_stats(mocker):
    """Mock the update_meal_stats function for testing purposes."""
    return mocker.patch("meal_max.models.battle_model.update_meal_stats")

##################################################
# Combatant Management Test Cases
##################################################


def test_prep_combatant(battle_model, sample_meal1):
    """Test adding a combatant to the battle."""
    battle_model.prep_combatant(sample_meal1)
    assert len(battle_model.combatants) == 1
    assert battle_model.combatants[0].meal == "Pizza"


def test_prep_combatant_full_list(battle_model, sample_meal1, sample_meal2):
    """Test error when adding a third combatant."""
    battle_model.prep_combatant(sample_meal1)
    battle_model.prep_combatant(sample_meal2)

    meal3 = Meal(id=3, meal="Sushi", cuisine="Japanese", price=20.99, difficulty="HIGH")
    with pytest.raises(ValueError, match="Combatant list is full"):
        battle_model.prep_combatant(meal3)


def test_clear_combatants(battle_model, sample_meal1):
    """Test clearing all combatants."""
    battle_model.prep_combatant(sample_meal1)
    battle_model.clear_combatants()
    assert len(battle_model.combatants) == 0


def test_get_combatants(battle_model, sample_meal1, sample_meal2):
    """Test retrieving the list of combatants."""
    battle_model.prep_combatant(sample_meal1)
    battle_model.prep_combatant(sample_meal2)

    combatants = battle_model.get_combatants()
    assert len(combatants) == 2
    assert combatants[0].meal == "Pizza"
    assert combatants[1].meal == "Tacos"

##################################################
# Battle Score Test Cases
##################################################


def test_get_battle_score(battle_model, sample_meal1):
    """Test battle score calculation."""
    score = battle_model.get_battle_score(sample_meal1)
    # Price (15.99) * len("Italian")(7) - difficulty_modifier["MED"](2)
    expected_score = 15.99 * 7 - 2
    assert score == pytest.approx(expected_score, 0.01)


def test_get_battle_score_different_difficulties(battle_model):
    """Test battle scores with different difficulties."""
    meals = [
        Meal(id=1, meal="Test1", cuisine="Test", price=10.0, difficulty="LOW"),
        Meal(id=2, meal="Test2", cuisine="Test", price=10.0, difficulty="MED"),
        Meal(id=3, meal="Test3", cuisine="Test", price=10.0, difficulty="HIGH")
    ]

    scores = [battle_model.get_battle_score(meal) for meal in meals]
    # Ensure LOW difficulty (modifier 3) results in lowest score
    assert scores[0] < scores[1] < scores[2]

##################################################
# Battle Execution Test Cases
##################################################


def test_battle_not_enough_combatants(battle_model, sample_meal1):
    """Test error when battling with insufficient combatants."""
    battle_model.prep_combatant(sample_meal1)
    with pytest.raises(ValueError, match="Two combatants must be prepped"):
        battle_model.battle()


def test_battle_execution(battle_model, sample_meal1, sample_meal2, mock_get_random, mock_update_meal_stats):
    """Test complete battle execution with predetermined winner."""
    battle_model.prep_combatant(sample_meal1)
    battle_model.prep_combatant(sample_meal2)

    # Set random number to ensure meal1 wins
    mock_get_random.return_value = 0.1

    winner = battle_model.battle()

    # Verify winner and stats updates
    assert winner == "Pizza"
    mock_update_meal_stats.assert_any_call(1, "win")
    mock_update_meal_stats.assert_any_call(2, "loss")

    # Verify loser was removed from combatants
    assert len(battle_model.combatants) == 1
    assert battle_model.combatants[0].meal == "Pizza"


def test_battle_close_match(battle_model, sample_meal1, sample_meal2, mock_get_random, mock_update_meal_stats):
    """Test battle with very close scores."""
    battle_model.prep_combatant(sample_meal1)
    battle_model.prep_combatant(sample_meal2)

    # Set random number higher than normalized delta to ensure meal2 wins
    mock_get_random.return_value = 0.9

    winner = battle_model.battle()

    assert winner == "Tacos"
    mock_update_meal_stats.assert_any_call(2, "win")
    mock_update_meal_stats.assert_any_call(1, "loss")