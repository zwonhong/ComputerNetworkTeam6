import socket
import threading

# 로드 밸런서 설정
HOST = "0.0.0.0"
PORT = 9090
SERVERS = [("127.0.0.1", 8080)]  # 서버 리스트

server_index = 0
lock = threading.Lock()

# 서버 선택 함수
def get_next_server():
    global server_index
    with lock:
        server = SERVERS[server_index]
        server_index = (server_index + 1) % len(SERVERS)
    return server

# 클라이언트 처리 함수
def handle_client(client_socket):
    server_address = get_next_server()
    print(f"Forwarding client to {server_address}")
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.connect(server_address)

    threading.Thread(target=forward_data, args=(client_socket, server_socket)).start()
    threading.Thread(target=forward_data, args=(server_socket, client_socket)).start()

# 데이터 전달 함수
def forward_data(source, destination):
    try:
        while True:
            data = source.recv(4096)
            if not data:
                break
            destination.sendall(data)
    except ConnectionResetError:
        pass
    finally:
        source.close()
        destination.close()

# 로드 밸런서 실행 함수
def start_load_balancer():
    load_balancer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    load_balancer_socket.bind((HOST, PORT))
    load_balancer_socket.listen()
    print(f"Load Balancer is running on {HOST}:{PORT}")

    while True:
        client_socket, address = load_balancer_socket.accept()
        print(f"New connection from {address}")
        threading.Thread(target=handle_client, args=(client_socket,)).start()

if __name__ == "__main__":
    start_load_balancer()
