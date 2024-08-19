import socket
import threading
import signal
import sys
import hashlib
import sqlite3
import uuid
from room import Room
from player import Player

class MUDServer:
    def __init__(self, host='0.0.0.0', start_port=4000, max_port=4010, db_name='mud_database.db'):
        self.host = host
        self.start_port = start_port
        self.max_port = max_port
        self.port = None
        self.sock = None
        # self.port = port
        # self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.players = {}
        self.rooms = self.create_world()
        self.running = False
        self.commands = {
            'look': self.do_look,
            'l': self.do_look,
            'north': lambda player: self.do_move(player, 'north'),
            'w': lambda player: self.do_move(player, 'north'),
            'south': lambda player: self.do_move(player, 'south'),
            's': lambda player: self.do_move(player, 'south'),
            'east': lambda player: self.do_move(player, 'east'),
            'd': lambda player: self.do_move(player, 'east'),
            'west': lambda player: self.do_move(player, 'west'),
            'a': lambda player: self.do_move(player, 'west'),
            'quit': self.do_quit,
            'q': self.do_quit,
            'help': self.do_help,
            'h': self.do_help,
            'say': self.do_say,
            'inventory': self.do_inventory,
            'i': self.do_inventory,
        }
        self.db_name = db_name
        self.init_database()

    def init_database(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password TEXT NOT NULL
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS player_data (
                    username TEXT PRIMARY KEY,
                    room TEXT NOT NULL,
                    inventory TEXT
                )
            ''')
            conn.commit()

    def load_player_data(self, player):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT room, inventory FROM player_data WHERE username = ?', (player.name,))
            result = cursor.fetchone()
            if result:
                room_name, inventory = result
                player.current_room = self.rooms[room_name]
                player.inventory = inventory.split(',') if inventory else []
            else:
                player.current_room = self.rooms['Center']
                player.inventory = []

    def save_player_data(self, player):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            inventory = ','.join(player.inventory)
            cursor.execute('''
                INSERT OR REPLACE INTO player_data (username, room, inventory)
                VALUES (?, ?, ?)
            ''', (player.name, player.current_room.name, inventory))
            conn.commit()

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

    def start(self):
        if not self.find_available_port():
            print(f"Unable to find an available port between {self.start_port} and {self.max_port}")
            return

        self.sock.listen(5)
        print(f"Server started on {self.host}:{self.port}")
        print("Press Ctrl+C to stop the server.")

        self.running = True
        while self.running:
            try:
                self.sock.settimeout(1.0)  # Set a timeout for socket.accept()
                client, address = self.sock.accept()
                threading.Thread(target=self.handle_client, args=(client, address)).start()
            except socket.timeout:
                continue  # This allows checking self.running periodically
            except KeyboardInterrupt:
                print("\nShutting down the server...")
                self.stop()

    def stop(self): 
        self.running = False
        print("Closing all client connections...")
        for player_id, player in list(self.players.items()):
            self.save_player_data(player)
            player.send_message("Server is shutting down. Your progress has been saved. Goodbye!")
            self.remove_player(player_id)
        print("Closing server socket...")
        if self.sock:
            self.sock.close()
        print("Server has been shut down.")

    def handle_client(self, client, address):
        try:
            print(f"New connection from {address}")
            client.send("Welcome to the MUD! Please log in or register.\n".encode('utf-8'))
            
            authenticated = False
            while not authenticated and self.running:
                client.send("Enter 'login' or 'register': ".encode('utf-8'))
                choice = client.recv(1024).decode('utf-8').strip().lower()
                
                if choice == 'login':
                    player_id, authenticated = self.login(client)
                elif choice == 'register':
                    player_id, authenticated = self.register(client)
                else:
                    client.send("Invalid choice. Please try again.\n".encode('utf-8'))

            if not authenticated or player_id is None:
                client.close()
                return

            player = self.players[player_id]
            self.load_player_data(player)
            self.move_player(player, player.current_room)
            player.send_message(f"Welcome back, {player.name}! You are in {player.current_room.name}.")
            
            while self.running:
                try:
                    client.settimeout(1.0)
                    message = client.recv(1024).decode('utf-8').strip()
                    if message.lower() == 'quit':
                        break
                    self.process_command(player, message)
                except socket.timeout:
                    continue
                except ConnectionResetError:
                    break
                except Exception as e:
                    print(f"Error processing command for {player.name}: {str(e)}")

        except Exception as e:
            print(f"Error handling client {address}: {str(e)}")
        # finally:
        #     if player_id and player_id in self.players:
        #         player = self.players[player_id]
        #         self.save_player_data(player)
        #         self.remove_player(player_id)
        #     else:
        #         client.close()

    def login(self, client):
        client.send("Username: ".encode('utf-8'))
        username = client.recv(1024).decode('utf-8').strip()
        client.send("Password: ".encode('utf-8'))
        password = client.recv(1024).decode('utf-8').strip()
        
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT password FROM users WHERE username = ?', (username,))
            result = cursor.fetchone()
            
            if result and result[0] == hashed_password:
                client.send("Login successful!\n".encode('utf-8'))
                player_id = str(uuid.uuid4())
                player = Player(username, client)
                self.players[player_id] = player
                return player_id, True
            else:
                client.send("Invalid username or password.\n".encode('utf-8'))
                return None, False

    def register(self, client):
        client.send("Choose a username: ".encode('utf-8'))
        username = client.recv(1024).decode('utf-8').strip()
        
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT username FROM users WHERE username = ?', (username,))
            if cursor.fetchone():
                client.send("Username already exists. Please try again.\n".encode('utf-8'))
                return None, False
        
        client.send("Choose a password: ".encode('utf-8'))
        password = client.recv(1024).decode('utf-8').strip()
        
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
            conn.commit()
        
        client.send("Registration successful! You can now log in.\n".encode('utf-8'))
        return None, False  # Return False to prompt for login

    def process_command(self, player, command):
        parts = command.lower().split()
        if not parts:
            return

        command = parts[0]
        args = parts[1:]

        if command in self.commands:
            if command in ['say']:
                return self.commands[command](player, ' '.join(args))
            else:
                return self.commands[command](player)
        else:
            player.send_message(f"Unknown command: {command}. Type 'help' for a list of commands.")
        return True

    def do_look(self, player):
        room = player.current_room
        player.send_message(f"You are in {room.name}")
        player.send_message(room.description)
        player.send_message("Exits: " + ", ".join(room.exits.keys()))
        if room.players:
            player.send_message("Monkes here: " + ", ".join(p.name for p in room.players if p != player))

    def do_move(self, player, direction):
        current_room = player.current_room
        if direction in current_room.exits:
            new_room = current_room.exits[direction]
            current_room.broadcast(f"{player.name} has left the room.", exclude=player)
            self.move_player(player, new_room)
            new_room.broadcast(f"{player.name} has entered the room.", exclude=player)
            player.send_message(f"You have moved to {new_room.name}.")
            self.do_look(player)
        else:
            player.send_message(f"There's no exit in that direction.")

    def do_quit(self, player):
        player.send_message("Goodbye!")
        return False  # Signal to close the connection

    def do_help(self, player):
        help_text = """
Available commands:
- look (l): Look around the room
- north (w), south (s), east (d), west (a): Move in a direction
- say <message>: Say something to everyone in the room
- inventory (i): Check your inventory
- help (h): Show this help message
- quit (q): Quit the game
        """
        player.send_message(help_text)

    def do_say(self, player, message):
        if not message:
            player.send_message("Say what?")
            return
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

    def move_player(self, player, new_room):
        if player.current_room:
            player.current_room.remove_player(player)
        player.current_room = new_room
        new_room.add_player(player)

    def remove_player(self, player_id):
        if player_id in self.players:
            player = self.players[player_id]
            print(f"{player.name} has disconnected")
            if player.current_room:
                player.current_room.remove_player(player)
            player.client.close()
            del self.players[player_id]

def signal_handler(sig, frame):
    print("\nCtrl+C pressed. Stopping the server...")
    if server:
        server.stop()
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    server = MUDServer()
    server.start()