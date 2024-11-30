import socket
import threading
import pickle

# 서버 설정
HOST = "0.0.0.0"
PORT = 8080

clients = {}  # 클라이언트 소켓 저장
snakes = {}  # 각 클라이언트의 뱀 위치
scores = {}  # 각 클라이언트의 점수
color_index = 0  # 색상 인덱스
top_score = 0  # 전체 최고 점수

lock = threading.Lock()

# 클라이언트 처리 함수
def handle_client(client_socket, address, client_id):
    global color_index, top_score
    print(f"New connection from {address}")
    try:
        # 클라이언트에 색상 인덱스 전송
        client_socket.send(str(color_index).encode())
        with lock:
            color_index += 1

        while True:
            data = client_socket.recv(4096)
            if not data:
                break

            # 클라이언트로부터 데이터 수신
            client_data = pickle.loads(data)
            snakes[client_id] = client_data.get("move", [])
            scores[client_id] = client_data.get("score", 0)

            # 최고 점수 업데이트
            with lock:
                top_score = max(top_score, scores[client_id])

            # 다른 플레이어 정보 전송
            game_state = {
                "snakes": {cid: s for cid, s in snakes.items() if cid != client_id},
                "top_score": top_score,
            }
            client_socket.sendall(pickle.dumps(game_state))
    except (ConnectionResetError, EOFError):
        print(f"Client {address} disconnected.")
    finally:
        with lock:
            if client_id in snakes:
                del snakes[client_id]
            if client_id in scores:
                del scores[client_id]
        client_socket.close()

# 서버 실행 함수
def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print(f"Server is running on {HOST}:{PORT}")

    client_id = 0
    while True:
        client_socket, address = server_socket.accept()
        with lock:
            clients[client_id] = client_socket
        threading.Thread(target=handle_client, args=(client_socket, address, client_id)).start()
        client_id += 1

if __name__ == "__main__":
    start_server()
