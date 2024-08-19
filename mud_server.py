import socket
import threading
import uuid
from database import Database
from command_handler import CommandHandler
from player import Player
from room import Room

class MUDServer:
    def __init__(self, host='0.0.0.0', start_port=4000, max_port=4010):
        self.host = host
        self.start_port = start_port
        self.max_port = max_port
        self.port = None
        self.sock = None
        self.players = {}
        self.rooms = self.create_world()
        self.running = False
        self.db = Database()
        self.command_handler = CommandHandler(self)

    def create_world(self):
        rooms = {
            'Center': Room('Center', 'This is center of monke village, there are many monkes walking around.'),
            'North Street': Room('North Street', 'So many fancy dressed monke on the street, you are new here and not sure what to do.'),
            'East Street': Room('East Street', 'Plenty of banana trees planted on both side of the street, however you are not sure where to go.')
        }
        rooms['Center'].add_exit('north', rooms['North Street'])
        rooms['Center'].add_exit('east', rooms['East Street'])
        rooms['North Street'].add_exit('south', rooms['Center'])
        rooms['East Street'].add_exit('west', rooms['Center'])
        return rooms

    def find_available_port(self):
        for port in range(self.start_port, self.max_port + 1):
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.bind((self.host, port))
                self.port = port
                return True
            except socket.error:
                continue
        return False

    def start(self):
        if not self.find_available_port():
            print(f"Unable to find an available port between {self.start_port} and {self.max_port}")
            return

        self.sock.listen(5)
        print(f"Server started on {self.host}:{self.port}")
        print("Press Ctrl+C to stop the server.")

        self.running = True
        while self.running:
            client, address = self.sock.accept()
            threading.Thread(target=self.handle_client, args=(client, address)).start()

    def handle_client(self, client, address):
        print(f"New connection from {address}")
        client.send("Welcome to the MUD! Please log in or register.\n".encode('utf-8'))
        
        player_id = None
        try:
            authenticated = False
            while not authenticated and self.running:
                client.send("Enter 'login' or 'register': ".encode('utf-8'))
                choice = client.recv(1024).decode('utf-8').strip().lower()
                
                if choice == 'login':
                    player_id, authenticated = self.db.login(client)
                elif choice == 'register':
                    player_id, authenticated = self.db.register(client)
                else:
                    client.send("Invalid choice. Please try again.\n".encode('utf-8'))

            if not authenticated or player_id is None:
                client.close()
                return

            player = Player(self.db.get_username(player_id), client)
            self.players[player_id] = player
            self.db.load_player_data(player, self.rooms)
            self.move_player(player, player.current_room)
            player.send_message(f"Welcome back, {player.name}! You are in {player.current_room.name}.")
            
            while self.running:
                try:
                    message = client.recv(1024).decode('utf-8').strip()
                    if message.lower() == 'quit':
                        break
                    self.command_handler.handle(player, message)
                except ConnectionResetError:
                    break

        except Exception as e:
            print(f"Error handling client {address}: {str(e)}")
        finally:
            if player_id and player_id in self.players:
                player = self.players[player_id]
                self.db.save_player_data(player)
                self.remove_player(player_id)
            else:
                client.close()

    def move_player(self, player, new_room):
        if player.current_room:
            player.current_room.remove_player(player)
        player.current_room = new_room
        new_room.add_player(player)

    def remove_player(self, player_id):
        if player_id in self.players:
            self.db.remove_player_session(player_id)
            player = self.players[player_id]
            print(f"{player.name} has disconnected")
            if player.current_room:
                player.current_room.remove_player(player)
            player.client.close()
            del self.players[player_id]

    def stop(self):
        self.running = False
        print("Closing all client connections...")
        for player_id, player in list(self.players.items()):
            self.db.save_player_data(player)
            player.send_message("Server is shutting down. Your progress has been saved. Goodbye!")
            self.remove_player(player_id)
        print("Closing server socket...")
        if self.sock:
            self.sock.close()
        print("Server has been shut down.")