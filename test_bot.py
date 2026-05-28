import unittest
from shared_utils import is_sentence_valid

class TestDevilGirlBotUtils(unittest.TestCase):

    def setUp(self):
        """Sets up mock data structures before each test runs."""
        # Mock pool matching v2.0 [{'sentence': '...', 'url': '...'}] structure
        self.mock_pool = [
            {"sentence": "This is a valid quote from a movie.", "url": "https://mastodon.social/1"},
            {"sentence": "Another classic sci-fi line here.", "url": "https://mastodon.social/2"}
        ]
        
        # Mock historical records (handling both old strings and new dicts safely)
        self.mock_history = [
            "We already posted this exact sentence years ago.",
            "Testing a duplicate string."
        ]
        
        # Simple banlist for explicit content filtering
        self.mock_banlist = ["bannedword", "spamsite"]

    def test_valid_sentence(self):
        """Ensure a clean, unique sentence of acceptable length passes validation."""
        test_str = "Look at the stars, they are beautiful tonight."
        result = is_sentence_valid(test_str, self.mock_pool, self.mock_history, self.mock_banlist)
        self.assertTrue(result, "A standard unique sentence should return True.")

    def test_sentence_too_short(self):
        """Sentences under 5 characters should be rejected."""
        test_str = "Heh"
        result = is_sentence_valid(test_str, self.mock_pool, self.mock_history, self.mock_banlist)
        self.assertFalse(result, "Sentences under 5 characters should return False.")

    def test_sentence_too_long(self):
        """Sentences over 150 characters should be rejected."""
        test_str = "This is a very long sentence designed explicitly to stretch past the boundaries of our standard one hundred and fifty character limit buffer zone to see if the filter catches it and fifty character limit buffer zone to see if the filter catches it and fifty character limit buffer zone to see if the filter catches it and fifty character limit buffer zone to see if the filter catches it."
        result = is_sentence_valid(test_str, self.mock_pool, self.mock_history, self.mock_banlist)
        self.assertFalse(result, "Sentences over 150 characters should return False.")

    def test_duplicate_in_pool(self):
        """Sentences already scraped into the current pool should be rejected."""
        test_str = "This is a valid quote from a movie."
        result = is_sentence_valid(test_str, self.mock_pool, self.mock_history, self.mock_banlist)
        self.assertFalse(result, "Sentences already sitting in the potential pool should return False.")

    def test_duplicate_in_history(self):
        """Sentences we have posted historically should be rejected."""
        test_str = "We already posted this exact sentence years ago."
        result = is_sentence_valid(test_str, self.mock_pool, self.mock_history, self.mock_banlist)
        self.assertFalse(result, "Sentences found in the historical logs should return False.")

    def test_banlist_trigger(self):
        """Sentences containing explicitly banned substrings should be rejected."""
        test_str = "This sentence contains a bannedword inside it."
        result = is_sentence_valid(test_str, self.mock_pool, self.mock_history, self.mock_banlist)
        self.assertFalse(result, "Sentences containing terms from the banlist should return False.")

if __name__ == '__main__':
    unittest.main()