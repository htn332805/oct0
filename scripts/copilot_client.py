import openai
import json
import os
import logging
from typing import Dict, List, Optional, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from config.config import load

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CopilotClient:
    """Client for interacting with OpenAI's API for Copilot-like functionality."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4"):
        """
        Initialize the Copilot client.

        Args:
            api_key: OpenAI API key. If None, loads from config.
            model: OpenAI model to use (default: gpt-4)
        """
        config = load()
        self.api_key = api_key or config.get('openai_api_key', '')
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Set it in config/settings.json or OPENAI_API_KEY environment variable.")

        self.model = model
        self.client = openai.OpenAI(api_key=self.api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type((openai.APIError, openai.APIConnectionError, openai.RateLimitError))
    )
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Make a chat completion request to OpenAI with retry logic.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            **kwargs: Additional parameters for the API call

        Returns:
            The response content from the model
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                **kwargs
            )
            return response.choices[0].message.content
        except openai.AuthenticationError as e:
            logger.error(f"Authentication error: {e}")
            raise ValueError("Invalid OpenAI API key. Please check your configuration.")
        except openai.RateLimitError as e:
            logger.warning(f"Rate limit exceeded: {e}")
            raise  # This will be retried by tenacity
        except openai.APIConnectionError as e:
            logger.warning(f"Connection error: {e}")
            raise  # This will be retried by tenacity
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise  # This will be retried by tenacity
        except Exception as e:
            logger.error(f"Unexpected error in chat completion: {e}")
            raise Exception(f"Unexpected error: {str(e)}")

    def generate_summary(self, text: str, max_length: int = 500) -> str:
        """
        Generate a summary of the given text.

        Args:
            text: Text to summarize
            max_length: Maximum length of summary in words

        Returns:
            Summarized text
        """
        prompt = f"Please provide a concise summary of the following text in no more than {max_length} words:\n\n{text}"
        messages = [{"role": "user", "content": prompt}]
        return self.chat_completion(messages, max_tokens=500)

    def generate_questions(self, text: str, num_questions: int = 5) -> List[str]:
        """
        Generate questions based on the given text.

        Args:
            text: Source text
            num_questions: Number of questions to generate

        Returns:
            List of generated questions
        """
        prompt = f"Generate {num_questions} thoughtful questions based on the following text:\n\n{text}"
        messages = [{"role": "user", "content": prompt}]
        response = self.chat_completion(messages, max_tokens=300)
        # Split response into individual questions
        questions = [q.strip() for q in response.split('\n') if q.strip() and not q.strip().startswith(('1.', '2.', '3.', '-', '*'))]
        return questions[:num_questions]

    def generate_flashcards(self, text: str, num_cards: int = 10) -> List[Dict[str, str]]:
        """
        Generate flashcards (Q&A pairs) from the given text.

        Args:
            text: Source text
            num_cards: Number of flashcards to generate

        Returns:
            List of dictionaries with 'question' and 'answer' keys
        """
        prompt = f"""Create {num_cards} flashcards from the following text. Format each flashcard as:
Q: [Question]
A: [Answer]

{text}"""
        messages = [{"role": "user", "content": prompt}]
        response = self.chat_completion(messages, max_tokens=1000)

        flashcards = []
        lines = response.split('\n')
        current_card = {}

        for line in lines:
            line = line.strip()
            if line.startswith('Q:'):
                if current_card:
                    flashcards.append(current_card)
                current_card = {'question': line[2:].strip(), 'answer': ''}
            elif line.startswith('A:'):
                current_card['answer'] = line[2:].strip()

        if current_card:
            flashcards.append(current_card)

        return flashcards[:num_cards]

    def load_prompt_template(self, template_name: str) -> Dict[str, Any]:
        """
        Load a prompt template from the prompts directory.

        Args:
            template_name: Name of the template file (without .json extension)

        Returns:
            Template dictionary
        """
        template_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', f'{template_name}.json')
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Prompt template '{template_name}' not found")

        with open(template_path, 'r') as f:
            return json.load(f)

    def parse_flashcard_response(self, response: str) -> List[Dict[str, str]]:
        """
        Parse flashcard response into structured format.

        Args:
            response: Raw response from AI

        Returns:
            List of flashcard dictionaries with 'question' and 'answer' keys
        """
        flashcards = []
        lines = response.split('\n')
        current_card = {}

        for line in lines:
            line = line.strip()
            if line.startswith('Q:') or line.startswith('Question:'):
                if current_card and 'question' in current_card:
                    flashcards.append(current_card)
                current_card = {'question': line.split(':', 1)[1].strip(), 'answer': ''}
            elif line.startswith('A:') or line.startswith('Answer:'):
                current_card['answer'] = line.split(':', 1)[1].strip()

        if current_card and 'question' in current_card:
            flashcards.append(current_card)

        return flashcards

    def parse_quiz_response(self, response: str) -> List[Dict[str, Any]]:
        """
        Parse quiz response into structured format.

        Args:
            response: Raw response from AI

        Returns:
            List of quiz question dictionaries
        """
        questions = []
        lines = response.split('\n')
        current_question = {}

        for line in lines:
            line = line.strip()
            if line.startswith('Question') and ':' in line:
                if current_question and 'question' in current_question:
                    questions.append(current_question)
                question_text = line.split(':', 1)[1].strip()
                current_question = {
                    'question': question_text,
                    'options': [],
                    'correct_answer': ''
                }
            elif line.startswith(('A)', 'B)', 'C)', 'D)')):
                current_question['options'].append(line[2:].strip())
            elif line.startswith('Correct:'):
                current_question['correct_answer'] = line.split(':', 1)[1].strip()

        if current_question and 'question' in current_question:
            questions.append(current_question)

        return questions

    def parse_concept_map_response(self, response: str) -> Dict[str, Any]:
        """
        Parse concept map response into structured format.

        Args:
            response: Raw response from AI

        Returns:
            Dictionary representing the concept map structure
        """
        # This is a simplified parser - in practice, you might want to use
        # more sophisticated parsing or ask the AI to return JSON
        lines = response.split('\n')
        concepts = []
        relationships = []

        for line in lines:
            line = line.strip()
            if line and not line.startswith('-') and not line.startswith('*'):
                # Assume main concepts are on their own lines
                concepts.append(line)
            elif line.startswith('-') or line.startswith('*'):
                # Assume relationships are marked with bullets
                relationships.append(line[1:].strip())

        return {
            'concepts': concepts,
            'relationships': relationships,
            'raw_response': response
        }

    def parse_summary_response(self, response: str) -> Dict[str, str]:
        """
        Parse summary response into structured format.

        Args:
            response: Raw response from AI

        Returns:
            Dictionary with summary components
        """
        # Simple parser - split by common section markers
        sections = {}
        current_section = 'main'
        lines = response.split('\n')

        for line in lines:
            line = line.strip()
            if line.lower().startswith(('key concepts:', 'main ideas:', 'summary:')):
                current_section = line.split(':')[0].lower().replace(' ', '_')
                sections[current_section] = line.split(':', 1)[1].strip() if ':' in line else ''
            elif line and current_section:
                if current_section not in sections:
                    sections[current_section] = line
                else:
                    sections[current_section] += ' ' + line

        return sections if sections else {'main': response}