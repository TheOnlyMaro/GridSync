class GridGame:
    def __init__(self, rows=20, cols=20):
        self.rows = rows
        self.cols = cols
        self.grid = [[0 for _ in range(cols)] for _ in range(rows)]
        self.actions = []

    def apply_action(self, player_id, row, col):
        if 0 <= row < self.rows and 0 <= col < self.cols:
            self.grid[row][col] = player_id
            self.actions.append((row, col, player_id))
            return True
        return False

    def get_recent_actions(self, limit=20):
        return self.actions[-limit:] if len(self.actions) > limit else list(self.actions)

    def clear_actions(self):
        self.actions.clear()
