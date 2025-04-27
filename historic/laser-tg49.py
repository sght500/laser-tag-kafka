from kafka_messaging18 import KafkaMessenger, KafkaMessageHandler, KafkaMapManager
import string
import pygame
import random
import time

# Initialize Pygame
pygame.init()

# Game Constants
WIDTH, HEIGHT = 800, 600
BG_COLOR = (30, 30, 30)
PLAYER_COLOR = (0, 255, 0)
ENEMY_COLOR = (255, 0, 0)
REMOTE_ENEMY_COLOR = (191, 0, 191)
BULLET_COLOR = (255, 255, 0)
WALL_COLOR, WALL_PIXELS = (128, 96, 96), 40
SPEED = 3
BULLET_SPEED, DG_BULLET_SPPED_X, DG_BULLET_SPPED_Y = 5, 4, 3
BULLET_OFFSET = 1
DG_BUFFER_TIME = 50
NO_KEY = -999
MAX_HEALTH = 2000
BULLET_HURT_SPEED = 250
HEALTH_RECOVERY_SPEED = 2
ENEMY_TIMERS = [300,350,500,550,650]
# Kafka Constants
BOOTSTRAP_SERVERS = "192.168.0.9:9092"
MAX_AGE_LAST_ACTIVITY = 300  # Seconds from last activity to create a new maze.

# Create Game Window
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Laser Tag Game with Kafka")
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
        self.processing_buffer = False
        self.buffer_start_time = 0
        self.previous_key_down = NO_KEY
        self.hurt_rect = pygame.Rect(x, y, 0, 0)
        self.health = MAX_HEALTH

    def move(self, keys, bricks):
        original_y = self.rect.y
        if pygame.K_w in keys: self.rect.y -= SPEED
        if pygame.K_s in keys: self.rect.y += SPEED
        # Vertical collision check
        if any(self.rect.colliderect(brick) for brick in bricks):
            self.rect.y = original_y  # Revert vertical position if collided
        original_x = self.rect.x
        if pygame.K_a in keys: self.rect.x -= SPEED
        if pygame.K_d in keys: self.rect.x += SPEED
        # Horizontal collision check
        if any(self.rect.colliderect(brick) for brick in bricks):
            self.rect.x = original_x  # Revert horizontal position if collided
        # Check if there's pending buffer to process
        if self.processing_buffer:
            buffer_time = pygame.time.get_ticks() - self.buffer_start_time
            if buffer_time >= DG_BUFFER_TIME:
                global game_bullets # Fixes simple IJKL direction bullets.
                bullet = self.process_buffer(NO_KEY)
                messenger.send_bullet_created((bullet.rect.x+2, bullet.rect.y+2), (bullet.dx, bullet.dy))
                map_manager.send_last_activity()
                game_bullets.append(bullet)

        if self.health < MAX_HEALTH: self.health += HEALTH_RECOVERY_SPEED
        # How hurt is the Player?
        hurt_percent = (MAX_HEALTH - self.health) / MAX_HEALTH
        self.hurt_rect.update(
            self.rect.x + 10 - 10 * hurt_percent,
            self.rect.y + 10 - 10 * hurt_percent,
            20 * hurt_percent,
            20 * hurt_percent
        )

    def process_buffer(self, key):
        bullet = None
        if self.processing_buffer:
            # If it's the same one, you need to process previou key and start processing the buffer again
            if self.previous_key_down == key:
                if key == pygame.K_i: direction = "up"
                elif key == pygame.K_k: direction = "dn"
                elif key == pygame.K_j: direction = "lf"
                elif key == pygame.K_l: direction = "rt"
                else: direction = None
                if direction: bullet = self.shoot(direction)
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
                if direction: bullet = self.shoot(direction)
                self.previous_key_down = NO_KEY
                self.processing_buffer = False
        else:
            self.processing_buffer = True
            self.buffer_start_time = pygame.time.get_ticks()
            self.previous_key_down = key
        return bullet

    def hit(self):
        messenger.send_hit()
        self.health -= BULLET_HURT_SPEED

    def shoot(self, direction):
        return create_bullet(self.rect, direction)

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)
        pygame.draw.rect(screen, BG_COLOR, self.hurt_rect)


# Enemy Class
class Enemy:
    def __init__(self, x, y, e, timer):
        self.rect = pygame.Rect(x, y, 20, 20)
        self.hurt_rect = pygame.Rect(x, y, 0, 0)
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

