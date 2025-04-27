from kafka_messaging30 import KafkaMessenger, KafkaMessageHandler
import string
import pygame
import random
import time
import math

# Initialize Pygame
pygame.init()

# Game Constants
WIDTH, HEIGHT = 800, 600
BG_COLOR = (30, 30, 30)
BG_COLOR_ALPHA = (30, 30, 30, 229)  # 229 = Alpha 90% (10% Transparent)
TITLE_COLOR = (255, 255, 64)
INSTRUCTION_COLOR = (229, 229, 229)
STATUS_COLOR = (99, 151, 203)
PLAYER_COLOR = (0, 255, 0)
ENEMY_COLOR = (255, 0, 0)
REMOTE_ENEMY_COLOR = (191, 0, 191)
BULLET_COLOR = (255, 255, 0)
WALL_COLOR, WALL_PIXELS = (128, 96, 96), 40
SPEED = 3
BULLET_SPEED, DG_BULLET_SPPED_X, DG_BULLET_SPPED_Y = 5, 4, 3
BULLET_OFFSET = 1
DG_BUFFER_TIME = 50  # How many ms should pass to detect a diagonal shot.
NO_KEY = -999
MAX_HEALTH = 2000
BULLET_HURT_SPEED = 250
HEALTH_RECOVERY_SPEED = 2
ENEMY_TIMERS = [300,350,500,550,650]  # How often the local enemies shoot.
PLAYER_TIMER = 250  # How often the player sends it's current position while at rest.
# Kafka Constants
BOOTSTRAP_SERVERS = "192.168.0.9:9092"
# Game States and Game Flow Constants
GAME_MENU = "menu"
GAME_PLAYING = "playing"


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
        self.cutout_rect = pygame.Rect(0, 0, 0, 0)
        self.health = MAX_HEALTH
        # TCOP - Step 1: Create a transparent surface for the player
        self.surface = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)

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
                game_bullets.append(bullet)
        # Heal at recovery speed.
        if self.health < MAX_HEALTH: self.health += HEALTH_RECOVERY_SPEED

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
        # TCOP - Step 2: Draw the full player
        pygame.draw.rect(self.surface, self.color, (0, 0, self.rect.width, self.rect.height))
        # TCOP - Step 3: Calculate "hurt" cutout
        hurt_percent = (MAX_HEALTH - self.health) / MAX_HEALTH
        cutout_size = int(20 * hurt_percent)
        self.cutout_rect.update(
            (self.rect.width - cutout_size) // 2,
            (self.rect.height - cutout_size) // 2,
            cutout_size,
            cutout_size
        )
        # TCOP - Step 4: "Cut out" the hurt area by clearing that part (make it transparent)
        self.surface.fill((0, 0, 0, 0), self.cutout_rect)
        # TCOP - Step 5: Blit the player surface into the screen.
        screen.blit(self.surface, self.rect)

# Enemy Class
class Enemy:
    def __init__(self, x, y, e, timer):
        self.rect = pygame.Rect(x, y, 20, 20)
        self.cutout_rect = pygame.Rect(0, 0, 0, 0)
        self.health = MAX_HEALTH
        self.x_way = random.choice([-1, 0, 1])
        self.y_way = random.choice([-1, 0, 1])
        self.shoot_timer = pygame.USEREVENT + e
        pygame.time.set_timer(self.shoot_timer, timer)
        # TCOP - Step 1: Create a transparent surface for the enemy
        self.surface = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)

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
        # Heal at recovery speed.
        if self.health < MAX_HEALTH: self.health += HEALTH_RECOVERY_SPEED

    def hit(self):
        self.health -= BULLET_HURT_SPEED

    def shoot(self, direction):
        return create_bullet(self.rect, direction)

    def draw(self, screen):
        # TCOP - Step 2: Draw the full enemy
        pygame.draw.rect(self.surface, ENEMY_COLOR, (0, 0, self.rect.width, self.rect.height))
        # TCOP - Step 3: Calculate "hurt" cutout
        hurt_percent = (MAX_HEALTH - self.health) / MAX_HEALTH
        cutout_size = int(20 * hurt_percent)
        self.cutout_rect.update(
            (self.rect.width - cutout_size) // 2,
            (self.rect.height - cutout_size) // 2,
            cutout_size,
            cutout_size
        )
        # TCOP - Step 4: "Cut out" the hurt area by clearing that part (make it transparent)
        self.surface.fill((0, 0, 0, 0), self.cutout_rect)
        # TCOP - Step 5: Blit the enemy surface into the screen.
        screen.blit(self.surface, self.rect)

