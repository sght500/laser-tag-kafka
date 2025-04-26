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
DG_BUFFER_TIME = 50
NO_KEY = -999
MAX_HEALTH = 2000
BULLET_HURT_SPEED = 250
HEALTH_RECOVERY_SPEED = 2
ENEMY_TIMERS = [300,500,850,900]

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
        self.processing_buffer = False
        self.buffer_start_time = 0
        self.previous_key_down = NO_KEY

    def move(self, keys, bricks):
        original_y = self.rect.y
        if keys[pygame.K_w]: self.rect.y -= SPEED
        if keys[pygame.K_s]: self.rect.y += SPEED
        # Vertical collision check
        if any(self.rect.colliderect(brick) for brick in bricks):
            self.rect.y = original_y  # Revert vertical position if collided
        original_x = self.rect.x
        if keys[pygame.K_a]: self.rect.x -= SPEED
        if keys[pygame.K_d]: self.rect.x += SPEED
        # Horizontal collision check
        if any(self.rect.colliderect(brick) for brick in bricks):
            self.rect.x = original_x  # Revert horizontal position if collided
        # Check if there's pending buffer to process
        if self.processing_buffer:
            buffer_time = pygame.time.get_ticks() - self.buffer_start_time
            if buffer_time >= DG_BUFFER_TIME:
                self.process_buffer(NO_KEY)

    def process_buffer(self, key):
        if self.processing_buffer:
            # If it's the same one, you need to process previou key and start processing the buffer again
            if self.previous_key_down == key:
                if key == pygame.K_i: direction = "up"
                elif key == pygame.K_k: direction = "dn"
                elif key == pygame.K_j: direction = "lf"
                elif key == pygame.K_l: direction = "rt"
                else: direction = None
                if direction: self.shoot(direction)
                self.buffer_start_time = pygame.time.get_ticks()
            else:
                if key == NO_KEY:
                    # Buffer time is up. We need to peocess the buffer now.
                    if self.previous_key_down == pygame.K_i: direction = "up"
                    elif self.previous_key_down == pygame.K_k: direction = "dn"
                    elif self.previous_key_down == pygame.K_j: direction = "lf"
                    elif self.previous_key_down == pygame.K_l: direction = "rt"
                elif self.previous_key_down == pygame.K_i:
                    if key == pygame.K_k: direction = None
                    elif key == pygame.K_j: direction = "up-lf"
                    elif key == pygame.K_l: direction = "up-rt"
                elif self.previous_key_down == pygame.K_k:
                    if key == pygame.K_i: direction = None
                    elif key == pygame.K_j: direction = "dn-lf"
                    elif key == pygame.K_l: direction = "dn-rt"
                elif self.previous_key_down == pygame.K_j:
                    if key == pygame.K_i: direction = "up-lf"
                    elif key == pygame.K_k: direction = "dn-lf"
                    elif key == pygame.K_l: direction = None
                elif self.previous_key_down == pygame.K_l:
                    if key == pygame.K_i: direction = "up-rt"
                    elif key == pygame.K_k: direction = "dn-rt"
                    elif key == pygame.K_j: direction = None
                if direction: self.shoot(direction)
                self.previous_key_down = NO_KEY
                self.processing_buffer = False
        else:
            self.processing_buffer = True
            self.buffer_start_time = pygame.time.get_ticks()
            self.previous_key_down = key

    def shoot(self, direction):
        bullet = create_bullet(self.rect, direction)
        self.bullets.append(bullet)

    def update_bullets(self, bricks, enemies):
        for bullet in self.bullets[:]:
            bullet.update()
            # Check if bullet is off the screen
            # if bullet.rect.bottom < 0 or bullet.rect.top > HEIGHT or bullet.rect.right < 0 or bullet.rect.left > WIDTH:
            #     self.bullets.remove(bullet)
            # Collision detection bullet vs wall
            if any(bullet.rect.colliderect(brick) for brick in bricks):
                self.bullets.remove(bullet)
            else:
                # Collision detection bullet vs enemy
                for enemy in enemies:
                    if bullet.rect.colliderect(enemy.rect):
                        enemy.hit()
                        self.bullets.remove(bullet)

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)
        for bullet in self.bullets:
            bullet.draw(screen)

