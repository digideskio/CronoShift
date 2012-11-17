"""
Taken (with modification) from:
  https://bitbucket.org/thesheep/qq/src/1090d7e5537f/qq.py?at=default

@copyright: 2008, 2009 Radomir Dopieralski <qq@sheep.art.pl>
@license: BSD
                           BSD LICENSE

Copyright (c) 2008, 2009, Radomir Dopieralski
All rights reserved. 

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

 * Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.

 * Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in
   the documentation and/or other materials provided with the
   distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import pygame
import operator
import functools

from chrono.model.field import Position
from chrono.model.direction import Direction

from chrono.view.tile_cache import TileCache

# Dimensions of the map tiles
MAP_TILE_WIDTH = 24
MAP_TILE_HEIGHT = 16

TL_FACTOR = Position(MAP_TILE_WIDTH, MAP_TILE_HEIGHT)
TL_OFFSET = Position(MAP_TILE_WIDTH/2, MAP_TILE_HEIGHT)

GATE_OPEN = 0
GATE_CLOSED = 1

def lpos2gpos(lpos, c=(0,0)):
    return Position(lpos[0] * TL_FACTOR.x + TL_OFFSET.x + c[0],
                    lpos[1] * TL_FACTOR.y + TL_OFFSET.y + c[1])

def gpos2lpos(gpos, c=(0,0)):
    return Position((gpos[0] - TL_OFFSET.x - c[0]) / TL_FACTOR.x,
                    (gpos[1] - TL_OFFSET.y - c[1]) / TL_FACTOR.y)

class SortedUpdates(pygame.sprite.RenderUpdates):
    """A sprite group that sorts them by depth."""

    def sprites(self):
        """The list of sprites in the group, sorted by depth."""

        return sorted(self.spritedict.keys(), key=operator.attrgetter("depth"))

class Shadow(pygame.sprite.Sprite):
    """Sprite for shadows."""

    def __init__(self, owner, sprite, pos=None):
        pygame.sprite.Sprite.__init__(self)
        self.image = sprite
        self.image.set_alpha(64)
        self.rect = self.image.get_rect()
        self.owner = owner
        if pos:
            self.rect.midbottom = lpos2gpos(pos)

    def update(self, *args):
        """Make the shadow follow its owner."""

        if self.owner:
            self.rect.midbottom = self.owner.rect.midbottom

class Sprite(pygame.sprite.Sprite):
    """Sprite for animated items and base class for Player."""

    is_player = False

    def __init__(self, pos, frames, c_pos=None, c_depth=None):
        super(Sprite, self).__init__()
        self.frames = frames
        self._c_pos = c_pos if c_pos else Position(0, 0)
        self._c_depth = c_depth if c_depth else 0
        self.image = self.frames[0][0]
        self.rect = self.image.get_rect()
        self.animation = self.stand_animation()
        self.pos = pos
        self._state = 0

    @property
    def pos(self):
        """Check the current position of the sprite on the map."""

        return gpos2lpos(self.rect.midbottom, self._c_pos)

    @pos.setter
    def pos(self, pos):
        """Set the position and depth of the sprite on the map."""

        self.rect.midbottom = lpos2gpos(pos, self._c_pos)
        self.depth = self.rect.midbottom[1] + self._c_depth

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, new_state):
        self.image = self.frames[new_state][0]
        self._state = new_state

    def move(self, pos):
        """Change the position of the sprite on screen."""

        self.rect.move_ip(pos[0], pos[1])
        self.depth = self.rect.midbottom[1]

    def stand_animation(self):
        """The default animation."""

        while True:
            # Change to next frame every two ticks
            for frame in self.frames[self.state]:
                self.image = frame
                yield None
                yield None

    def update(self, *args):
        """Run the current animation."""

        self.animation.next()

class MoveableSprite(Sprite):
    """ Display and animate the moveable objects."""
    def __init__(self, pos, frames, c_pos=None, c_depth=None):
        Sprite.__init__(self, pos, frames, c_pos=c_pos, c_depth=c_depth)
        self.direction = 0
        self.animation = None
        self.image = self.frames[0][0]

    def do_nothing_animation(self):
        """Fake animation for timing purposes"""

        # This animation is hardcoded for 4 frames and 16x24 map tiles
        for frame in range(4):
            yield None
            yield None

    def walk_animation(self):
        """Animation for the player walking."""

        # This animation is hardcoded for 4 frames and 16x24 map tiles
        d = self.direction
        dpos = Direction.dir_update(d)
        for frame in range(4):
            if d < len(self.frames) and frame < len(self.frames[d]):
                self.image = self.frames[d][frame]
            else:
                self.image = self.frames[0][0]
            yield None
            self.move(Position(3*dpos.x, 2*dpos.y))
            yield None
            self.move(Position(3*dpos.x, 2*dpos.y))

    def update(self, *args):
        """Run the current animation or just stand there if no animation set."""

        if self.animation is None:
            if self.direction < len(self.frames):
                self.image = self.frames[self.direction][0]
            else:
                self.image = self.frames[0][0]
        else:
            try:
                self.animation.next()
            except StopIteration:
                self.animation = None

class PlayerSprite(MoveableSprite):
    """ Display and animate the player character."""

    is_player = True

    def __init__(self, player, frames):
        MoveableSprite.__init__(self, player.position, frames)
        self.direction = Direction.EAST
        self.image = self.frames[self.direction][0]

def update_background(tiles, background, level, field, fixup=False, overlays=None):
    pos = field.position
    if overlays is None:
        overlays = {}
    def wall(pos):
        if 0 <= pos.x < level.width and 0 <= pos.y < level.height:
            return level.get_field(pos).is_wall
        return True

    wall_dir2 = lambda pos, d: wall(pos.dir_pos(d))
    wall_dir = functools.partial(wall_dir2, pos)

    if wall(pos):
        tile = 3, 3
        # Draw different tiles depending on neighbourhood
        if not wall_dir(Direction.SOUTH):
            if wall_dir(Direction.WEST) and wall_dir(Direction.EAST):
                tile = 1, 2
            elif wall_dir(Direction.EAST):
                tile = 0, 2
            elif wall_dir(Direction.WEST):
                tile = 2, 2
            else:
                tile = 3, 2
        else:
            south = pos.dir_pos(Direction.SOUTH)
            if wall_dir2(south, Direction.EAST) and wall_dir2(south, Direction.WEST):
                # Walls at SW, S and SE
                tile = 1, 1
            elif wall_dir2(south, Direction.EAST):
                # Walls at S and SE
                tile = 0, 1
            elif wall_dir2(south, Direction.WEST):
                # Walls at SW and S
                tile = 2, 1
            else:
                tile = 3, 1
        # Add overlays if the wall may be obscuring something
        if not wall_dir(Direction.NORTH):
            if wall_dir(Direction.EAST) and wall_dir(Direction.WEST):
                over = 1, 0
            elif wall_dir(Direction.EAST):
                over = 0, 0
            elif wall_dir(Direction.WEST):
                over = 2, 0
            else:
                over = 3, 0
            overlays[pos] = tiles[over[0]][over[1]]
    else:
        tile = 0, 3
    tile_image = tiles[tile[0]][tile[1]]
    background.blit(tile_image,
                    (field.x * MAP_TILE_WIDTH, field.y * MAP_TILE_HEIGHT))

    if fixup:
        for d in (Direction.NORTH, Direction.SOUTH, Direction.WEST, Direction.EAST):
            ff = level.get_field(field.position.dir_pos(d))
            update_background(tiles, background, level, ff, fixup=False, overlays=overlays)

    return overlays

def make_background(level, tileset=None, map_cache=None):
    if tileset is None:
        tileset = "tileset" # default is literally "tileset"
    if map_cache is None:
        self._map_cache = TileCache(MAP_TILE_WIDTH, MAP_TILE_HEIGHT)
    tiles = map_cache[tileset]
    gates = {}
    image = pygame.Surface((level.width*MAP_TILE_WIDTH,
                            level.height*MAP_TILE_HEIGHT))
    overlays = {}
    ub = functools.partial(update_background, tiles, image, level, overlays=overlays)

    for field in level.iter_fields():
        ub(field)
    return image, overlays
    
