class CalculatorException(Exception):
    def __init__(self, title, message):
        self.title = title
        self.message = message
