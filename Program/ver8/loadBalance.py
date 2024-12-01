import socket
import threading
import random
import time
import pickle  # pickle 모듈 추가

class LoadBalancer:
    def __init__(self, server_addresses):
        """
        로드 밸런서 초기화.
        :param server_addresses: 분산 서버의 (IP, 포트) 목록
        """
        self.server_addresses = server_addresses  # 서버 주소 목록
        self.server_status = {address: True for address in server_addresses}  # 서버 상태 관리
        self.server_clients = {address: [] for address in server_addresses}  # 서버별 클라이언트 관리

    def health_check(self):
        """
        서버 상태를 주기적으로 확인하여 비정상 서버를 제외.
        """
        while True:
            for address in self.server_addresses:
                is_alive = self.ping_server(address)  # 서버 상태 확인

                if is_alive and not self.server_status[address]:
                    print(f"Server {address} has reconnected.")  # 서버 재연결 메시지 출력
                elif not is_alive and self.server_status[address]:
                    print(f"Server {address} is down.")
                    self.close_clients_of_server(address)  # 서버 다운 시 연결된 클라이언트 종료

                self.server_status[address] = is_alive
            
            time.sleep(5)  # 5초마다 상태 확인

    def close_clients_of_server(self, server_address):
        """
        특정 서버에 연결된 모든 클라이언트 연결 종료.
        """
        if server_address in self.server_clients:
            clients = self.server_clients[server_address]
            for client in clients:
                threading.Thread(target=self.close_client_with_countdown, args=(client,)).start()
            self.server_clients[server_address] = []  # 클라이언트 목록 초기화

    def close_client_with_countdown(self, client_conn):
        """
        클라이언트를 5초 카운트다운 후 종료.
        """
        try:
            # 메시지를 pickle로 직렬화하여 전송
            message = {"message": "Server is down. Connection will close in 5 seconds."}
            client_conn.sendall(pickle.dumps(message))
            for i in range(5, 0, -1):
                time.sleep(1)
                try:
                    countdown_message = {"message": f"{i}..."}
                    client_conn.sendall(pickle.dumps(countdown_message))
                except socket.error:
                    break  # 클라이언트가 닫힌 경우 루프 종료
            final_message = {"message": "Connection closed."}
            client_conn.sendall(pickle.dumps(final_message))
        except socket.error:
            pass  # 클라이언트 연결이 이미 닫힌 경우 예외 무시
        finally:
            client_conn.close()

    def ping_server(self, address):
        """
        서버의 상태를 확인.
        :param address: 서버 주소 (IP, Port)
        :return: True(정상), False(비정상)
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(2)  # 타임아웃 설정
                sock.connect(address)
                sock.sendall(b'PING')  # 하트비트 메시지 전송
                response = sock.recv(1024)
                return response == b'PONG'  # 서버에서 PONG 응답 확인
        except (socket.error, socket.timeout):
            return False

    def get_next_server(self):
        """
        클라이언트를 할당할 다음 서버를 가져옵니다.
        :return: 선택된 서버 주소
        """
        # 활성화된 서버 중 랜덤으로 선택
        active_servers = [server for server, status in self.server_status.items() if status]
        if not active_servers:
            return None

        target_server = random.choice(active_servers)

        # 특정 서버에 클라이언트가 과도하게 몰린 경우 부하 분산
        avg_clients = sum(len(self.server_clients[server]) for server in active_servers) / len(active_servers)
        if len(self.server_clients[target_server]) > avg_clients * 1.5:  # 과도한 부하 기준
            target_server = min(active_servers, key=lambda server: len(self.server_clients[server]))
            print(f"Reassigning to least loaded server: {target_server}")
        return target_server

    def start(self, host='localhost', port=8080):
        """
        로드 밸런서를 실행하여 클라이언트 요청 처리.
        :param host: 로드 밸런서가 수신할 IP
        :param port: 로드 밸런서가 수신할 포트
        """
        balancer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        balancer_socket.bind((host, port))
        balancer_socket.listen()
        print(f"Load Balancer started on {host}:{port}")

        # 서버 상태 확인 쓰레드 실행
        threading.Thread(target=self.health_check, daemon=True).start()

        while True:
            # 클라이언트 연결 수락
            client_conn, client_addr = balancer_socket.accept()
            print(f"Client connected: {client_addr}")

            # 서버 선택
            target_server = self.get_next_server()
            if not target_server:
                print("No active servers available. Closing client connection.")
                client_conn.close()
                continue

            print(f"Forwarding client {client_addr} to server {target_server}")

            # 클라이언트 연결을 서버에 매핑
            self.server_clients[target_server].append(client_conn)

            # 클라이언트를 서버로 전달하는 쓰레드 생성
            threading.Thread(target=self.redirect_client, args=(client_conn, target_server)).start()

    def redirect_client(self, client_conn, target_server):
        """
        클라이언트와 서버 간 직접 연결 설정.
        """
        try:
            # 서버와 연결
            server_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_conn.connect(target_server)

            # 클라이언트를 서버로 직접 연결
            self.forward(client_conn, server_conn)

        except ConnectionRefusedError:
            print(f"Connection to server {target_server} failed. Closing client connection.")
            self.close_client_with_countdown(client_conn)

    def forward(self, client_conn, server_conn):
        """
        클라이언트와 서버 간의 직접 통신을 설정.
        """
        try:
            # 서버와 클라이언트 간 양방향 데이터 전송
            threading.Thread(target=self.transfer, args=(client_conn, server_conn)).start()
            self.transfer(server_conn, client_conn)
        finally:
            client_conn.close()
            server_conn.close()

    def transfer(self, source_conn, destination_conn):
        """
        데이터 전송 처리.
        """
        try:
            while True:
                data = source_conn.recv(4096)
                if not data:  # 데이터가 없으면 연결 종료
                    break
                destination_conn.sendall(data)
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
            print("Connection between client and server was interrupted.")
        finally:
            source_conn.close()
            destination_conn.close()

if __name__ == "__main__":
    # 사용할 서버 주소 (IP, 포트)
    server_addresses = [
        ('localhost', 5555),  # 첫 번째 게임 서버
        ('localhost', 5556),  # 두 번째 게임 서버
        ('localhost', 5557)   # 세 번째 게임 서버
    ]
    balancer = LoadBalancer(server_addresses)
    balancer.start()  # 로드 밸런서 실행
