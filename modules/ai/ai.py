# Base AI interaction class
class AI:
    def __init__(self, max_new_tokens, temperature):
        self.prompt          = ""
        self.max_new_tokens  = max_new_tokens
        self.temperature     = temperature

    def add_to_prompt(self, new_content):
        self.prompt += new_content + "\n"

    def clear_prompt(self):
        self.prompt = ""

    def print_response(self):
        raise NotImplementedError("Subclasses should implement this method")