# Enemy Class
class Enemy:
    def __init__(self, x, y, e, timer):
        self.rect = pygame.Rect(x, y, 20, 20)
        self.hurt_rect = pygame.Rect(x + 2, y + 2, 0, 16)
        self.health = MAX_HEALTH
        self.x_way = random.choice([-1, 0, 1])
        self.y_way = random.choice([-1, 0, 1])
        self.shoot_timer = pygame.USEREVENT + e
        pygame.time.set_timer(self.shoot_timer, timer)

    def move(self, bricks):
        if random.random() <= .05:
            self.x_way = random.choice([-1, 0, 0, 0, 1])
            self.y_way = random.choice([-1, 0, 0, 0, 1])
        # Horizontal movement
        original_x = self.rect.x
        self.rect.x += self.x_way * SPEED
        # Horizontal collision check
        if any(self.rect.colliderect(brick) for brick in bricks):
            self.rect.x = original_x  # Revert vertical position if collided
        # Vertical movement
        original_y = self.rect.y
        self.rect.y += self.y_way * SPEED
        # Vertical collision check
        if any(self.rect.colliderect(brick) for brick in bricks):
            self.rect.y = original_y  # Revert vertical position if collided

        if self.health < MAX_HEALTH: self.health += HEALTH_RECOVERY_SPEED
        # How hurt is this enemy?
        hurt_percent = (MAX_HEALTH - self.health) / MAX_HEALTH
        self.hurt_rect.update(
            self.rect.x + 10 - 10 * hurt_percent,
            self.rect.y + 10 - 10 * hurt_percent,
            20 * hurt_percent,
            20 * hurt_percent
        )

    def hit(self):
        self.health -= BULLET_HURT_SPEED

    def shoot(self, direction):
        return create_bullet(self.rect, direction)

    def draw(self, screen):
        pygame.draw.rect(screen, ENEMY_COLOR, self.rect)
        pygame.draw.rect(screen, BG_COLOR, self.hurt_rect)

class NoDirectionException(Exception):
    """Exception raised when no direction is provided for bullet creation."""
    pass

def create_bullet(rect, direction):
    if not direction: raise NoDirectionException("Bullet must have a direction!")
    # Apply the shoot direction
    if direction == "up":
        cx, cy = rect.centerx, rect.top
        dx, dy = 0, -BULLET_SPEED            
    elif direction == "dn":
        cx, cy = rect.centerx, rect.bottom
        dx, dy = 0, BULLET_SPEED
    elif direction == "lf":
        cx, cy = rect.left, rect.centery
        dx, dy = -BULLET_SPEED, 0
    elif direction == "rt":
        cx, cy = rect.right, rect.centery
        dx, dy = BULLET_SPEED, 0
    elif direction == "up-lf":
        cx, cy = rect.left, rect.top
        dx, dy = -DG_BULLET_SPPED_X, -DG_BULLET_SPPED_Y
    elif direction == "up-rt":
        cx, cy = rect.right, rect.top
        dx, dy = DG_BULLET_SPPED_X, -DG_BULLET_SPPED_Y
    elif direction == "dn-lf":
        cx, cy = rect.left, rect.bottom
        dx, dy = -DG_BULLET_SPPED_X, DG_BULLET_SPPED_Y
    elif direction == "dn-rt":
        cx, cy = rect.right, rect.bottom
        dx, dy = DG_BULLET_SPPED_X, DG_BULLET_SPPED_Y
    # Return the new bullet with the defined parameters
    return Bullet(cx,cy,dx,dy)


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

# Create the maze and the player and the enemies
maze = Maze(HEIGHT//WALL_PIXELS, WIDTH//WALL_PIXELS, WALL_PIXELS)
# Create a list of open spaces
open_spaces = [(r, c) for r in range(len(maze.map)) for c in range(len(maze.map[0])) if maze.map[r][c] == 0]
# Spawn the player at a random open space
r, c = random.choice(open_spaces)
x = c * WALL_PIXELS + 20 * random.random()
y = r * WALL_PIXELS + 20 * random.random()
player = Player(x, y, PLAYER_COLOR)
# Spawn the enemies at random open spaces
enemies = []
for e, timer in enumerate(ENEMY_TIMERS):
    r, c = random.choice(open_spaces)
    x = c * WALL_PIXELS + 20 * random.random()
    y = r * WALL_PIXELS + 20 * random.random()
    enemies.append(Enemy(x, y, e, timer))
# Centralized bullet magement
bullets = []

# Game Loop
running = True
while running:
    screen.fill(BG_COLOR)
    keys = pygame.key.get_pressed()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key in [pygame.K_i, pygame.K_j, pygame.K_k, pygame.K_l]:
            player.process_buffer(event.key)
        for enemy in enemies:
            if event.type == enemy.shoot_timer:
                bullets.append(
                    enemy.shoot(random.choice(["up", "dn", "lf", "rt", "up-lf", "up-rt", "dn-lf", "dn-rt"]))
                )

    maze.draw(screen)

    player.move(keys, maze.bricks)
    player.update_bullets(maze.bricks, enemies)
    player.draw(screen)
    
    for enemy in enemies[:]:
        if enemy.health <= 0:
            pygame.time.set_timer(enemy.shoot_timer, 0)
            enemies.remove(enemy)
        else:
            enemy.move(maze.bricks)
            enemy.draw(screen)

    # Indepentent bullet management
    for bullet in bullets[:]:
        bullet.update()
        # Collision detection bullet vs wall
        if any(bullet.rect.colliderect(brick) for brick in maze.bricks):
            bullets.remove(bullet)
        else:
            bullet.draw(screen)
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
