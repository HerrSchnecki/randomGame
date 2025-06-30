import random
import math
import time
from collections import defaultdict
from ursina import *
from block import BlockRegistry


class SimpleNoise:
    """Einfache und schnelle Noise-Implementierung"""
    
    def __init__(self, seed=0):
        random.seed(seed)
        self.perm = [i for i in range(256)]
        random.shuffle(self.perm)
        self.perm *= 2
    
    def noise2d(self, x, z, scale=1.0):
        """Einfache 2D Noise Funktion"""
        x *= scale
        z *= scale
        
        # Integer Koordinaten
        xi = int(x) & 255
        zi = int(z) & 255
        
        # Fractional Koordinaten
        xf = x - int(x)
        zf = z - int(z)
        
        # Fade Kurven
        u = self._fade(xf)
        v = self._fade(zf)
        
        # Hash Koordinaten
        aa = self.perm[self.perm[xi] + zi]
        ab = self.perm[self.perm[xi] + zi + 1]
        ba = self.perm[self.perm[xi + 1] + zi]
        bb = self.perm[self.perm[xi + 1] + zi + 1]
        
        # Interpolation
        x1 = self._lerp(self._grad(aa, xf, zf), self._grad(ba, xf - 1, zf), u)
        x2 = self._lerp(self._grad(ab, xf, zf - 1), self._grad(bb, xf - 1, zf - 1), u)
        
        return self._lerp(x1, x2, v)
    
    def _fade(self, t):
        return t * t * t * (t * (t * 6 - 15) + 10)
    
    def _lerp(self, a, b, t):
        return a + t * (b - a)
    
    def _grad(self, hash_val, x, z):
        h = hash_val & 15
        u = x if h < 8 else z
        v = z if h < 4 else (x if h == 12 or h == 14 else 0)
        return (u if (h & 1) == 0 else -u) + (v if (h & 2) == 0 else -v)