# Remote Enemy Class
class RemoteEnemy:
    def __init__(self, x, y, keys):
        self.rect = pygame.Rect(x, y, 20, 20)
        self.cutout_rect = pygame.Rect(0, 0, 0, 0)
        self.health = MAX_HEALTH
        self.keys = keys
        # TCOP - Step 1: Create a transparent surface for the enemy
        self.surface = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)

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
        # Heal at recovery speed.
        if self.health < MAX_HEALTH: self.health += HEALTH_RECOVERY_SPEED

    def update_position_and_keys(self, x, y, keys):
        self.rect.x = x
        self.rect.y = y
        self.keys = keys

    def hit(self):
        self.health -= BULLET_HURT_SPEED

    def draw(self, screen):
        # TCOP - Step 2: Draw the full enemy
        pygame.draw.rect(self.surface, REMOTE_ENEMY_COLOR, (0, 0, self.rect.width, self.rect.height))
        # TCOP - Step 3: Calculate "hurt" cutout
        hurt_percent = (MAX_HEALTH - self.health) / MAX_HEALTH
        cutout_size = int(20 * hurt_percent)
        self.cutout_rect.update(
            (self.rect.width - cutout_size) // 2,
            (self.rect.height - cutout_size) // 2,
            cutout_size,
            cutout_size
        )
        # TCOP - Step 4: "Cut out" the hurt area by clearing that part (make it transparent)
        self.surface.fill((0, 0, 0, 0), self.cutout_rect)
        # TCOP - Step 5: Blit the enemy surface into the screen.
        screen.blit(self.surface, self.rect)

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


# Game Class
class Game:
    def __init__(self):
        print("Game init")


# Handling Kafka Messages in the Menu Loop
def get_map_from_idle(sender_id, data):
    global map
    msg_type = data.get("type")
    if msg_type in ["waiting-2-join", "wasd-update"]:
        map = data.get("map")
        b = [sum(x) for x in zip(*map)]
        print(f"[{sender_id}] {msg_type} {b}")

# Handling Kafka Messages in the Game Loop
def handle_kafka_message(sender_id, data):
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
            print (f"Created {sender_id} remote enemy on wasd-update message.")
    elif msg_type == "bullet-created":
        position = data.get("position")
        x, y = position[0], position[1]
        velocity = data.get("velocity")
        dx, dy = velocity[0], velocity[1]
        bullet = Bullet(x, y, dx, dy)
        game_bullets.append(bullet)
    elif msg_type == "player-spawn":
        position = data.get("position")
        x, y = position[0], position[1]
        keys = []
        enemy = RemoteEnemy(x, y, keys)
        remote_enemies[sender_id] = enemy
        print (f"Created {sender_id} remote enemy on player-spawn message.")        
    elif msg_type == "got-hit":        
        if sender_id in remote_enemies:
            enemy = remote_enemies.get(sender_id)
            enemy.hit()
    elif msg_type == "player-exit":
        print(f"[{sender_id}] player-exit")
        remote_enemies.pop(sender_id, None)

# Kafka Messaging
player_id = ''.join(random.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits) for _ in range(13))
messenger = KafkaMessenger(player_id, bootstrap_servers=BOOTSTRAP_SERVERS)
message_handler = KafkaMessageHandler(player_id, bootstrap_servers=BOOTSTRAP_SERVERS)

# # Try to read current map and last-activity
# map, last_activity_age = map_reader.read_map_and_last_activity_age()

# # Determine whether to reuse map or generate a new one
# reuse_map = False
# if map:
#     if last_activity_age:
#         if last_activity_age <= MAX_AGE_LAST_ACTIVITY:
#             reuse_map = True
#     else:
#         reuse_map = True
# # Apply the decision whether to reuse map or not.
# if reuse_map:
#     print("✅ Reusing maze from Kafka topic.")
#     maze = Maze(map=map)
# else:
#     print("🌀 Creating new maze and publishing to Kafka topic.")
#     maze = Maze(HEIGHT//WALL_PIXELS, WIDTH//WALL_PIXELS, WALL_PIXELS)  # Generate a new one
#     messenger.send_map(maze.map)

