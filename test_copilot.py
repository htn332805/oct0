import pytest
import json
from unittest.mock import Mock, patch, mock_open
from scripts.copilot_client import CopilotClient


class TestCopilotClient:
    """Test suite for CopilotClient class."""

    @patch('scripts.copilot_client.load')
    def test_init_with_config_api_key(self, mock_load):
        """Test initialization with API key from config."""
        mock_load.return_value = {'openai_api_key': 'test-key-123'}
        client = CopilotClient()
        assert client.api_key == 'test-key-123'
        assert client.model == 'gpt-4'

    @patch('scripts.copilot_client.load')
    def test_init_with_explicit_api_key(self, mock_load):
        """Test initialization with explicitly provided API key."""
        client = CopilotClient(api_key='explicit-key')
        assert client.api_key == 'explicit-key'

    @patch('scripts.copilot_client.load')
    def test_init_missing_api_key(self, mock_load):
        """Test initialization fails when no API key is available."""
        mock_load.return_value = {'openai_api_key': ''}
        with pytest.raises(ValueError, match="OpenAI API key not found"):
            CopilotClient()

    @patch('openai.OpenAI')
    @patch('scripts.copilot_client.load')
    def test_chat_completion_success(self, mock_load, mock_openai):
        """Test successful chat completion."""
        mock_load.return_value = {'openai_api_key': 'test-key'}

        # Mock the OpenAI client and response
        mock_client = Mock()
        mock_openai.return_value = mock_client

        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "Test response"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        client = CopilotClient()
        messages = [{"role": "user", "content": "Hello"}]
        result = client.chat_completion(messages)

        assert result == "Test response"
        mock_client.chat.completions.create.assert_called_once()

    @patch('scripts.copilot_client.load')
    def test_load_prompt_template(self, mock_load):
        """Test loading prompt templates."""
        mock_load.return_value = {'openai_api_key': 'test-key'}

        template_data = {
            "prompt": "Test prompt with {variable}",
            "parameters": {"temperature": 0.5}
        }

        with patch('builtins.open', mock_open(read_data=json.dumps(template_data))), \
             patch('os.path.exists', return_value=True):
            client = CopilotClient()
            result = client.load_prompt_template('summary')

            assert result == template_data

    @patch('scripts.copilot_client.load')
    def test_load_prompt_template_not_found(self, mock_load):
        """Test loading non-existent prompt template."""
        mock_load.return_value = {'openai_api_key': 'test-key'}

        client = CopilotClient()
        with pytest.raises(FileNotFoundError):
            client.load_prompt_template('nonexistent')

    def test_parse_flashcard_response(self):
        """Test parsing flashcard responses."""
        response = """Q: What is Python?
A: A programming language

Q: What is AI?
A: Artificial Intelligence"""

        client = CopilotClient(api_key='test-key')
        flashcards = client.parse_flashcard_response(response)

        assert len(flashcards) == 2
        assert flashcards[0]['question'] == 'What is Python?'
        assert flashcards[0]['answer'] == 'A programming language'
        assert flashcards[1]['question'] == 'What is AI?'
        assert flashcards[1]['answer'] == 'Artificial Intelligence'

    def test_parse_quiz_response(self):
        """Test parsing quiz responses."""
        response = """Question 1: What is 2+2?
A) 3
B) 4
C) 5
D) 6
Correct: B"""

        client = CopilotClient(api_key='test-key')
        questions = client.parse_quiz_response(response)

        assert len(questions) == 1
        assert questions[0]['question'] == 'What is 2+2?'
        assert questions[0]['options'] == ['3', '4', '5', '6']
        assert questions[0]['correct_answer'] == 'B'

    def test_parse_summary_response(self):
        """Test parsing summary responses."""
        response = """Key concepts: Python, AI
Main ideas: Programming languages are tools for creating software."""

        client = CopilotClient(api_key='test-key')
        summary = client.parse_summary_response(response)

        assert 'key_concepts' in summary
        assert 'main_ideas' in summary


if __name__ == '__main__':
    pytest.main([__file__])