# Remote Enemy Class
class RemoteEnemy:
    def __init__(self, x, y, keys):
        self.rect = pygame.Rect(x, y, 20, 20)
        self.hurt_rect = pygame.Rect(x, y, 0, 0)
        self.health = MAX_HEALTH
        self.keys = keys

    def move(self, bricks):
        original_y = self.rect.y
        if pygame.K_w in self.keys: self.rect.y -= SPEED
        if pygame.K_s in self.keys: self.rect.y += SPEED
        # Vertical collision check
        if any(self.rect.colliderect(brick) for brick in bricks):
            self.rect.y = original_y  # Revert vertical position if collided
        original_x = self.rect.x
        if pygame.K_a in self.keys: self.rect.x -= SPEED
        if pygame.K_d in self.keys: self.rect.x += SPEED
        # Horizontal collision check
        if any(self.rect.colliderect(brick) for brick in bricks):
            self.rect.x = original_x  # Revert horizontal position if collided

        if self.health < MAX_HEALTH: self.health += HEALTH_RECOVERY_SPEED
        # How hurt is this enemy?
        hurt_percent = (MAX_HEALTH - self.health) / MAX_HEALTH
        self.hurt_rect.update(
            self.rect.x + 10 - 10 * hurt_percent,
            self.rect.y + 10 - 10 * hurt_percent,
            20 * hurt_percent,
            20 * hurt_percent
        )

    def update_position_and_keys(self, x, y, keys):
        self.rect.x = x
        self.rect.y = y
        self.keys = keys

    def hit(self):
        self.health -= BULLET_HURT_SPEED

    def draw(self, screen):
        pygame.draw.rect(screen, REMOTE_ENEMY_COLOR, self.rect)
        pygame.draw.rect(screen, BG_COLOR, self.hurt_rect)

class NoDirectionException(Exception):
    """Exception raised when no direction is provided for bullet creation."""
    pass

def create_bullet(rect, direction):
    if not direction: raise NoDirectionException("Bullet must have a direction!")
    # Apply the shoot direction
    if direction == "up":
        cx, cy = rect.centerx, rect.top - BULLET_OFFSET
        dx, dy = 0, -BULLET_SPEED            
    elif direction == "dn":
        cx, cy = rect.centerx, rect.bottom + BULLET_OFFSET
        dx, dy = 0, BULLET_SPEED
    elif direction == "lf":
        cx, cy = rect.left - BULLET_OFFSET, rect.centery
        dx, dy = -BULLET_SPEED, 0
    elif direction == "rt":
        cx, cy = rect.right + BULLET_OFFSET, rect.centery
        dx, dy = BULLET_SPEED, 0
    elif direction == "up-lf":
        cx, cy = rect.left - BULLET_OFFSET, rect.top - BULLET_OFFSET
        dx, dy = -DG_BULLET_SPPED_X, -DG_BULLET_SPPED_Y
    elif direction == "up-rt":
        cx, cy = rect.right + BULLET_OFFSET, rect.top - BULLET_OFFSET
        dx, dy = DG_BULLET_SPPED_X, -DG_BULLET_SPPED_Y
    elif direction == "dn-lf":
        cx, cy = rect.left - BULLET_OFFSET, rect.bottom + BULLET_OFFSET
        dx, dy = -DG_BULLET_SPPED_X, DG_BULLET_SPPED_Y
    elif direction == "dn-rt":
        cx, cy = rect.right + BULLET_OFFSET, rect.bottom + BULLET_OFFSET
        dx, dy = DG_BULLET_SPPED_X, DG_BULLET_SPPED_Y
    # Return the new bullet with the defined parameters
    return Bullet(cx,cy,dx,dy)


# Maze Class
class Maze:
    def __init__(self, rows=HEIGHT//WALL_PIXELS, cols=WIDTH//WALL_PIXELS, pixels=WALL_PIXELS, map=None):
        self.pixels = pixels
        self.bricks = []

        if map:
            self.map = map
            self.rows = len(map)
            self.cols = len(map[0]) if self.rows > 0 else 0
        else:
            self.rows = rows
            self.cols = cols
            self.map = self.generate_map()

        # Generate bricks from the map
        for r, row in enumerate(self.map):
            for c, col in enumerate(row):
                if col:
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


# Handling Kafka Messages
def handle_kafka_message(sender_id, data, current_keys):
    msg_type = data.get("type")
    # global remote_enemies
    if msg_type == "wasd-update":
        position = data.get("position")
        x, y = position[0], position[1]
        keys = data.get("keys")
        if sender_id in remote_enemies:
            enemy = remote_enemies.get(sender_id)
            enemy.update_position_and_keys(x, y, keys)
        else:
            enemy = RemoteEnemy(x, y, keys)
            remote_enemies[sender_id] = enemy
            print (f"Created {sender_id} remote enemy")
    elif msg_type == "bullet-created":
        position = data.get("position")
        x, y = position[0], position[1]
        velocity = data.get("velocity")
        dx, dy = velocity[0], velocity[1]
        bullet = Bullet(x, y, dx, dy)
        game_bullets.append(bullet)
    elif msg_type == "player-spawn":
        messenger.send_wasd_update((player.rect.x, player.rect.y), current_keys)
    elif msg_type == "got-hit":
        print (f"remote enemy {sender_id} got hit")
        if sender_id in remote_enemies:
            enemy = remote_enemies.get(sender_id)
            enemy.hit()


# Kafka Messaging
player_id = ''.join(random.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits) for _ in range(13))
messenger = KafkaMessenger(player_id, bootstrap_servers=BOOTSTRAP_SERVERS)
message_handler = KafkaMessageHandler(player_id, bootstrap_servers=BOOTSTRAP_SERVERS)
map_manager = KafkaMapManager(player_id, bootstrap_servers=BOOTSTRAP_SERVERS)

