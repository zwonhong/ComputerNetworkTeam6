import socket
import threading
import pickle
import pygame
import random

pygame.init()
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
size = [400, 400]
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
        self.snake = [(random.randint(0, 19), random.randint(0, 19))]
        self.score = 0
        self.top_score = 0

        threading.Thread(target=self.receive_data).start()

    def receive_data(self):
        while self.running:
            try:
                data = self.client.recv(4096)
                if not data:  # 연결 종료
                    print("Connection closed by the server.")
                    break
                game_state = pickle.loads(data)
                self.update_game_state(game_state)
            except (EOFError, ConnectionResetError):
                print("Connection to the server was interrupted.")
                break
        self.stop()  # 연결 종료 시 클라이언트 종료


    def update_game_state(self, state):
        # Keep local score unless a new score is higher
        server_score = state.get("scores", {}).get(self.client, 0)
        self.score = max(self.score, server_score)  # Only update if server score is higher
        self.top_score = state.get("top_score", 0)
        # Process other game state data as needed

    def send_data(self, data):
        try:
            self.client.send(pickle.dumps(data))
        except socket.error:
            self.stop()

    def stop(self):
        self.running = False
        self.client.close()

class Apple:
    def __init__(self):
        self.position = (random.randint(0, 19), random.randint(0, 19))

    def draw(self):
        draw_block(screen, RED, self.position)

def draw_block(screen, color, position):
    block = pygame.Rect((position[1] * 20, position[0] * 20), (20, 20))
    pygame.draw.rect(screen, color, block)

# Update snake_client class to send score
def main():
    client = SnakeClient()
    running = True
    direction = "E"
    snake_body = client.snake
    apple = Apple()  # Initialize apple

    while running:
        screen.fill(WHITE)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                client.stop()
            if event.type == pygame.KEYDOWN:
                if event.key in {pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT}:
                    direction = KEY_DIRECTION[event.key]

        # Move snake and update server
        head_y, head_x = snake_body[0]
        if direction == "N":
            new_head = (head_y - 1, head_x)
        elif direction == "S":
            new_head = (head_y + 1, head_x)
        elif direction == "W":
            new_head = (head_y, head_x - 1)
        elif direction == "E":
            new_head = (head_y, head_x + 1)

         # Boundary check: Stop movement if out of bounds
        if not (0 <= new_head[0] < size[1] // 20 and 0 <= new_head[1] < size[0] // 20):
            # If out of bounds, stop movement in current direction
            continue  # Skip to the next iteration without updating position


        # Check if snake eats the apple
        if new_head == apple.position:
            snake_body = [new_head] + snake_body  # Grow the snake by adding the new head
            apple = Apple()  # Generate a new apple
            client.score += 1  # Increase local score
            client.send_data({"score": client.score})  # Send updated score to server
        else:
            snake_body = [new_head] + snake_body[:-1]  # Regular movement

        # Check for collision with self
        if snake_body[0] in snake_body[1:]:
            print("Game Over! You collided with yourself.")
            running = False
            client.stop()

        client.send_data({"move": snake_body})

        # Drawing
        for segment in snake_body:
            pygame.draw.rect(screen, GREEN, (segment[1] * 20, segment[0] * 20, 20, 20))
        
        apple.draw()  # Draw the apple

        # Display scores
        score_text = FONT.render(f"Your Score: {client.score}", True, (0, 0, 0))
        top_score_text = FONT.render(f"Top Score: {client.top_score}", True, (0, 0, 0))
        screen.blit(score_text, (10, 10))
        screen.blit(top_score_text, (10, 50))

        pygame.display.update()
        clock.tick(10)

    pygame.quit()



if __name__ == "__main__":
    main()
