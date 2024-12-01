import socket
import threading
import random
import time
import pickle  # pickle 모듈 추가
from collections import deque

class LoadBalancer:
    def __init__(self, server_addresses):
        """
        로드 밸런서 초기화.
        :param server_addresses: 분산 서버의 (IP, 포트) 목록
        """
        self.server_addresses = server_addresses  # 서버 주소 목록
        self.server_status = {address: True for address in server_addresses}  # 서버 상태 관리
        self.server_clients = {address: [] for address in server_addresses}  # 서버별 클라이언트 관리
        self.current_server_index = 0  # Round-Robin용 서버 인덱스
        self.client_queue = deque()  # 클라이언트 대기열

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

                # 상태 업데이트
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

    def is_socket_alive(sock):
        """
        소켓이 유효한지 확인.
        """
        try:
            sock.send(b'')  # 빈 데이터를 전송하여 상태 확인
            return True
        except socket.error:
            return False

    def assign_client_to_server(self, client_conn):
        """
        클라이언트를 서버에 할당하거나 대기열에 추가.
        """
        for _ in range(len(self.server_addresses)):  # 모든 서버를 순회
            current_server = self.server_addresses[self.current_server_index]

            # 활성화된 서버 중 클라이언트가 4명 미만인 경우 선택
            if self.server_status[current_server] and len(self.server_clients[current_server]) < 4:
                print(f"Assigning client to server {current_server}")
                self.server_clients[current_server].append(client_conn)
                threading.Thread(target=self.redirect_client, args=(client_conn, current_server)).start()
                return

            # 다음 서버로 이동
            self.current_server_index = (self.current_server_index + 1) % len(self.server_addresses)

        # 모든 서버가 꽉 찬 경우 대기열에 추가
        print("All servers are full. Adding client to the queue.")
        self.client_queue.append(client_conn)

    def process_waiting_clients(self):
        """
        대기열에서 클라이언트를 서버로 할당.
        """
        while True:
            time.sleep(1)  # 1초마다 대기열 확인
            if self.client_queue:
                for server_address in self.server_addresses:
                    if self.server_status[server_address] and len(self.server_clients[server_address]) < 4:
                        client_conn = self.client_queue.popleft()
                        print(f"Assigning queued client to server {server_address}")
                        self.server_clients[server_address].append(client_conn)
                        threading.Thread(target=self.redirect_client, args=(client_conn, server_address)).start()
                        break
    
    def monitor_server_load(self):
        """
        서버의 클라이언트 상태를 주기적으로 확인하여 비어 있는 서버에 대기열의 클라이언트를 할당.
        """
        while True:
            time.sleep(1)  # 1초마다 상태 확인
            
            for server_address in self.server_addresses:
                # 서버가 활성화되고 클라이언트 공간이 남아있는 경우
                if self.server_status[server_address] and len(self.server_clients[server_address]) < 4:
                    while self.client_queue and len(self.server_clients[server_address]) < 4:
                        # 대기열에서 클라이언트를 가져옴
                        client_conn = self.client_queue.popleft()

                        # 소켓 유효성 확인
                        if not self.is_socket_alive(client_conn):
                            print("Client socket is no longer valid. Skipping.")
                            continue

                        print(f"Assigning queued client to available server {server_address}")
                        self.server_clients[server_address].append(client_conn)
                        try:
                            threading.Thread(target=self.redirect_client, args=(client_conn, server_address)).start()
                        except Exception as e:
                            print(f"Error while redirecting client: {e}")
                            self.client_queue.append(client_conn)  # 실패 시 다시 대기열로 추가

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

        # 서버 상태 확인 및 대기열 처리 쓰레드 실행
        threading.Thread(target=self.health_check, daemon=True).start()
        threading.Thread(target=self.process_waiting_clients, daemon=True).start()
        threading.Thread(target=self.monitor_server_load, daemon=True).start()  # 빈 서버 감지 스레드 추가

        while True:
            # 클라이언트 연결 수락
            client_conn, client_addr = balancer_socket.accept()
            print(f"Client connected: {client_addr}")

            # 클라이언트 할당
            self.assign_client_to_server(client_conn)

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

        except (ConnectionRefusedError, socket.error) as e:
            print(f"Connection to server {target_server} failed: {e}")
            self.client_queue.append(client_conn)  # 연결 실패 시 대기열로 복구
        except Exception as e:
            print(f"Unexpected error in redirect_client: {e}")
            self.client_queue.append(client_conn)  # 기타 예외 발생 시 복구

    def forward(self, client_conn, server_conn):
        """
        클라이언트와 서버 간의 직접 통신을 설정.
        """
        try:
            # 서버와 클라이언트 간 양방향 데이터 전송
            threading.Thread(target=self.transfer, args=(client_conn, server_conn)).start()
            self.transfer(server_conn, client_conn)
        except Exception as e:
            print(f"Error during data transfer: {e}")
        finally:
            # 연결 종료 시 클라이언트 목록에서 제거
            for server_address, clients in self.server_clients.items():
                if client_conn in clients:
                    clients.remove(client_conn)
                    print(f"Client disconnected from server {server_address}.")
                    break
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
