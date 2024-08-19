class Room:
    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.exits = {}
        self.players = set()  # Using a set for efficient player management

    def add_exit(self, direction, room):
        self.exits[direction] = room

    def remove_player(self, player):
        self.players.discard(player)  # Using discard instead of remove

    def add_player(self, player):
        self.players.add(player)

    def get_players(self):
        return [player.name for player in self.players]

    def broadcast(self, message, exclude=None):
        for player in self.players:
            if player != exclude:
                player.send_message(message)