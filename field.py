"""
@copyright: 2012, Niels Thykier <niels@thykier.net>
@license:
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

import operator

from position import Pos
from direction import Direction

class Position(Pos):

    def dir_pos(self, direction):
        return self + Direction.dir_update(direction)

class Field(object):
    def __init__(self, symbol):
        self._symbol = symbol
        self._is_source = False
        self._is_target = False
        self._activated = False
        self._targets = set()
        self._sources = set()
        self._pos = None


    @property
    def position(self):
        return self._pos

    @property
    def symbol(self):
        return self._symbol

    @property
    def activated(self):
        return self._activated

    @property
    def can_enter(self):
        return True

    @property
    def is_activation_source(self):
        return self._is_source

    @property
    def is_activation_target(self):
        return self._is_target

    @property
    def x(self):
        return self._pos.x

    @property
    def y(self):
        return self._pos.y

    def add_activation_target(self, target):
        if not self.is_activation_source:
            raise NotImplementedError("%s is not an activation source" % self.symbol)
        if not target.is_activation_target:
            raise ValueError("%s is not an activation target" % self.symbol)

        self._targets.add(target)
        target._add_source(self)

    def _add_source(self, source):
        self._sources.add(source)

    def _set_position(self, pos):
        self._pos = pos

    def iter_activation_targets(self):
        # Technically we could just do return sorted(...), but this
        # way we force it to be an iterator and require the "iter()"
        # call.
        return (x for x in sorted(self._targets, key=operator.attrgetter("position")))

    def iter_activation_sources(self):
        # Technically we could just do return sorted(...), but this
        # way we force it to be an iterator and require the "iter()"
        # call.
        return (x for x in sorted(self._sources, key=operator.attrgetter("position")))

    @property
    def is_wall(self):
        return False

    def toogle_activation(self, newstate=None):
        pass

    def on_enter(self, obj):
        pass

    def activate(self):
        if not self._activated:
            self._activated = True
            self.toogle_activation(True)

    def deactivate(self):
        if self._activated:
            self._activated = False
            self.toogle_activation(False)

class Wall(Field):

    def __init__(self, symbol):
        super(Wall, self).__init__(symbol)

    @property
    def is_wall(self):
        return True

    @property
    def can_enter(self):
        return False

class Gate(Field):

    def __init__(self, symbol):
        super(Gate, self).__init__(symbol)
        self.closed = True
        self._is_target = True
        if symbol == "_":
            self.closed = False

    def toogle_activation(self, _=True):
        # invert our state
        self.closed = not self.closed
        if self.closed:
            self._sym = '-'
        else:
            self._sym = '_'

    @property
    def can_enter(self):
        return not self.closed

class Button(Field):

    def __init__(self, symbol):
        super(Button, self).__init__(symbol)
        self._is_source = True

    def toogle_activation(self, newstate=None):
        if newstate is None:
            newstate = not self.activated
        for target in self._targets:
            if newstate:
                target.activate()
            else:
                target.deactivate()

class StartLocation(Field):

    def __init__(self, symbol):
        super(StartLocation, self).__init__(symbol)

class GoalLocation(Field):

    def __init__(self, symbol):
        super(GoalLocation, self).__init__(symbol)

def parse_field(symbol):
    if symbol == "+":
        return Wall(symbol)
    if symbol == "-" or symbol == "_":
        return Gate(symbol)
    if symbol == " " or symbol == "c":
        # crates are always ontop of a "field"
        return Field(symbol)
    if symbol == "b" or symbol == "B":
        return Button(symbol)
    if symbol == "S":
        return StartLocation(symbol)
    if symbol == "G":
        return GoalLocation(symbol)
    raise IOError("Unknown symbol %s" % symbol)
