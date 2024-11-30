import socket
import threading
import pickle
import pygame
import random

# 파이게임 초기화 🌟
pygame.init()
WHITE = (255, 255, 255)  # 화면 배경색 🎨
RED = (255, 0, 0)        # 사과 색 🍎
GREEN = (0, 255, 0)      # 자신의 뱀 색 🐍
LIGHT_GRAY = (200, 200, 200)  # 다른 플레이어의 뱀 색 🐍
size = [400, 440]        # 화면 크기 설정 📏
screen = pygame.display.set_mode(size)
pygame.display.set_caption("Multiplayer Snake Game")
FONT = pygame.font.Font(None, 36)
clock = pygame.time.Clock()

KEY_DIRECTION = {
    pygame.K_UP: 'N',
    pygame.K_DOWN: 'S',
    pygame.K_LEFT: 'W',
    pygame.K_RIGHT: 'E',
}

class SnakeClient:
    def __init__(self, host='localhost', port=8080):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((host, port))
        self.running = True
        self.snake = [(random.randint(1, 19), random.randint(0, 19))]
        self.score = 0
        self.top_score = 0
        self.apples = [(random.randint(0, 19), random.randint(0, 19))]
        self.other_snakes = {}
        self.color_index = None

        # 색상 인덱스 수신
        self.color_index = int(self.client.recv(1024).decode())
        threading.Thread(target=self.receive_data).start()

    def receive_data(self):
        while self.running:
            try:
                data = self.client.recv(4096)
                if not data:
                    break
                game_state = pickle.loads(data)
                self.update_game_state(game_state)
            except (EOFError, ConnectionResetError):
                break
        self.stop()

    def update_game_state(self, state):
        self.other_snakes = state.get("snakes", {})
        self.top_score = state.get("top_score", 0)

    def send_data(self, data):
        try:
            self.client.send(pickle.dumps(data))
        except socket.error:
            self.stop()

    def stop(self):
        self.running = False
        self.client.close()

def draw_block(screen, color, position):
    block = pygame.Rect((position[1] * 20, position[0] * 20 + 40), (20, 20))
    pygame.draw.rect(screen, color, block)

def main():
    client = SnakeClient()
    running = True
    direction = "E"
    last_direction = direction
    snake_body = client.snake

    while running:
        screen.fill(WHITE)
        pygame.draw.rect(screen, (200, 200, 200), (0, 0, size[0], 40))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                client.stop()
            if event.type == pygame.KEYDOWN:
                if event.key in KEY_DIRECTION:
                    new_direction = KEY_DIRECTION[event.key]
                    if not (
                        (new_direction == "N" and last_direction == "S") or
                        (new_direction == "S" and last_direction == "N") or
                        (new_direction == "E" and last_direction == "W") or
                        (new_direction == "W" and last_direction == "E")
                    ):
                        direction = new_direction

        head_y, head_x = snake_body[0]
        if direction == "N":
            new_head = (head_y - 1, head_x)
        elif direction == "S":
            new_head = (head_y + 1, head_x)
        elif direction == "W":
            new_head = (head_y, head_x - 1)
        elif direction == "E":
            new_head = (head_y, head_x + 1)

        new_head = (new_head[0] % 20, new_head[1] % 20)

        if new_head in client.apples:
            snake_body = [new_head] + snake_body
            client.apples.remove(new_head)
            client.apples.append((random.randint(0, 19), random.randint(0, 19)))
            client.score += 1
        else:
            snake_body = [new_head] + snake_body[:-1]

        if snake_body[0] in snake_body[1:]:
            running = False
            client.stop()

        client.send_data({"move": snake_body, "score": client.score})

        # 자신의 뱀 그리기
        for segment in snake_body:
            draw_block(screen, GREEN, segment)

        # 다른 플레이어의 뱀 그리기 (연한 회색으로 표시)
        for player_id, other_snake in client.other_snakes.items():
            for segment in other_snake:
                draw_block(screen, LIGHT_GRAY, segment)

        # 사과 그리기
        for apple in client.apples:
            draw_block(screen, RED, apple)

        # 점수 표시
        score_text = FONT.render(f"Your Score: {client.score}", True, (0, 0, 0))
        top_score_text = FONT.render(f"Top Score: {client.top_score}", True, (0, 0, 0))
        screen.blit(score_text, (10, 5))
        screen.blit(top_score_text, (200, 5))

        pygame.display.update()
        clock.tick(10)
        last_direction = direction

    pygame.quit()

if __name__ == "__main__":
    main()
