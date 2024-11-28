Python 3.10.5 (tags/v3.10.5:f377153, Jun  6 2022, 16:14:13) [MSC v.1929 64 bit (AMD64)] on win32
Type "help", "copyright", "credits" or "license()" for more information.
import socket
import threading
import pickle
import random
import pygame

# 파이게임 초기화
pygame.init()
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
size = [400, 440]
screen = pygame.display.set_mode(size)
pygame.display.set_caption("Multiplayer Snake Game")
FONT = pygame.font.Font(None, 36)
clock = pygame.time.Clock()

# 키보드 방향키와 실제 방향 연결
KEY_DIRECTION = {
    pygame.K_UP: 'N',
    pygame.K_DOWN: 'S',
    pygame.K_LEFT: 'W',
    pygame.K_RIGHT: 'E',
}

class GameServer:
    def __init__(self, host='localhost', port=5555, max_rooms=3):
        """게임 서버 초기화"""
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((host, port))
        self.server.listen()
        print(f"Server started on {host}:{port}")
        self.clients = {}  # 클라이언트 목록
        self.rooms = {i: [] for i in range(max_rooms)}
        self.scores = {}  # 점수 목록
        self.top_score = 0  # 최고 점수
        self.apples = [(random.randint(0, 19), random.randint(0, 19)) for _ in range(5)]  # 초기 사과 위치

    def handle_client(self, conn, addr):
        """클라이언트 요청 처리"""
        try:
            initial_data = conn.recv(1024)
            if initial_data == b'PING':
                conn.sendall(b'PONG')
                conn.close()
                return

            print(f"Client connected: {addr}")
            self.clients[conn] = {"snake": [(random.randint(0, 19), random.randint(0, 19))], "score": 0}

            while True:
                data = conn.recv(4096)
                if not data:
                    break
                message = pickle.loads(data)
                if "chat" in message:
                    self.broadcast_chat_message(conn, message["chat"])
                else:
                    self.update_game_state(conn, message)
        except (ConnectionResetError, EOFError):
            print(f"Client disconnected: {addr}")
        finally:
            self.disconnect_client(conn)

    def update_game_state(self, conn, data):
        """게임 상태 업데이트"""
        if "move" in data:
            self.clients[conn]["snake"] = data["move"]
        if "score" in data:
            self.clients[conn]["score"] = data["score"]
            self.top_score = max(self.top_score, data["score"])

        head = self.clients[conn]["snake"][0]
        new_apples = []
        for apple in self.apples:
            if head == apple:
                self.clients[conn]["score"] += 1
                self.top_score = max(self.top_score, self.clients[conn]["score"])
            else:
                new_apples.append(apple)
        while len(new_apples) < 5:
            new_apples.append((random.randint(0, 19), random.randint(0, 19)))
        self.apples = new_apples

        self.broadcast_game_state()

    def broadcast_game_state(self):
        """현재 게임 상태를 모든 클라이언트에 전송"""
        game_state = {
            "snakes": {conn.fileno(): self.clients[conn]["snake"] for conn in self.clients},
            "scores": {conn.fileno(): self.clients[conn]["score"] for conn in self.clients},
            "top_score": self.top_score,
            "apples": self.apples
        }
        for client in self.clients:
            try:
                client.send(pickle.dumps(game_state))
            except (ConnectionResetError, EOFError):
                self.disconnect_client(client)

    def broadcast_chat_message(self, sender_conn, message):
        """채팅 메시지를 모든 클라이언트에 전송"""
        chat_message = {"chat": f"Client {sender_conn.fileno()}: {message}"}
        for client in self.clients:
            if client != sender_conn:  # 메시지를 보낸 클라이언트 제외
                try:
                    client.send(pickle.dumps(chat_message))
                except (ConnectionResetError, EOFError):
                    self.disconnect_client(client)

    def disconnect_client(self, conn):
        """클라이언트 연결 종료 처리"""
        if conn in self.clients:
            del self.clients[conn]
        conn.close()

    def start(self):
        """서버 시작"""
        while True:
            conn, addr = self.server.accept()
            threading.Thread(target=self.handle_client, args=(conn, addr)).start()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Game Server")
    parser.add_argument('--port', type=int, default=5555, help='Port to run the server on')
    args = parser.parse_args()

    server = GameServer(port=args.port)
    server.start()
