import socket
import threading
import pickle
import random
import time

class GameServer:
    def __init__(self, host='localhost', port=5555, max_rooms=5):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((host, port))
        self.server.listen()
        print(f"Server started on {host}:{port}")
        self.clients = {}
        self.rooms = {i: [] for i in range(max_rooms)}
        self.scores = {i: {} for i in range(max_rooms)}  # Track scores per room
        self.top_scores = {i: 0 for i in range(max_rooms)}

    def handle_client(self, conn, addr, room_id):
        print(f"New connection from {addr} in Room {room_id}")
        conn.send(pickle.dumps({"message": "Welcome to the Snake Battle Game!"}))

        player_snake = [(random.randint(0, 19), random.randint(0, 19))]  # Random spawn
        self.clients[conn] = {"snake": player_snake, "score": 0}

        try:
            while True:
                try:
                    data = conn.recv(4096)
                    if not data:
                        break
                    # Packet loss detection and recovery exception handling
                    try:
                        data = pickle.loads(data)
                    except (pickle.UnpicklingError, EOFError):
                        print(f"Packet loss detected from {addr}. Ignoring corrupt data.")
                        continue  # Ignore the data and process the next packet

                    self.update_game_state(conn, data, room_id)
                except (ConnectionResetError, BrokenPipeError):
                    # Client disconnection exception handling
                    print(f"Connection lost with {addr}. Handling disconnection.")
                    break
                except socket.timeout:
                    # Client response timeout exception handling
                    print(f"Timeout from {addr}. Client may have high latency.")
                    continue  # Wait again when timeout occurs

        finally:
            self.disconnect_client(conn, addr, room_id)

    def update_game_state(self, conn, data, room_id):
        if "move" in data:
            self.clients[conn]["snake"] = data["move"]
        if "score" in data:
            self.clients[conn]["score"] = data["score"]
            # Update top score
            self.top_scores[room_id] = max(self.top_scores[room_id], self.clients[conn]["score"])
        self.broadcast_game_state(room_id)

    def broadcast_game_state(self, room_id):
        game_state = {
            "snakes": {conn.fileno(): self.clients[conn]["snake"] for conn in self.rooms[room_id]},
            "scores": {conn.fileno(): self.clients[conn]["score"] for conn in self.rooms[room_id]},
            "top_score": self.top_scores[room_id],  # Include the top score in the state
        }
        for client in self.rooms[room_id]:
            try:
                client.send(pickle.dumps(game_state))
            except (socket.error, ConnectionResetError):
                print("Failed to send data to a client. Removing the client.")
                self.disconnect_client(client)


    def disconnect_client(self, conn, addr=None, room_id=None):
        if addr:
            print(f"Client {addr} disconnected")
        conn.close()
        if conn in self.rooms[room_id]:
            self.rooms[room_id].remove(conn)
        if conn in self.clients:
            del self.clients[conn]

    def start(self):
        while True:
            conn, addr = self.server.accept()
            conn.settimeout(10)  # Set client response latency
            conn.send(pickle.dumps({"rooms": list(self.rooms.keys())}))
            room_id = pickle.loads(conn.recv(4096)).get("room_id", 0)
            try:
                if room_id in self.rooms:
                    self.rooms[room_id].append(conn)
                    thread = threading.Thread(target=self.handle_client, args=(conn, addr, room_id))
                    thread.start()
                else:
                    conn.close()
            except (EOFError, pickle.UnpicklingError):
                # Initial data processing failure exception handling
                print(f"Invalid data received from {addr}. Closing connection.")
                conn.close()

if __name__ == "__main__":
    server = GameServer()
    server.start()
