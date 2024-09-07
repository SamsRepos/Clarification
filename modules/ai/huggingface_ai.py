from huggingface_hub import InferenceClient
from .ai import AI
import sys

class HuggingFaceAI(AI):
    def __init__(self, model_name, max_new_tokens, temperature, access_token):
        super().__init__(max_new_tokens, temperature)
        self.client = InferenceClient(
            model = model_name,
            token = access_token
        )

    def print_response(self):
        full_prompt = f"{self.prompt}\n\nResponse:"
        response_started = False
        for token in self.client.text_generation(
            prompt          = full_prompt,
            max_new_tokens  = self.max_new_tokens,
            temperature     = self.temperature,
            stream          = True,
            stop_sequences  = ["\n\nHuman:", "\n\nAssistant:", "\n\nFeedback:"]
        ):
            if token.strip() and token not in ["\n", " "]:
                response_started = True
            if not response_started:
                continue
            print(token, end='', flush=True)
