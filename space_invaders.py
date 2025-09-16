"""Space Invaders clone implemented with pygame.

This script recreates the feel of the classic 1978 Space Invaders arcade game.
It features multiple waves of aliens, player and alien projectiles, score and
lives tracking, and a restartable game loop.  All graphics are rendered with
simple vector art so the game works out-of-the-box without any asset files.

Run the script with ``python space_invaders.py`` after installing pygame.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable, Optional

import pygame

# Screen configuration
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
FPS = 60

# Fleet configuration
ALIEN_ROWS = 5
ALIEN_COLS = 10
ALIEN_HORIZONTAL_PADDING = 12
ALIEN_VERTICAL_PADDING = 18
ALIEN_DROP_DISTANCE = 24
ALIEN_BASE_SPEED = 55
ALIEN_SPEED_INCREMENT = 12

# Player configuration
PLAYER_SPEED = 320
PLAYER_LIVES = 3
PLAYER_SHOT_COOLDOWN = 0.35  # seconds
PLAYER_INVULNERABLE_TIME = 2.0  # seconds after being hit

# Projectile configuration
PLAYER_LASER_SPEED = -520
ALIEN_LASER_SPEED = 280

# Colours
BACKGROUND_COLOR = (10, 10, 30)
PLAYER_COLOR = (0, 255, 120)
PLAYER_GLOW = (0, 180, 120)
ALIEN_COLORS = [
    (68, 170, 255),
    (100, 200, 255),
    (80, 220, 180),
    (255, 220, 120),
    (255, 120, 150),
]
LASER_COLOR = (255, 255, 255)
ALIEN_LASER_COLOR = (255, 110, 60)
HUD_COLOR = (220, 220, 220)


@dataclass
class GameStats:
    """Tracks mutable score-related state."""

    score: int = 0
    level: int = 1

    def add_score(self, base_value: int, multiplier: int = 1) -> None:
        self.score += base_value * multiplier

    def next_level(self) -> None:
        self.level += 1


class Laser(pygame.sprite.Sprite):
    """Projectile fired by the player or aliens."""

    def __init__(self, start_pos: tuple[int, int], speed: float, color: tuple[int, int, int]):
        super().__init__()
        self.image = pygame.Surface((4, 18), pygame.SRCALPHA)
        pygame.draw.rect(self.image, color, self.image.get_rect())
        self.rect = self.image.get_rect(center=start_pos)
        self.speed = speed

    def update(self, dt: float) -> None:
        self.rect.y += int(self.speed * dt)
        if self.rect.bottom < 0 or self.rect.top > WINDOW_HEIGHT:
            self.kill()


class Player(pygame.sprite.Sprite):
    """Represents the player cannon."""

    def __init__(self, start_pos: tuple[int, int]):
        super().__init__()
        self.image = pygame.Surface((54, 32), pygame.SRCALPHA)
        self._base_image = self.image.copy()
        self._draw_player_shape()
        self.rect = self.image.get_rect(midbottom=start_pos)
        self.speed = PLAYER_SPEED
        self.lives = PLAYER_LIVES
        self._shot_cooldown = PLAYER_SHOT_COOLDOWN
        self._time_since_shot = PLAYER_SHOT_COOLDOWN
        self._invulnerable_timer = 0.0

    def _draw_player_shape(self) -> None:
        surface = self._base_image
        surface.fill((0, 0, 0, 0))
        rect = surface.get_rect()
        pygame.draw.rect(surface, PLAYER_GLOW, (rect.width // 2 - 2, rect.height - 4, 4, 4))
        pygame.draw.rect(surface, PLAYER_COLOR, (rect.width // 2 - 18, rect.height - 14, 36, 14))
        pygame.draw.rect(surface, PLAYER_COLOR, (rect.width // 2 - 10, rect.height - 24, 20, 10))
        pygame.draw.rect(surface, PLAYER_COLOR, (rect.width // 2 - 4, rect.height - 30, 8, 6))
        self.image.blit(surface, (0, 0))

    def update(self, dt: float, pressed_keys: Iterable[bool]) -> None:
        movement = 0
        if pressed_keys[pygame.K_LEFT] or pressed_keys[pygame.K_a]:
            movement -= 1
        if pressed_keys[pygame.K_RIGHT] or pressed_keys[pygame.K_d]:
            movement += 1
        self.rect.x += int(movement * self.speed * dt)
        self.rect.left = max(self.rect.left, 32)
        self.rect.right = min(self.rect.right, WINDOW_WIDTH - 32)

        self._time_since_shot += dt
        if self._invulnerable_timer > 0:
            self._invulnerable_timer = max(0.0, self._invulnerable_timer - dt)
            alpha = 100 if int(self._invulnerable_timer * 10) % 2 == 0 else 255
            self.image.set_alpha(alpha)
        else:
            self.image.set_alpha(255)

    def can_shoot(self) -> bool:
        return self._time_since_shot >= self._shot_cooldown

    def shoot(self) -> Laser:
        self._time_since_shot = 0.0
        return Laser(self.rect.midtop, PLAYER_LASER_SPEED, LASER_COLOR)

    def hit(self) -> bool:
        if self._invulnerable_timer > 0:
            return False
        self.lives -= 1
        self._invulnerable_timer = PLAYER_INVULNERABLE_TIME
        return self.lives > 0

    @property
    def invulnerable(self) -> bool:
        return self._invulnerable_timer > 0


class Alien(pygame.sprite.Sprite):
    """Represents a single alien in the fleet."""

    def __init__(self, position: tuple[int, int], color: tuple[int, int, int], column: int):
        super().__init__()
        self.image = pygame.Surface((44, 32), pygame.SRCALPHA)
        self._draw_shape(color)
        self.rect = self.image.get_rect(topleft=position)
        self.column = column

    def _draw_shape(self, color: tuple[int, int, int]) -> None:
        surface = self.image
        surface.fill((0, 0, 0, 0))
        rect = surface.get_rect()
        body_rect = pygame.Rect(4, 10, rect.width - 8, rect.height - 14)
        pygame.draw.rect(surface, color, body_rect)
        pygame.draw.rect(surface, color, (rect.width // 2 - 8, rect.height - 12, 16, 8))
        pygame.draw.circle(surface, color, (rect.width // 4, 14), 6)
        pygame.draw.circle(surface, color, (rect.width - rect.width // 4, 14), 6)
        pygame.draw.rect(surface, (0, 0, 0), (rect.width // 4 - 2, 14 - 2, 4, 4))
        pygame.draw.rect(surface, (0, 0, 0), (rect.width - rect.width // 4 - 2, 14 - 2, 4, 4))


class SpaceInvaders:
    """Main game controller."""

    ALIEN_SHOOT_EVENT = pygame.USEREVENT + 1

    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Space Invaders")
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font_small = pygame.font.Font(None, 36)
        self.font_large = pygame.font.Font(None, 72)

        self.stats = GameStats()
        self.running = True
        self.game_over = False
        self.alien_speed = ALIEN_BASE_SPEED
        self.alien_direction = 1
        self._laser_group = pygame.sprite.Group()
        self._alien_lasers = pygame.sprite.Group()
        self._player_group = pygame.sprite.GroupSingle()
        self._alien_group = pygame.sprite.Group()

        self._setup_new_game(reset_score=True)

    def _setup_new_game(self, reset_score: bool = False) -> None:
        self._laser_group.empty()
        self._alien_lasers.empty()
        self._alien_group.empty()
        self._player_group.empty()

        if reset_score:
            self.stats = GameStats()

        self.player = Player((WINDOW_WIDTH // 2, WINDOW_HEIGHT - 40))
        self._player_group.add(self.player)

        self._create_alien_fleet()
        self.alien_speed = ALIEN_BASE_SPEED + (self.stats.level - 1) * ALIEN_SPEED_INCREMENT
        self.alien_direction = 1
        self.game_over = False
        self._update_alien_fire_timer()

    def _create_alien_fleet(self) -> None:
        top_margin = 80
        left_margin = 100
        for row in range(ALIEN_ROWS):
            color = ALIEN_COLORS[row % len(ALIEN_COLORS)]
            for col in range(ALIEN_COLS):
                x = left_margin + col * (44 + ALIEN_HORIZONTAL_PADDING)
                y = top_margin + row * (32 + ALIEN_VERTICAL_PADDING)
                alien = Alien((x, y), color, col)
                self._alien_group.add(alien)

    def _update_alien_fire_timer(self) -> None:
        delay = max(250, 780 - (self.stats.level - 1) * 70)
        pygame.time.set_timer(self.ALIEN_SHOOT_EVENT, delay)

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self._handle_events()
            if not self.game_over:
                self._update(dt)
            self._draw()

        pygame.quit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_SPACE and not self.game_over:
                    self._handle_player_fire()
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.game_over:
                    self._setup_new_game(reset_score=True)
            elif event.type == self.ALIEN_SHOOT_EVENT and not self.game_over:
                self._alien_fire()

    def _handle_player_fire(self) -> None:
        if not self.player.can_shoot():
            return
        laser = self.player.shoot()
        self._laser_group.add(laser)

    def _alien_fire(self) -> None:
        shooter = self._choose_alien_shooter()
        if shooter is None:
            return
        start_pos = shooter.rect.midbottom
        laser = Laser(start_pos, ALIEN_LASER_SPEED, ALIEN_LASER_COLOR)
        self._alien_lasers.add(laser)

    def _choose_alien_shooter(self) -> Optional[Alien]:
        if not self._alien_group:
            return None
        columns: dict[int, list[Alien]] = {}
        for alien in self._alien_group.sprites():
            columns.setdefault(alien.column, []).append(alien)
        column_index = random.choice(list(columns.keys()))
        column_aliens = columns[column_index]
        return max(column_aliens, key=lambda alien: alien.rect.y)

    def _update(self, dt: float) -> None:
        pressed_keys = pygame.key.get_pressed()
        self.player.update(dt, pressed_keys)
        self._laser_group.update(dt)
        self._alien_lasers.update(dt)
        self._update_aliens(dt)
        self._handle_collisions()

        if not self._alien_group:
            self.stats.next_level()
            self.alien_speed = ALIEN_BASE_SPEED + (self.stats.level - 1) * ALIEN_SPEED_INCREMENT
            self._create_alien_fleet()
            self._update_alien_fire_timer()

    def _update_aliens(self, dt: float) -> None:
        dx = self.alien_direction * self.alien_speed * dt
        drop = False
        for alien in self._alien_group.sprites():
            alien.rect.x += int(dx)
            if alien.rect.right >= WINDOW_WIDTH - 40 and self.alien_direction > 0:
                drop = True
            elif alien.rect.left <= 40 and self.alien_direction < 0:
                drop = True

        if drop:
            for alien in self._alien_group.sprites():
                alien.rect.y += ALIEN_DROP_DISTANCE
            self.alien_direction *= -1
            self.alien_speed *= 1.05

        # Check if any alien reached the player level.
        for alien in self._alien_group.sprites():
            if alien.rect.bottom >= self.player.rect.top:
                self._trigger_game_over()
                break

    def _handle_collisions(self) -> None:
        hits = pygame.sprite.groupcollide(self._alien_group, self._laser_group, True, True)
        if hits:
            self.stats.add_score(100, multiplier=len(hits))

        if pygame.sprite.spritecollide(self.player, self._alien_group, False):
            self._trigger_game_over()
            return

        if pygame.sprite.spritecollide(self.player, self._alien_lasers, True):
            surviving = self.player.hit()
            if not surviving:
                self._trigger_game_over()

        pygame.sprite.groupcollide(self._laser_group, self._alien_lasers, True, True)

    def _trigger_game_over(self) -> None:
        self.game_over = True
        self._laser_group.empty()
        self._alien_lasers.empty()

    def _draw(self) -> None:
        self.screen.fill(BACKGROUND_COLOR)
        self._alien_group.draw(self.screen)
        self._laser_group.draw(self.screen)
        self._alien_lasers.draw(self.screen)
        self._player_group.draw(self.screen)

        self._draw_hud()

        if self.game_over:
            self._draw_game_over_overlay()

        pygame.display.flip()

    def _draw_hud(self) -> None:
        score_surface = self.font_small.render(f"Score: {self.stats.score}", True, HUD_COLOR)
        level_surface = self.font_small.render(f"Level: {self.stats.level}", True, HUD_COLOR)
        lives_surface = self.font_small.render(f"Lives: {self.player.lives}", True, HUD_COLOR)
        self.screen.blit(score_surface, (24, 20))
        self.screen.blit(level_surface, (24, 52))
        self.screen.blit(lives_surface, (WINDOW_WIDTH - lives_surface.get_width() - 24, 20))

    def _draw_game_over_overlay(self) -> None:
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        game_over_text = self.font_large.render("Game Over", True, HUD_COLOR)
        prompt_text = self.font_small.render("Press Enter to play again", True, HUD_COLOR)
        score_text = self.font_small.render(f"Final Score: {self.stats.score}", True, HUD_COLOR)

        rect = game_over_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 40))
        self.screen.blit(game_over_text, rect)
        self.screen.blit(score_text, score_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 10)))
        self.screen.blit(prompt_text, prompt_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 60)))


def main() -> None:
    game = SpaceInvaders()
    game.run()


if __name__ == "__main__":
    main()
