import socket
import threading
import pickle
import random

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

    def handle_client(self, conn, addr):
        """클라이언트 요청 처리"""
        try:
            # 데이터 확인 (하트비트 요청 구분)
            initial_data = conn.recv(1024)
            if initial_data == b'PING':  # 하트비트 요청 처리
                conn.sendall(b'PONG')
                conn.close()
                return

            # 일반 클라이언트 연결 처리
            print(f"Client connected: {addr}")
            self.clients[conn] = {"snake": [(random.randint(0, 19), random.randint(0, 19))], "score": 0}

            while True:
                data = conn.recv(4096)
                if not data:
                    break
                message = pickle.loads(data)  # 클라이언트 데이터 역직렬화
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
            self.top_score = max(self.top_score, data["score"])  # 최고 점수 갱신

        self.broadcast_game_state()

    def broadcast_game_state(self):
        """현재 게임 상태를 모든 클라이언트에 전송"""
        game_state = {
            "snakes": {conn.fileno(): self.clients[conn]["snake"] for conn in self.clients},
            "scores": {conn.fileno(): self.clients[conn]["score"] for conn in self.clients},
            "top_score": self.top_score
        }
        for client in self.clients:
            try:
                client.send(pickle.dumps(game_state))
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

    # 포트 번호를 인자로 받아 다중 서버 실행 가능
    parser = argparse.ArgumentParser(description="Game Server")
    parser.add_argument('--port', type=int, default=5555, help='Port to run the server on')
    args = parser.parse_args()

    server = GameServer(port=args.port)
    server.start()
