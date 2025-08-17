import logging

logger = logging.getLogger(__name__)


class UserStateManager:
    def __init__(self):
        self.states = {}

    def set_state(self, user_id, step, data=None):
        self.states[user_id] = {
            'step': step,
            'data': data or {},
            'chat_id': None
        }

    def get_state(self, user_id):
        return self.states.get(user_id)

    def update_state(self, user_id, step=None, data=None):
        if user_id not in self.states:
            return

        if step:
            self.states[user_id]['step'] = step
        if data:
            self.states[user_id]['data'].update(data)

    def clear_state(self, user_id):
        if user_id in self.states:
            del self.states[user_id]