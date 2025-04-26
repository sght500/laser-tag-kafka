import pygame
import random

# Initialize Pygame
pygame.init()

# Game Constants
WIDTH, HEIGHT = 800, 600
BG_COLOR = (30, 30, 30)
PLAYER_COLOR = (0, 255, 0)
ENEMY_COLOR = (255, 0, 0)
BULLET_COLOR = (255, 255, 0)
WALL_COLOR, WALL_PIXELS = (128, 96, 96), 40
SPEED = 3
BULLET_SPEED, DG_BULLET_SPPED_X, DG_BULLET_SPPED_Y = 5, 4, 3

# Create Game Window
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Laser Tag Game")
clock = pygame.time.Clock()

class Bullet:
    def __init__(self, centerx, centery, dx, dy):
        self.rect = pygame.Rect(centerx - 2, centery - 2, 5, 5)  # Square bullet due to diagonal shots
        self.dx = dx
        self.dy = dy

    def update(self):
        self.rect.x += self.dx
        self.rect.y += self.dy

    def draw(self, screen):
        pygame.draw.rect(screen, BULLET_COLOR, self.rect)
        
# Player Class
class Player:
    def __init__(self, x, y, color):
        self.rect = pygame.Rect(x, y, 20, 20)
        self.color = color
        self.bullets = []

    def move_or_shoot(self, keys):
        if keys[pygame.K_w]: self.rect.y -= SPEED
        if keys[pygame.K_s]: self.rect.y += SPEED
        if keys[pygame.K_a]: self.rect.x -= SPEED
        if keys[pygame.K_d]: self.rect.x += SPEED

        # Check for 4 key press
        direction = None
        if keys[pygame.K_j] and keys[pygame.K_i] and keys[pygame.K_l] and keys[pygame.K_k]: direction = None
        # Check for 3 key press
        elif keys[pygame.K_j] and keys[pygame.K_i] and keys[pygame.K_l]: direction = "up"
        elif keys[pygame.K_j] and keys[pygame.K_k] and keys[pygame.K_l]: direction = "dn"
        elif keys[pygame.K_j] and keys[pygame.K_i] and keys[pygame.K_k]: direction = "lf"
        elif keys[pygame.K_i] and keys[pygame.K_k] and keys[pygame.K_l]: direction = "rt"
        # Check for 2 key press
        elif keys[pygame.K_j] and keys[pygame.K_i]: direction = "up-lf"
        elif keys[pygame.K_i] and keys[pygame.K_l]: direction = "up-rt"
        elif keys[pygame.K_k] and keys[pygame.K_l]: direction = "dn-rt"
        elif keys[pygame.K_j] and keys[pygame.K_k]: direction = "dn-lf"
        # Check for 1 key press
        elif keys[pygame.K_i]: direction = "up"
        elif keys[pygame.K_k]: direction = "dn"
        elif keys[pygame.K_j]: direction = "lf"
        elif keys[pygame.K_l]: direction = "rt"
        # Apply the shoot direction
        if direction: self.shoot(direction)

    def shoot(self, direction):
        if direction == "up":
            cx, cy = self.rect.centerx, self.rect.top
            dx, dy = 0, -BULLET_SPEED            
        elif direction == "dn":
            cx, cy = self.rect.centerx, self.rect.bottom
            dx, dy = 0, BULLET_SPEED
        elif direction == "lf":
            cx, cy = self.rect.left, self.rect.centery
            dx, dy = -BULLET_SPEED, 0
        elif direction == "rt":
            cx, cy = self.rect.right, self.rect.centery
            dx, dy = BULLET_SPEED, 0
        elif direction == "up-lf":
            cx, cy = self.rect.left, self.rect.top
            dx, dy = -DG_BULLET_SPPED_X, -DG_BULLET_SPPED_Y
        elif direction == "up-rt":
            cx, cy = self.rect.right, self.rect.top
            dx, dy = DG_BULLET_SPPED_X, -DG_BULLET_SPPED_Y
        elif direction == "dn-lf":
            cx, cy = self.rect.left, self.rect.bottom
            dx, dy = -DG_BULLET_SPPED_X, DG_BULLET_SPPED_Y
        elif direction == "dn-rt":
            cx, cy = self.rect.right, self.rect.bottom
            dx, dy = DG_BULLET_SPPED_X, DG_BULLET_SPPED_Y
        bullet = Bullet(cx, cy,dx,dy)
        self.bullets.append(bullet)

    def update_bullets(self):
        for bullet in self.bullets[:]:
            bullet.update()
            if bullet.rect.bottom < 0 or bullet.rect.top > HEIGHT or bullet.rect.right < 0 or bullet.rect.left > WIDTH:
                self.bullets.remove(bullet)

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)
        for bullet in self.bullets:
            bullet.draw(screen)

# Enemy Class
class Enemy:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 20, 20)

    def move(self):
        self.rect.x += random.choice([-1, 1]) * SPEED
        self.rect.y += random.choice([-1, 1]) * SPEED

    def draw(self, screen):
        pygame.draw.rect(screen, ENEMY_COLOR, self.rect)

# Maze Class
class Maze:
    def __init__(self, rows, cols, pixels):
        self.rows = rows
        self.cols = cols
        self.pixels = pixels
        self.map = self.generate_map()
        self.bricks = []
        for r, row in enumerate(self.map):  # r = row index, row = row data
            for c, col in enumerate(row):  # c = column index, col = cell value
                if col:  # If the cell is not empty (wall present)
                    self.bricks.append(
                        pygame.Rect(c * self.pixels, r * self.pixels, self.pixels, self.pixels)
                    )

    def generate_map(self):
        """Generates a random map with a border of walls."""
        map = [[1] * self.cols for _ in range(self.rows)]  # Start with all walls
        # Create random open spots
        for r in range(1, self.rows - 1):  # Avoid modifying outer border
            for c in range(1, self.cols - 1):
                if random.random() > 0.2: map[r][c] = 0  # 80% chance to clear the brick
        return map

    def draw(self, screen):
        for brick in self.bricks:
            pygame.draw.rect(screen, WALL_COLOR, brick)

# Create Players and the Maze
player = Player(WIDTH//2, HEIGHT-50, PLAYER_COLOR)
enemies = [Enemy(random.randint(0, WIDTH-20), random.randint(0, HEIGHT//2)) for _ in range(3)]
maze = Maze(HEIGHT//WALL_PIXELS, WIDTH//WALL_PIXELS, WALL_PIXELS)

# Game Loop
running = True
while running:
    screen.fill(BG_COLOR)
    keys = pygame.key.get_pressed()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    maze.draw(screen)

    player.move_or_shoot(keys)
    player.update_bullets()
    player.draw(screen)
    
    for enemy in enemies:
        enemy.move()
        enemy.draw(screen)
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
