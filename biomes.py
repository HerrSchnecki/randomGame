from random import randint

class Biome:
    def __init__(self, name):
        self.name = name

    def generate_block(self, x, y, z):
        """Gibt den Blocktyp an Position zurück."""
        return 'air'

class PlainsBiome(Biome):
    def __init__(self):
        super().__init__('Plains')

    def generate_block(self, x, y, z):
        if y == 0:
            return 'grass'
        elif y < 0:
            return 'dirt'
        else:
            return 'air'

class MountainBiome(Biome):
    def __init__(self):
        super().__init__('Mountain')

    def generate_block(self, x, y, z):
        height = 5 + (x % 3)
        if y == height:
            return 'stone'
        elif y < height:
            return 'dirt'
        else:
            return 'air'