# Try to read current map and last-activity
map, last_activity = map_manager.read_map_and_activity()

# Determine whether to reuse map or generate a new one
reuse_map = False
if map:
    if last_activity:
        age_last_activiy = time.time() - last_activity
        print("!!Last activity was {:.1f}s ago".format(age_last_activiy))
        if age_last_activiy <= MAX_AGE_LAST_ACTIVITY:
            print("Last activity was {:.1f}s ago".format(age_last_activiy))
            reuse_map = True
    else:
        reuse_map = True

if reuse_map:
    print("✅ Reusing maze from Kafka topic.")
    maze = Maze(map=map)
else:
    print("🌀 Creating new maze and publishing to Kafka topic.")
    maze = Maze(HEIGHT//WALL_PIXELS, WIDTH//WALL_PIXELS, WALL_PIXELS)  # Generate a new one
    map_manager.send_map(maze.map)
    map_manager.send_last_activity()


# Create the player and the enemies
# Create a list of open spaces
open_spaces = [(r, c) for r in range(len(maze.map)) for c in range(len(maze.map[0])) if maze.map[r][c] == 0]
# Spawn the player at a random open space
r, c = random.choice(open_spaces)
x = c * WALL_PIXELS + 20 * random.random()
y = r * WALL_PIXELS + 20 * random.random()
player = Player(x, y, PLAYER_COLOR)
messenger.send_spawn((player.rect.x, player.rect.y))
# Spawn the enemies at random open spaces
enemies = []
for e, timer in enumerate(ENEMY_TIMERS):
    r, c = random.choice(open_spaces)
    x = c * WALL_PIXELS + 20 * random.random()
    y = r * WALL_PIXELS + 20 * random.random()
    enemies.append(Enemy(x, y, e, timer))

game_bullets = []  # Centralized bullet magement
prev_keys = []  # To detect WASD press/release changes
remote_enemies = {}  # Identified by sender_id as the key.

# Game Loop
running = True
while running:
    screen.fill(BG_COLOR)
    keys = []
    pressed = pygame.key.get_pressed()
    if pressed[pygame.K_w]: keys.append(pygame.K_w)
    if pressed[pygame.K_a]: keys.append(pygame.K_a)
    if pressed[pygame.K_s]: keys.append(pygame.K_s)
    if pressed[pygame.K_d]: keys.append(pygame.K_d)
    if keys != prev_keys:
        messenger.send_wasd_update((player.rect.x, player.rect.y), keys)
        map_manager.send_last_activity()
        prev_keys = keys
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key in [pygame.K_i, pygame.K_j, pygame.K_k, pygame.K_l]:
            bullet = player.process_buffer(event.key)
            if bullet:
                messenger.send_bullet_created((bullet.rect.x+2, bullet.rect.y+2), (bullet.dx, bullet.dy))
                map_manager.send_last_activity()
                game_bullets.append(bullet)
        for enemy in enemies:
            if event.type == enemy.shoot_timer:
                game_bullets.append(
                    enemy.shoot(random.choice(["up", "dn", "lf", "rt", "up-lf", "up-rt", "dn-lf", "dn-rt"]))
                )
    message_handler.poll_messages(handle_kafka_message, keys)

    maze.draw(screen)

    player.move(keys, maze.bricks)
    player.draw(screen)
    
    # Health check
    if player.health <= 0: running = False
    for enemy in enemies[:]:
        if enemy.health <= 0:
            pygame.time.set_timer(enemy.shoot_timer, 0)
            enemies.remove(enemy)
        else:
            enemy.move(maze.bricks)
            enemy.draw(screen)
    for remote_id, enemy in list(remote_enemies.items()):  # Shalow copy because we're removing items while iterating them.
        if enemy.health <= 0:
            del remote_enemies[remote_id]
        else:
            enemy.move(maze.bricks)
            enemy.draw(screen)

    # Indepentent bullet management
    for bullet in game_bullets:
        bullet.update()
        # Collision detection bullet vs wall
        if any(bullet.rect.colliderect(brick) for brick in maze.bricks):
            game_bullets.remove(bullet)
        elif bullet.rect.colliderect(player.rect):
            player.hit()
            game_bullets.remove(bullet)
        else:
            # Collision detection bullet vs enemies
            remove_bullet = False  # Fixes error: ValueError: list.remove(x): x not in list
            for enemy in enemies:
                if bullet.rect.colliderect(enemy.rect):
                    enemy.hit()
                    remove_bullet = True
            for enemy in remote_enemies.values():
                if bullet.rect.colliderect(enemy.rect):
                    remove_bullet = True
            if remove_bullet: game_bullets.remove(bullet)
    # Draw the remaining bullets
    for bullet in game_bullets:
        bullet.draw(screen)

    pygame.display.flip()
    clock.tick(60)

messenger.flush()
message_handler.close()
map_manager.producer.flush()
map_manager.close()
pygame.quit()
