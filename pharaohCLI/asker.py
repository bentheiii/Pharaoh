class Asker:
    """a class that asks y/n questions and remembers the previous answer"""
    def __init__(self):
        self.prev = None

    def small_prompt(self):
        """
        get a prompt for potential answers, including an enter prompt if a default exists.
        """
        if self.prev:
            return f'[y/n/<enter> for {self.prev}]'
        return '[y/n]'

    def ask(self, rule, prompt):
        """
        ask a question
        :param rule: if this is entered, the input is skipped and the value is returned automatically
        :param prompt: the description of the suggestion
        :return: whether the user accepted or rejected the suggestion
        """
        if rule == 'y':
            print(prompt+'? y')
            return True
        if rule == 'n':
            print(prompt+'? n')
            return False

        response = input(f'Suggestion: {prompt}, accept? {self.small_prompt()}: ').lower()
        while True:
            if response == 'n':
                self.prev = 'n'
                return False
            elif response == 'y':
                self.prev = 'y'
                return True
            elif self.prev and response == '':
                return self.prev == 'y'
            response = input(f'not recognized, {self.small_prompt()}: ')
