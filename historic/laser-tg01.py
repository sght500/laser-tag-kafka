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
SPEED = 3
BULLET_SPEED = 5

# Create Game Window
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Laser Tag Game")
clock = pygame.time.Clock()

# Player Class
class Player:
    def __init__(self, x, y, color):
        self.rect = pygame.Rect(x, y, 20, 20)
        self.color = color
        self.bullets = []

    def move(self, keys):
        if keys[pygame.K_w]: self.rect.y -= SPEED
        if keys[pygame.K_s]: self.rect.y += SPEED
        if keys[pygame.K_a]: self.rect.x -= SPEED
        if keys[pygame.K_d]: self.rect.x += SPEED

    def shoot(self):
        bullet = pygame.Rect(self.rect.centerx, self.rect.top, 5, 10)
        self.bullets.append(bullet)

    def update_bullets(self):
        for bullet in self.bullets[:]:
            bullet.y -= BULLET_SPEED
            if bullet.bottom < 0:
                self.bullets.remove(bullet)

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)
        for bullet in self.bullets:
            pygame.draw.rect(screen, BULLET_COLOR, bullet)

# Enemy Class
class Enemy:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 20, 20)

    def move(self):
        self.rect.x += random.choice([-1, 1]) * SPEED
        self.rect.y += random.choice([-1, 1]) * SPEED

    def draw(self, screen):
        pygame.draw.rect(screen, ENEMY_COLOR, self.rect)

# Create Players
player = Player(WIDTH//2, HEIGHT-50, PLAYER_COLOR)
enemies = [Enemy(random.randint(0, WIDTH-20), random.randint(0, HEIGHT//2)) for _ in range(3)]

# Game Loop
running = True
while running:
    screen.fill(BG_COLOR)
    keys = pygame.key.get_pressed()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                player.shoot()

    player.move(keys)
    player.update_bullets()
    player.draw(screen)
    
    for enemy in enemies:
        enemy.move()
        enemy.draw(screen)
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
