import sqlite3
import hashlib
import uuid

class Database:
    def __init__(self, db_name='mud_database.db'):
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
                return username, True
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
        return None, False

    def save_player_data(self, player):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            inventory = ','.join(player.inventory)
            cursor.execute('''
                INSERT OR REPLACE INTO player_data (username, room, inventory)
                VALUES (?, ?, ?)
            ''', (player.name, player.current_room.name, inventory))
            conn.commit()

    def load_player_data(self, player, rooms):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT room, inventory FROM player_data WHERE username = ?', (player.name,))
            result = cursor.fetchone()
            if result:
                room_name, inventory = result
                player.current_room = rooms[room_name]
                player.inventory = inventory.split(',') if inventory else []
            else:
                player.current_room = rooms['Center']  # Default room
                player.inventory = []