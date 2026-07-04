user_memory = {}

def get_user_memory(user_id: str):
    return user_memory.get(user_id, {})

def save_user_memory(user_id: str, goal: str):
    user_memory[user_id] = {
        "goal": goal
    }