# # Create the player and the enemies
# # Create a list of open spaces
# open_spaces = [(r, c) for r in range(len(maze.map)) for c in range(len(maze.map[0])) if maze.map[r][c] == 0]
# # Spawn the player at a random open space
# r, c = random.choice(open_spaces)
# x = c * WALL_PIXELS + 20 * random.random()
# y = r * WALL_PIXELS + 20 * random.random()
# player = Player(x, y, PLAYER_COLOR)
# messenger.send_spawn((player.rect.x, player.rect.y))
# # Spawn the enemies at random open spaces
# enemies = []
# for e, timer in enumerate(ENEMY_TIMERS):
#     r, c = random.choice(open_spaces)
#     x = c * WALL_PIXELS + 20 * random.random()
#     y = r * WALL_PIXELS + 20 * random.random()
#     enemies.append(Enemy(x, y, e, timer))
# # Create a timer to send player's current position every 250 ms
# player_timer = pygame.USEREVENT + len(ENEMY_TIMERS)  # Get the next USEREVENT for the player_timer
# pygame.time.set_timer(player_timer, PLAYER_TIMER)

# game_bullets = []  # Centralized bullet magement
# prev_keys = []  # To detect WASD press/release changes
# remote_enemies = {}  # Identified by sender_id as the key.

# Background Surface with transparent black overlay black
background_surface = pygame.image.load('image/gotcha_aerial_view_3.png').convert()
dark_overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
dark_overlay.fill(BG_COLOR_ALPHA)

# Menu Screen
title_font = pygame.font.Font('font/Rock_Salt/RockSalt-Regular.ttf', 50)
title_surf = title_font.render('Laser Tag Kafka', True, TITLE_COLOR)
title_rect = title_surf.get_rect(center = (400,80))

WASD_surf = pygame.image.load('image/WASD_alpha_low.png').convert_alpha()
IJKL_surf = pygame.image.load('image/IJKL_alpha_low.png').convert_alpha()
WASD_rect = WASD_surf.get_rect(center = (250,300))
IJKL_rect = IJKL_surf.get_rect(center = (550,300))

instr_font = pygame.font.Font('font/Passero_One/PasseroOne-Regular.ttf', 50)
instr1_surf = instr_font.render('Move', True, INSTRUCTION_COLOR)
instr2_surf = instr_font.render('Shoot', True, INSTRUCTION_COLOR)
instr1_rect = instr1_surf.get_rect(center = (250, 410))
instr2_rect = instr2_surf.get_rect(center = (550, 410))

status_font = pygame.font.Font('font/ZCOOL_KuaiLe/ZCOOLKuaiLe-Regular.ttf', 50)
status_surf = status_font.render('Loading Map...', True, STATUS_COLOR)
status_rect = status_surf.get_rect(center = (400, 530))

instr3_surf = instr_font.render('Press <F5> to Join', True, INSTRUCTION_COLOR)
instr3_rect = instr3_surf.get_rect(center = (400, 530))

SHAKE_INTERVAL = 1500  # 1.5 seconds per set
SHAKE_DURATION = 900  # how long each shake lasts
SHAKE_ANGLE = 5  # max tilt angle
TIME_TO_GET_MAP = 6  # Number of seconds without map to generate a new map.

last_shake_start = pygame.time.get_ticks()
current_shake_set = "WASD"  # or "IJKL"

def blit_shaking_image(screen, surf, rect, angle):
    "Rotate the surface slightly, then re-blit at the center position."
    rotated_surf = pygame.transform.rotate(surf, angle)
    new_rect = rotated_surf.get_rect(center=rect.center)
    screen.blit(rotated_surf, new_rect)

player_timer = pygame.USEREVENT + len(ENEMY_TIMERS)  # Get the next USEREVENT for the player_timer
pygame.time.set_timer(player_timer, PLAYER_TIMER)

