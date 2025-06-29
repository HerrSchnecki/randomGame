from ursina import *
from block import BlockRegistry
from biomes import PlainsBiome, MountainBiome

CHUNK_SIZE = 16
CHUNK_HEIGHT = 16

class Chunk(Entity):
    def __init__(self, world, chunk_x, chunk_z, biome):
        super().__init__(parent=world)
        self.chunk_x = chunk_x
        self.chunk_z = chunk_z
        self.biome = biome
        self.blocks = []
        self.generate()

    def generate(self):
        start_x = self.chunk_x * CHUNK_SIZE
        start_z = self.chunk_z * CHUNK_SIZE

        for x in range(CHUNK_SIZE):
            for z in range(CHUNK_SIZE):
                for y in range(CHUNK_HEIGHT):
                    world_x = start_x + x
                    world_y = y
                    world_z = start_z + z

                    block_type = self.biome.generate_block(world_x, world_y, world_z)
                    if block_type != 'air':
                        block = BlockRegistry.create(block_type, position=(world_x, world_y, world_z), parent=self)
                        self.blocks.append(block)

class World(Entity):
    def __init__(self):
        super().__init__()
        self.chunks = {}
        self.biomes = [PlainsBiome(), MountainBiome()]

    def generate_chunk(self, chunk_x, chunk_z):
        biome = self.choose_biome(chunk_x, chunk_z)
        chunk = Chunk(self, chunk_x, chunk_z, biome)
        self.chunks[(chunk_x, chunk_z)] = chunk

    def choose_biome(self, chunk_x, chunk_z):
        if (chunk_x + chunk_z) % 2 == 0:
            return self.biomes[0]
        else:
            return self.biomes[1]

    def generate_area(self, radius=1):
        for x in range(-radius, radius+1):
            for z in range(-radius, radius+1):
                if (x, z) not in self.chunks:
                    self.generate_chunk(x, z)
