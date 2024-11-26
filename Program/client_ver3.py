import socket
import threading
import pickle
import pygame
import random

# 파이게임 초기화 🌟 뱀이 움직일 준비 완료!
pygame.init()
WHITE = (255, 255, 255)  # 화면 배경색 🎨
RED = (255, 0, 0)        # 사과 색 🍎
GREEN = (0, 255, 0)      # 뱀 색 🐍
size = [400, 400]        # 화면 크기 설정 📏
screen = pygame.display.set_mode(size)  # 게임 창 생성
pygame.display.set_caption("Multiplayer Snake Game")  # 게임 제목 설정 🌟
FONT = pygame.font.Font(None, 36)  # 점수 표시 폰트 🎨
clock = pygame.time.Clock()  # 게임 속도 조절 시계 ⏰

# 키보드 방향키와 실제 방향 연결 🧭
KEY_DIRECTION = {
    pygame.K_UP: 'N',
    pygame.K_DOWN: 'S',
    pygame.K_LEFT: 'W',
    pygame.K_RIGHT: 'E',
}

# 클라이언트 클래스 정의 🐍📡 멀티플레이 준비!
class SnakeClient:
    def __init__(self, host='localhost', port=8080):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # 서버와 연결할 소켓 생성 📡
        self.client.connect((host, port))  # 서버 연결 🔗
        self.running = True  # 게임 실행 여부 🌟
        self.snake = [(random.randint(0, 19), random.randint(0, 19))]  # 뱀 초기 위치 설정 🐍
        self.score = 0  # 점수 초기화 🎯
        self.top_score = 0  # 최고 점수 초기화 🏆

        # 서버로부터 데이터 받는 스레드 시작 🧵
        threading.Thread(target=self.receive_data).start()

    # 서버에서 데이터 받기 📩
    def receive_data(self):
        while self.running:
            try:
                data = self.client.recv(4096)  # 서버로부터 데이터 받기
                if not data:  # 연결 종료 시
                    print("Connection closed by the server.")
                    break
                game_state = pickle.loads(data)  # 데이터 디코딩
                self.update_game_state(game_state)  # 게임 상태 업데이트
            except (EOFError, ConnectionResetError):
                print("Connection to the server was interrupted.")
                break
        self.stop()  # 연결 종료 시 클라이언트 멈춤

    # 게임 상태 업데이트 🐍
    def update_game_state(self, state):
        server_score = state.get("scores", {}).get(self.client, 0)  # 서버 점수 확인
        self.score = max(self.score, server_score)  # 높은 점수로 업데이트 🎯
        self.top_score = state.get("top_score", 0)  # 최고 점수 업데이트 🏆

    # 데이터 서버로 보내기 📤
    def send_data(self, data):
        try:
            self.client.send(pickle.dumps(data))  # 데이터 인코딩 후 전송
        except socket.error:
            self.stop()

    # 클라이언트 종료 🚫
    def stop(self):
        self.running = False
        self.client.close()

# 사과 클래스 🍎
class Apple:
    def __init__(self):
        self.position = (random.randint(0, 19), random.randint(0, 19))  # 사과 위치 랜덤 생성

    def draw(self):
        draw_block(screen, RED, self.position)  # 사과 화면에 그리기

# 블록 그리는 함수 🎨
def draw_block(screen, color, position):
    block = pygame.Rect((position[1] * 20, position[0] * 20), (20, 20))  # 블록 크기와 위치
    pygame.draw.rect(screen, color, block)  # 화면에 블록 그리기

# 메인 게임 함수 🎮
def main():
    client = SnakeClient()  # 클라이언트 생성
    running = True  # 게임 루프 실행 여부 🌟
    direction = "E"  # 뱀 초기 방향 설정 🐍➡️
    snake_body = client.snake  # 뱀의 몸체 🐍
    apple = Apple()  # 사과 생성 🍎

    while running:
        screen.fill(WHITE)  # 화면 초기화 🎨
        for event in pygame.event.get():  # 이벤트 처리
            if event.type == pygame.QUIT:  # 게임 종료 이벤트
                running = False
                client.stop()
            if event.type == pygame.KEYDOWN:  # 키보드 입력 이벤트
                if event.key in {pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT}:
                    direction = KEY_DIRECTION[event.key]

        # 뱀 이동 🐍
        head_y, head_x = snake_body[0]
        if direction == "N":
            new_head = (head_y - 1, head_x)
        elif direction == "S":
            new_head = (head_y + 1, head_x)
        elif direction == "W":
            new_head = (head_y, head_x - 1)
        elif direction == "E":
            new_head = (head_y, head_x + 1)

        # 벽을 넘어가면 반대편으로 이동 🚧➡️⬅️
        new_head = (new_head[0] % (size[1] // 20), new_head[1] % (size[0] // 20))

        # 뱀이 사과 먹기 🍎🐍
        if new_head == apple.position:
            snake_body = [new_head] + snake_body  # 몸 길이 증가
            apple = Apple()  # 새로운 사과 생성
            client.score += 1  # 점수 증가 🎯
            client.send_data({"score": client.score})  # 점수 서버에 전송
        else:
            snake_body = [new_head] + snake_body[:-1]  # 뱀 이동

        # 자기 자신과 충돌 확인 ❌🐍
        if snake_body[0] in snake_body[1:]:
            print("Game Over! You collided with yourself.")
            running = False
            client.stop()

        client.send_data({"move": snake_body})  # 이동 데이터 서버에 전송

        # 뱀과 사과 그리기 🐍🍎
        for segment in snake_body:
            pygame.draw.rect(screen, GREEN, (segment[1] * 20, segment[0] * 20, 20, 20))
        apple.draw()

        # 점수 표시 🎯
        score_text = FONT.render(f"Your Score: {client.score}", True, (0, 0, 0))
        top_score_text = FONT.render(f"Top Score: {client.top_score}", True, (0, 0, 0))
        screen.blit(score_text, (10, 10))
        screen.blit(top_score_text, (10, 50))

        pygame.display.update()  # 화면 업데이트 🌟
        clock.tick(10)  # 게임 속도 설정 ⏰

    pygame.quit()  # 게임 종료 🚪

# 프로그램 실행 🐍
if __name__ == "__main__":
    main()