# Game Loop
game_state = GAME_MENU
menu_start_time = time.time()
map = None
maze = None
running = True
while running:
    # Draw background and then the dark overlay
    screen.blit(background_surface, (0, 0))
    screen.blit(dark_overlay, (0, 0))

    if game_state == GAME_MENU:
        screen.blit(title_surf, title_rect)
        now = pygame.time.get_ticks()
        shake_elapsed = now - last_shake_start

        if shake_elapsed > SHAKE_INTERVAL:
            # switch to next set (WASD <-> IJKL)
            current_shake_set = "IJKL" if current_shake_set == "WASD" else "WASD"
            last_shake_start = now

        # WASD
        if current_shake_set == "WASD":
            elapsed = pygame.time.get_ticks() - last_shake_start
            t = min(elapsed / SHAKE_DURATION, 1)  # from 0 to 1
            angle = math.sin(t * math.pi * 4) * SHAKE_ANGLE  # 2 full oscillations
            blit_shaking_image(screen, WASD_surf, WASD_rect, angle)
            blit_shaking_image(screen, instr1_surf, instr1_rect, -angle)
        else:
            screen.blit(WASD_surf, WASD_rect)
            screen.blit(instr1_surf, instr1_rect)

        # IJKL
        if current_shake_set == "IJKL": # and is_shaking:
            elapsed = pygame.time.get_ticks() - last_shake_start
            t = min(elapsed / SHAKE_DURATION, 1)  # from 0 to 1
            angle = math.sin(t * math.pi * 4) * SHAKE_ANGLE  # 2 full oscillations
            blit_shaking_image(screen, IJKL_surf, IJKL_rect, angle)
            blit_shaking_image(screen, instr2_surf, instr2_rect, -angle)
        else:
            screen.blit(IJKL_surf, IJKL_rect)
            screen.blit(instr2_surf, instr2_rect)

        # Get Map Logic
        message_handler.poll_messages(get_map_from_idle)
        if map:
            screen.blit(instr3_surf, instr3_rect)  # Show "Press <F5> to Join"
            if not maze:
                print("✅ Reusing map from Kafka topic.")
                maze = Maze(map=map)
        else:
            screen.blit(status_surf, status_rect)  # Show "Loading Map..."
            if maze is None:
                menu_elapsed = time.time() - menu_start_time
                if menu_elapsed >= TIME_TO_GET_MAP:
                    print("🌀 Creating new map.")
                    maze = Maze()  # Generate a new one
                    map = maze.map
                    messenger.send_waiting_2_join(map)

        pressed = pygame.key.get_pressed()
        if pressed[pygame.K_F5]:
            game_state = GAME_PLAYING
            print("Setting up the Game")
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == player_timer and map is not None:
                messenger.send_waiting_2_join(map)


    elif game_state == GAME_PLAYING:
        keys = []
        pressed = pygame.key.get_pressed()
        if pressed[pygame.K_w]: keys.append(pygame.K_w)
        if pressed[pygame.K_a]: keys.append(pygame.K_a)
        if pressed[pygame.K_s]: keys.append(pygame.K_s)
        if pressed[pygame.K_d]: keys.append(pygame.K_d)
        if keys != prev_keys:
            messenger.send_wasd_update((player.rect.x, player.rect.y), keys)
            prev_keys = keys
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key in [pygame.K_i, pygame.K_j, pygame.K_k, pygame.K_l]:
                bullet = player.process_buffer(event.key)
                if bullet:
                    messenger.send_bullet_created((bullet.rect.x+2, bullet.rect.y+2), (bullet.dx, bullet.dy))
                    game_bullets.append(bullet)
            elif event.type == player_timer:
                # Send player's current position only if the player is not moving.
                if len(keys) == 0: messenger.send_wasd_update((player.rect.x, player.rect.y), keys)
            else:
                for enemy in enemies:
                    if event.type == enemy.shoot_timer:
                        game_bullets.append(
                            enemy.shoot(random.choice(["up", "dn", "lf", "rt", "up-lf", "up-rt", "dn-lf", "dn-rt"]))
                        )
        message_handler.poll_messages(handle_kafka_message)

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

messenger.send_player_exit()
messenger.flush()
message_handler.close()
pygame.quit()
