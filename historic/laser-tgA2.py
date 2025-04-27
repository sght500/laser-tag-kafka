from kafka_messaging31 import KafkaMessenger, KafkaMessageHandler
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
BROWN_ALPHA = (128, 53, 14, 127)
TITLE_COLOR = (255, 255, 64)
INSTRUCTION_COLOR = (229, 229, 229)
# STATUS_COLOR = (99, 151, 203)
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
MAX_LOCAL_ENEMIES = 8  # How many local enemies, the most?
MIN_ENEMY_TIMER = 50  # How often the local enemies shoot, the least?
MAX_ENEMY_TIMER = 650  # How often the local enemies shoot, the most?
PLAYER_TIMER = 250  # How often the player sends it's current position while at rest.
# Kafka Constants
BOOTSTRAP_SERVERS = "192.168.0.9:9092"
# Game States and Game Flow Constants
GAME_MENU = "menu"
GAME_PLAYING = "playing"
GAME_WATCHING = "watching"
# Player Exit Reasons
PLAYER_DIED = "player-died"
PLAYER_WON = "player-won"
# Start Menu
SHAKE_INTERVAL = 1500  # 1.5 seconds per set
SHAKE_DURATION = 900  # how long each shake lasts
SHAKE_ANGLE = 5  # max tilt angle
TIME_TO_GET_MAP = 6  # Number of seconds without map to generate a new map.


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
                # global game_bullets # Fixes simple IJKL direction bullets. REMOVE THIS COMMENT.
                bullet = self.process_buffer(NO_KEY)
                messenger.send_bullet_created((bullet.rect.x+2, bullet.rect.y+2), (bullet.dx, bullet.dy))
                game.bullets.append(bullet)
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
        # Create a list of open spaces
        open_spaces = [(r, c) for r in range(len(maze.map)) for c in range(len(maze.map[0])) if maze.map[r][c] == 0]
        # Spawn the player at a random open space
        r, c = random.choice(open_spaces)
        x = c * WALL_PIXELS + 20 * random.random()
        y = r * WALL_PIXELS + 20 * random.random()
        self.player = Player(x, y, PLAYER_COLOR)
        messenger.send_spawn((self.player.rect.x, self.player.rect.y))
        # Randomize the number of local enemies and their shooter times.
        enemy_timers = random.sample(range(MIN_ENEMY_TIMER, MAX_ENEMY_TIMER), \
                                          random.randint(MAX_LOCAL_ENEMIES - 3, MAX_LOCAL_ENEMIES))
        # Spawn the enemies at random open spaces
        self.local_enemies = []
        for e, timer in enumerate(enemy_timers):
            r, c = random.choice(open_spaces)
            x = c * WALL_PIXELS + 20 * random.random()
            y = r * WALL_PIXELS + 20 * random.random()
            self.local_enemies.append(Enemy(x, y, e, timer))
        self.bullets = []  # Bullet magement at the game level.
        self.remote_enemies = {}  # Identified by sender_id as the key.

    def remove_player(self):
        self.player = None

    def health_check_enemies(self, screen):
        "Check the health of the enemies. Move them and draw them."
        for enemy in self.local_enemies[:]:
            if enemy.health <= 0:
                pygame.time.set_timer(enemy.shoot_timer, 0)
                self.local_enemies.remove(enemy)
            else:
                enemy.move(maze.bricks)
                enemy.draw(screen)
        for remote_id, enemy in list(self.remote_enemies.items()):
            if enemy.health <= 0:
                del self.remote_enemies[remote_id]
            else:
                enemy.move(maze.bricks)
                enemy.draw(screen)

    def bullet_collision_detection(self, screen):
        "Manage the game bullets. Check collisions. Draw the remaining bullets."
        for bullet in self.bullets:
            bullet.update()
            # Collision detection bullet vs wall
            if any(bullet.rect.colliderect(brick) for brick in maze.bricks):
                self.bullets.remove(bullet)
            elif self.player and bullet.rect.colliderect(self.player.rect):  # First check if the player exists.
                self.player.hit()
                self.bullets.remove(bullet)
            else:
                # Collision detection bullet vs enemies
                remove_bullet = False  # Fixes error: ValueError: list.remove(x): x not in list
                for enemy in self.local_enemies:
                    if bullet.rect.colliderect(enemy.rect):
                        enemy.hit()
                        remove_bullet = True
                for enemy in self.remote_enemies.values():
                    if bullet.rect.colliderect(enemy.rect):
                        remove_bullet = True
                if remove_bullet: self.bullets.remove(bullet)
        # Draw the remaining bullets
        for bullet in self.bullets:
            bullet.draw(screen)


# Handling Kafka Messages in the Menu Loop
def get_map_from_idle(sender_id, data):
    global map
    msg_type = data.get("type")
    if msg_type in ["waiting-2-join", "wasd-update"]:
        map = data.get("map")
        # b = [sum(x) for x in zip(*map)]
        # print(f"[{sender_id}] {msg_type} {b}")