class FastWorldGenerator:
    """Optimierter World Generator - Einfach und Schnell"""
    
    # Block Typen
    BLOCKS = {
        'grass': 0,
        'dirt': 1, 
        'stone': 2,
        'sand': 3,
        'water': 4,
        'wood': 5,
        'leaves': 6
    }
    
    # Biom Definitionen: [surface, subsurface, tree_chance, base_height, height_variation]
    BIOMES = {
        'plains': ['grass', 'dirt', 0.03, 8, 3],
        'desert': ['sand', 'sand', 0.001, 6, 2], 
        'hills': ['grass', 'stone', 0.02, 12, 6],
        'mountains': ['stone', 'stone', 0.005, 20, 10]
    }
    
    def __init__(self, seed=None, chunk_size=16):
        self.seed = seed or random.randint(0, 999999)
        self.chunk_size = chunk_size
        self.noise = SimpleNoise(self.seed)
        
        # Chunk Cache
        self.chunk_cache = {}
        self.max_cached_chunks = 50  # Begrenzt Memory Usage
        
        print(f"World Generator initialized - Seed: {self.seed}")
    
    def get_biome(self, x, z):
        """Bestimmt Biom basierend auf Koordinaten"""
        biome_noise = self.noise.noise2d(x, z, 0.005)
        
        if biome_noise < -0.3:
            return 'desert'
        elif biome_noise < 0.1:
            return 'plains'
        elif biome_noise < 0.4:
            return 'hills'
        else:
            return 'mountains'
    
    def get_height(self, x, z):
        """Berechnet Höhe für gegebene Koordinaten"""
        biome = self.get_biome(x, z)
        biome_data = self.BIOMES[biome]
        
        base_height = biome_data[3]
        height_var = biome_data[4]
        
        # Kombiniere mehrere Noise Layers für natürlichere Terrain
        height_noise = (
            self.noise.noise2d(x, z, 0.01) * 0.6 +
            self.noise.noise2d(x, z, 0.03) * 0.3 +
            self.noise.noise2d(x, z, 0.06) * 0.1
        )
        
        return int(base_height + height_noise * height_var)
    
    def generate_chunk(self, chunk_x, chunk_z):
        """Generiert einen einzelnen Chunk"""
        chunk_key = (chunk_x, chunk_z)
        
        # Check Cache
        if chunk_key in self.chunk_cache:
            return self.chunk_cache[chunk_key]
        
        start_time = time.perf_counter()
        blocks = []
        
        # World Koordinaten
        world_x_start = chunk_x * self.chunk_size
        world_z_start = chunk_z * self.chunk_size
        
        # Generiere Blöcke für jeden Position im Chunk
        for local_x in range(self.chunk_size):
            for local_z in range(self.chunk_size):
                world_x = world_x_start + local_x
                world_z = world_z_start + local_z
                
                blocks.extend(self._generate_column(world_x, world_z))
        
        # Cache Management
        if len(self.chunk_cache) >= self.max_cached_chunks:
            # Entferne ältesten Chunk
            oldest_key = next(iter(self.chunk_cache))
            del self.chunk_cache[oldest_key]
        
        self.chunk_cache[chunk_key] = blocks
        
        gen_time = (time.perf_counter() - start_time) * 1000
        print(f"Chunk ({chunk_x}, {chunk_z}) generated in {gen_time:.1f}ms - {len(blocks)} blocks")
        
        return blocks
    
    def _generate_column(self, x, z):
        """Generiert eine vertikale Säule von Blöcken"""
        blocks = []
        height = self.get_height(x, z)
        biome = self.get_biome(x, z)
        biome_data = self.BIOMES[biome]
        
        surface_block = biome_data[0]
        subsurface_block = biome_data[1]
        tree_chance = biome_data[2]
        
        # Bedrock Layer (ganz unten)
        for y in range(-10, -7):
            blocks.append(self._create_block('stone', x, y, z))
        
        # Underground
        for y in range(-7, height - 1):
            # Einfache Höhlen (sehr basic)
            if self._is_cave(x, y, z):
                continue
            blocks.append(self._create_block(subsurface_block, x, y, z))
        
        # Surface
        blocks.append(self._create_block(surface_block, x, height - 1, z))
        
        # Wasser (wenn unter Sea Level)
        sea_level = 5
        if height < sea_level:
            for y in range(height, sea_level):
                blocks.append(self._create_block('water', x, y, z))
        
        # Bäume
        if random.random() < tree_chance and height >= sea_level:
            tree_blocks = self._generate_simple_tree(x, height, z)
            blocks.extend(tree_blocks)
        
        return blocks
    
    def _is_cave(self, x, y, z):
        """Einfache Höhlen Generation"""
        if y > 0 or y < -15:  # Nur in bestimmten Höhen
            return False
        
        cave_noise = (
            self.noise.noise2d(x, y, 0.02) +
            self.noise.noise2d(y, z, 0.02) +
            self.noise.noise2d(x, z, 0.02)
        ) / 3
        
        return cave_noise > 0.6
    
    def _generate_simple_tree(self, x, base_y, z):
        """Generiert einen einfachen Baum"""
        tree_blocks = []
        tree_height = random.randint(3, 5)
        
        # Stamm
        for y in range(base_y, base_y + tree_height):
            tree_blocks.append(self._create_block('wood', x, y, z))
        
        # Blätter (einfache Form)
        crown_y = base_y + tree_height - 1
        for dx in range(-1, 2):
            for dz in range(-1, 2):
                for dy in range(0, 2):
                    if dx == 0 and dz == 0 and dy == 0:  # Nicht auf Stamm
                        continue
                    if random.random() < 0.7:  # Nicht alle Positionen füllen
                        tree_blocks.append(self._create_block('leaves', x + dx, crown_y + dy, z + dz))
        
        return tree_blocks
    
    def _create_block(self, block_type, x, y, z):
        """Erstellt einen Block"""
        if block_type in BlockRegistry.registry:
            return BlockRegistry.create(block_type, position=(x, y, z))
        return None


