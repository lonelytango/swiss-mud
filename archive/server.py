import socket
import threading
from room import Room
from player import Player

class MUDServer:
    def __init__(self, host='localhost', port=3001):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.players = {}
        self.rooms = self.create_world()

    def create_world(self):
        rooms = {
            '大堂': Room('紫风广场', '你正身处广场中央，无数奇人异士在此路过，熙来攘往的一个十字路口。'),
            '北大街': Room('北大街', '你正身处于北大街。'),
            '东大街': Room('东大街', '你正身处于东大街。')
        }
        rooms['大堂'].add_exit('north', rooms['北大街'])
        rooms['大堂'].add_exit('east', rooms['东大街'])
        rooms['北大街'].add_exit('south', rooms['大堂'])
        rooms['东大街'].add_exit('west', rooms['大堂'])
        return rooms

    def start(self):
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        print(f"Server started on {self.host}:{self.port}")

        while True:
            client, address = self.sock.accept()
            threading.Thread(target=self.handle_client, args=(client, address)).start()

    def handle_client(self, client, address):
        print(f"新链接自 {address}")
        client.send("欢迎来到紫风江湖，请输入你的名字：\n".encode())
        
        name = client.recv(1024).decode().strip()
        player = Player(name, client)
        self.players[client] = player
        self.move_player(player, self.rooms['大堂'])
        self.do_look(player)
        
        while True:
            try:
                message = client.recv(1024).decode().strip()
                if message.lower() == 'quit':
                    break
                self.process_command(player, message)
            except:
                break

        self.remove_player(player)

    def process_command(self, player, command):
        parts = command.lower().split()
        if not parts:
            return

        if parts[0] in ['look', 'l']:
            self.do_look(player)
        elif parts[0] in ['north', 'south', 'east', 'west', 'n', 's', 'e', 'w']:
            direction = parts[0]
            # Map shorthand to full direction names
            direction_mapping = {'n': 'north', 's': 'south', 'e': 'east', 'w': 'west'}
            full_direction = direction_mapping.get(direction, direction)
            self.do_move(player, full_direction)
        else:
            player.send_message(f"未知命令: {command}")

    def do_look(self, player):
        room = player.current_room
        player.send_message(f"你身处{room.name}")
        player.send_message(room.description)
        player.send_message("出口在: " + ", ".join(room.exits.keys()))
        if room.players:
            player.send_message("这里的玩家有: " + ", ".join(p.name for p in room.players if p != player))

    def do_move(self, player, direction):
        room = player.current_room
        if direction in room.exits:
            new_room = room.exits[direction]
            self.move_player(player, new_room)
            self.do_look(player)
        else:
            player.send_message(f"这个方向没有出口。")

    def move_player(self, player, new_room):
        if player.current_room:
            player.current_room.remove_player(player)
        player.current_room = new_room
        new_room.add_player(player)

    def remove_player(self, player):
        if player.client in self.players:
            print(f"{player.name}断线了。")
            if player.current_room:
                player.current_room.remove_player(player)
            del self.players[player.client]
        player.client.close()

if __name__ == "__main__":
    server = MUDServer()
    server.start()