# Handling Kafka Messages in the Game Loop
def handle_kafka_message(sender_id, data):
    msg_type = data.get("type")
    # global remote_enemies
    if msg_type == "wasd-update":
        position = data.get("position")
        x, y = position[0], position[1]
        keys = data.get("keys")
        if sender_id in game.remote_enemies:
            enemy = game.remote_enemies.get(sender_id)
            enemy.update_position_and_keys(x, y, keys)
        else:
            enemy = RemoteEnemy(x, y, keys)
            game.remote_enemies[sender_id] = enemy
            print (f"[{sender_id}] Created remote enemy on {msg_type}.")
    elif msg_type == "bullet-created":
        position = data.get("position")
        x, y = position[0], position[1]
        velocity = data.get("velocity")
        dx, dy = velocity[0], velocity[1]
        bullet = Bullet(x, y, dx, dy)
        game.bullets.append(bullet)
    elif msg_type == "player-spawn":
        position = data.get("position")
        x, y = position[0], position[1]
        keys = []
        enemy = RemoteEnemy(x, y, keys)
        game.remote_enemies[sender_id] = enemy
        print (f"[{sender_id}] Created remote enemy on {msg_type}.")
    elif msg_type == "got-hit":        
        if sender_id in game.remote_enemies:
            enemy = game.remote_enemies.get(sender_id)
            enemy.hit()
    elif msg_type == "player-exit":
        reason = data.get("reason")
        print(f"[{sender_id}] player-exit on {reason}")
        game.remote_enemies.pop(sender_id, None)

# Kafka Messaging
player_id = ''.join(random.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits) for _ in range(13))
messenger = KafkaMessenger(player_id, bootstrap_servers=BOOTSTRAP_SERVERS)
message_handler = KafkaMessageHandler(player_id, bootstrap_servers=BOOTSTRAP_SERVERS)

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

# status_font = pygame.font.Font('font/ZCOOL_KuaiLe/ZCOOLKuaiLe-Regular.ttf', 50)
# status_surf = status_font.render('Loading Map...', True, STATUS_COLOR)
# status_rect = status_surf.get_rect(center = (400, 530))

status_message = "Loading Map..."
status_font = pygame.font.Font('font/ZCOOL_KuaiLe/ZCOOLKuaiLe-Regular.ttf', 50)
status_start_time = pygame.time.get_ticks()  # Set this too when returning to Menu Screen. *********************
STATUS_COLOR_BASE = (99, 181, 255)
STATUS_COLOR_ALT = (150, 220, 255)  # for glowing flicker

instr3_surf = instr_font.render('Press <F5> to Join', True, INSTRUCTION_COLOR)
instr3_rect = instr3_surf.get_rect(center = (400, 530))

last_shake_start = pygame.time.get_ticks()
current_shake_set = "WASD"  # or "IJKL"

def blit_shaking_image(screen, surf, rect, angle):
    "Rotate the surface slightly, then re-blit at the center position."
    rotated_surf = pygame.transform.rotate(surf, angle)
    new_rect = rotated_surf.get_rect(center=rect.center)
    screen.blit(rotated_surf, new_rect)


# Watching Mode
font_big = pygame.font.Font('font/ZCOOL_KuaiLe/ZCOOLKuaiLe-Regular.ttf', 48)
font_small = pygame.font.Font('font/ZCOOL_KuaiLe/ZCOOLKuaiLe-Regular.ttf', 36)
# Kafka-style messages
messages = [
    ("All Lives Published", "Now Consuming Chaos"),
    ("Topic: player-dead", "Status: Spectator"),
    ("Your Actions Committed", "Now Reading the Logs"),
    ("Dead but Subscribed", "Waiting for Game Reset"),
    ("Reached End of Partition", "Spectating Mode Now")
]
brown_overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
brown_overlay.fill(BROWN_ALPHA)

player_timer = pygame.USEREVENT + MAX_LOCAL_ENEMIES  # Get the next USEREVENT for the player_timer
pygame.time.set_timer(player_timer, PLAYER_TIMER)
prev_keys = []  # To detect WASD press/release changes

