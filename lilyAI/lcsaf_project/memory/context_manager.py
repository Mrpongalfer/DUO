class ContextManager:
    def __init__(self):
        self.contexts = {}

    def get_context(self, user):
        return self.contexts.get(user, "")

    def update_context(self, user, prompt, response):
        self.contexts[user] = (
            f"{self.contexts.get(user, '')}\nUser: {prompt}\nLily: {response}"
        )
