class CommandHandler:
    def __init__(self, server):
        self.server = server
        self.commands = {
            'look': self.do_look,
            'move': self.do_move,
            'say': self.do_say,
            'inventory': self.do_inventory,
            'help': self.do_help,
        }

    def handle(self, player, command):
        parts = command.lower().split()
        if not parts:
            return
        
        command = parts[0]
        args = parts[1:]

        if command in self.commands:
            self.commands[command](player, *args)
        else:
            player.send_message(f"Unknown command: {command}. Type 'help' for a list of commands.")

    def do_look(self, player):
        room = player.current_room
        player.send_message(f"You are in {room.name}")
        player.send_message(room.description)
        player.send_message("Exits: " + ", ".join(room.exits.keys()))
        if room.players:
            player.send_message("Players here: " + ", ".join(p.name for p in room.players if p != player))

    def do_move(self, player, direction):
        room = player.current_room
        if direction in room.exits:
            new_room = room.exits[direction]
            self.server.move_player(player, new_room)
            player.send_message(f"You have moved to {new_room.name}.")
            self.do_look(player)
        else:
            player.send_message(f"There's no exit in that direction.")

    def do_say(self, player, *message):
        if not message:
            player.send_message("Say what?")
            return
        message = ' '.join(message)
        for other in player.current_room.players:
            if other != player:
                other.send_message(f"{player.name} says: {message}")
        player.send_message(f"You say: {message}")

    def do_inventory(self, player):
        if not player.inventory:
            player.send_message("Your inventory is empty.")
        else:
            player.send_message("You are carrying:")
            for item in player.inventory:
                player.send_message(f"- {item}")

    def do_help(self, player):
        help_text = """
Available commands:
- look: Look around the room
- move <direction>: Move in a direction (north, south, east, west)
- say <message>: Say something to everyone in the room
- inventory: Check your inventory
- help: Show this help message
- quit: Quit the game
        """
        player.send_message(help_text)