# Main Loop
game_state = GAME_MENU
game = None  # This is the Game object
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
            # screen.blit(status_surf, status_rect)  # Show "Loading Map..."
            elapsed = pygame.time.get_ticks() - status_start_time
            char_count = min(len(status_message), elapsed // 100)  # one char every 100ms
            # Flicker/glow: sin wave between 0 and 1
            glow_phase = math.sin(pygame.time.get_ticks() / 200) * 0.5 + 0.5
            r = int(STATUS_COLOR_BASE[0] * (1 - glow_phase) + STATUS_COLOR_ALT[0] * glow_phase)
            g = int(STATUS_COLOR_BASE[1] * (1 - glow_phase) + STATUS_COLOR_ALT[1] * glow_phase)
            b = int(STATUS_COLOR_BASE[2] * (1 - glow_phase) + STATUS_COLOR_ALT[2] * glow_phase)
            color = (r, g, b)
            status_surf = status_font.render(status_message[:char_count], True, color)
            status_rect = status_surf.get_rect(center=(400, 530))
            screen.blit(status_surf, status_rect)

            if maze is None:
                menu_elapsed = time.time() - menu_start_time
                if menu_elapsed >= TIME_TO_GET_MAP:
                    print("🌀 Creating new map.")
                    maze = Maze()  # Generate a new one
                    map = maze.map
                    messenger.send_waiting_2_join(map)

        pressed = pygame.key.get_pressed()
        if pressed[pygame.K_F5] and maze:
            game_state = GAME_PLAYING
            game = Game()  # Initialize the game.
            pygame.time.set_timer(player_timer, PLAYER_TIMER)
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
            messenger.send_wasd_update((game.player.rect.x, game.player.rect.y), keys, map)
            prev_keys = keys
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key in [pygame.K_i, pygame.K_j, pygame.K_k, pygame.K_l]:
                bullet = game.player.process_buffer(event.key)
                if bullet:
                    messenger.send_bullet_created((bullet.rect.x+2, bullet.rect.y+2), (bullet.dx, bullet.dy))
                    game.bullets.append(bullet)
            elif event.type == player_timer:
                # Send player's current position only if the player is not moving.
                if len(keys) == 0: messenger.send_wasd_update((game.player.rect.x, game.player.rect.y), keys, map)
            else:
                for enemy in game.local_enemies:
                    if event.type == enemy.shoot_timer:
                        game.bullets.append(
                            enemy.shoot(random.choice(["up", "dn", "lf", "rt", "up-lf", "up-rt", "dn-lf", "dn-rt"]))
                        )
        # Return to Menu?
        if len(game.remote_enemies) == 0 and len(game.local_enemies) == 0:
            game_state = GAME_MENU
            game = None  # This is the Game object
            menu_start_time = time.time()  # Don't add random number. Be the map leader.
            status_start_time = pygame.time.get_ticks()  # Initialize the typing effect.
            map = None
            maze = None
            messenger.send_player_exit(reason=PLAYER_WON)
            continue

        message_handler.poll_messages(handle_kafka_message)

        maze.draw(screen)

        game.player.move(keys, maze.bricks)
        game.player.draw(screen)
        
        # Health check
        if game.player.health <= 0:
            pygame.time.set_timer(player_timer, 0)
            game.remove_player()
            messenger.send_player_exit(reason=PLAYER_DIED)
            # Watching Mode? or Menu Screen?
            if len(game.remote_enemies) == 0:
                game_state = GAME_MENU
                game = None  # This is the Game object
                menu_start_time = time.time()
                status_start_time = pygame.time.get_ticks()  # Initialize the typing effect.
                map = None
                maze = None
                continue
            else:
                game_state = GAME_WATCHING
                # Prepare heart-pumping message
                message_index = 0
                last_message_switch = pygame.time.get_ticks()
                continue
        game.health_check_enemies(screen)
        game.bullet_collision_detection(screen)


    elif game_state == GAME_WATCHING:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                for enemy in game.local_enemies:
                    if event.type == enemy.shoot_timer:
                        game.bullets.append(
                            enemy.shoot(random.choice(["up", "dn", "lf", "rt", "up-lf", "up-rt", "dn-lf", "dn-rt"]))
                        )
        # Return to Menu?
        if len(game.remote_enemies) == 0:
            game_state = GAME_MENU
            game = None  # This is the Game object
            menu_start_time = time.time() + random.uniform(3, 9)
            status_start_time = pygame.time.get_ticks()  # Initialize the typing effect.
            map = None
            maze = None
            continue
        message_handler.poll_messages(handle_kafka_message)

        maze.draw(screen)

        game.health_check_enemies(screen)
        game.bullet_collision_detection(screen)

        # Pulsing scale factor
        t = pygame.time.get_ticks() / 1000  # seconds
        pulse = 1 + 0.05 * math.sin(t * 3)  # oscillate between 0.95 and 1.05

        # Select an spectator message
        now = pygame.time.get_ticks()
        if now - last_message_switch > 8000:
            message_index = (message_index + 1) % len(messages)
            last_message_switch = now
        spectator_line1, spectator_line2 = messages[message_index]

        # Render text
        text1 = font_big.render(spectator_line1, True, (255, 50, 50))  # Reddish
        text2 = font_small.render(spectator_line2, True, (255, 255, 255))

        # Scale text surfaces
        text1_scaled = pygame.transform.rotozoom(text1, 0, pulse)
        text2_scaled = pygame.transform.rotozoom(text2, 0, pulse)

        # Position at center
        text1_rect = text1_scaled.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 30))
        text2_rect = text2_scaled.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30))

        # Blit to screen
        screen.blit(brown_overlay, (0, 0))
        screen.blit(text1_scaled, text1_rect)
        screen.blit(text2_scaled, text2_rect)


    pygame.display.flip()
    clock.tick(60)

messenger.send_player_exit()
messenger.flush()
message_handler.close()
pygame.quit()