class SimpleChunkManager:
    """Einfacher Chunk Manager ohne komplexe Threading"""
    
    def __init__(self, world_generator, render_distance=3):
        self.world_gen = world_generator
        self.render_distance = render_distance
        self.loaded_chunks = {}
        self.chunk_blocks = {}
        
        print(f"Chunk Manager initialized - Render distance: {render_distance}")
    
    def get_chunk_coords(self, world_x, world_z):
        """Konvertiert World Koordinaten zu Chunk Koordinaten"""
        return (int(world_x) // self.world_gen.chunk_size, 
                int(world_z) // self.world_gen.chunk_size)
    
    def update_around_player(self, player_x, player_z):
        """Updated Chunks um den Spieler herum"""
        player_chunk_x, player_chunk_z = self.get_chunk_coords(player_x, player_z)
        
        chunks_needed = set()
        chunks_loaded = 0
        chunks_unloaded = 0
        
        # Bestimme benötigte Chunks
        for dx in range(-self.render_distance, self.render_distance + 1):
            for dz in range(-self.render_distance, self.render_distance + 1):
                chunk_coords = (player_chunk_x + dx, player_chunk_z + dz)
                chunks_needed.add(chunk_coords)
                
                # Lade Chunk falls nicht geladen
                if chunk_coords not in self.loaded_chunks:
                    self._load_chunk(*chunk_coords)
                    chunks_loaded += 1
        
        # Entlade weit entfernte Chunks
        chunks_to_unload = []
        for chunk_coords in self.loaded_chunks:
            if chunk_coords not in chunks_needed:
                chunks_to_unload.append(chunk_coords)
        
        for chunk_coords in chunks_to_unload:
            self._unload_chunk(chunk_coords)
            chunks_unloaded += 1
        
        if chunks_loaded > 0 or chunks_unloaded > 0:
            print(f"Chunks: +{chunks_loaded} -{chunks_unloaded} (Total: {len(self.loaded_chunks)})")
        
        return chunks_loaded, chunks_unloaded
    
    def _load_chunk(self, chunk_x, chunk_z):
        """Lädt einen einzelnen Chunk"""
        chunk_key = (chunk_x, chunk_z)
        blocks = self.world_gen.generate_chunk(chunk_x, chunk_z)
        
        self.loaded_chunks[chunk_key] = True
        self.chunk_blocks[chunk_key] = blocks
    
    def _unload_chunk(self, chunk_coords):
        """Entlädt einen Chunk"""
        if chunk_coords in self.chunk_blocks:
            # Zerstöre alle Blöcke
            for block in self.chunk_blocks[chunk_coords]:
                if block and hasattr(block, 'enabled'):
                    destroy(block)
            del self.chunk_blocks[chunk_coords]
        
        if chunk_coords in self.loaded_chunks:
            del self.loaded_chunks[chunk_coords]
    
    def generate_spawn_area(self, spawn_x=0, spawn_z=0, radius=1):
        """Generiert Spawn Bereich"""
        spawn_chunk_x, spawn_chunk_z = self.get_chunk_coords(spawn_x, spawn_z)
        
        print(f"Generating spawn area around chunk ({spawn_chunk_x}, {spawn_chunk_z})")
        
        for dx in range(-radius, radius + 1):
            for dz in range(-radius, radius + 1):
                chunk_x = spawn_chunk_x + dx
                chunk_z = spawn_chunk_z + dz
                self._load_chunk(chunk_x, chunk_z)
        
        print(f"Spawn area generated: {(radius * 2 + 1) ** 2} chunks")
    
    def get_height_at(self, x, z):
        """Gibt Höhe an Position zurück"""
        return self.world_gen.get_height(x, z)
    
    def get_stats(self):
        """Gibt Statistiken zurück"""
        total_blocks = sum(len(blocks) for blocks in self.chunk_blocks.values())
        return {
            'loaded_chunks': len(self.loaded_chunks),
            'total_blocks': total_blocks,
            'render_distance': self.render_distance,
            'seed': self.world_gen.seed
        }


# Factory Functions für einfache Verwendung
def create_world_generator(seed=None, chunk_size=16, render_distance=3):
    """Erstellt einen optimierten World Generator"""
    world_gen = FastWorldGenerator(seed, chunk_size)
    chunk_manager = SimpleChunkManager(world_gen, render_distance)
    return chunk_manager

def update_world_around_player(chunk_manager, player):
    """Updated die Welt um den Spieler"""
    if hasattr(player, 'position'):
        return chunk_manager.update_around_player(player.x, player.z)
    return 0, 0
        if loaded > 0 or unloaded > 0:
            print(f"[WorldGen] Chunks: +{loaded} gestartet, -{unloaded} entladen")
        return loaded, unloaded
    return 0, 0
