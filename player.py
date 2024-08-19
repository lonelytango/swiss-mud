class Player:
    def __init__(self, name, client):
        self.name = name
        self.client = client
        self.current_room = None
        self.inventory = []

    def send_message(self, message):
        self.client.send(f"{message}\n".encode())