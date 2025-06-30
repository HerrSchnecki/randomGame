import random
import math
import time
from ursina import *
from block import BlockRegistry, chunk_manager


class NoiseGenerator:
    """Einfacher Perlin-Noise-ähnlicher Generator für Terrain"""
    
    def __init__(self, seed=None):
        self.seed = seed or random.randint(0, 999999)
        random.seed(self.seed)
        self.octaves = 4
        self.persistence = 0.5
        self.scale = 0.02
        
    def noise(self, x, z, y=None):
        """Generiert Noise-Wert für gegebene Koordinaten (2D oder 3D)"""
        if y is None:
            # 2D Noise für Terrain
            return self._noise_2d(x, z)
        else:
            # 3D Noise für Höhlen
            return self._noise_3d(x, y, z)
    
    def _noise_2d(self, x, z):
        """2D Noise für Terrain-Generation"""
        value = 0
        amplitude = 1
        frequency = self.scale
        max_value = 0
        
        for i in range(self.octaves):
            value += self._interpolated_noise_2d(x * frequency, z * frequency) * amplitude
            max_value += amplitude
            amplitude *= self.persistence
            frequency *= 2
            
        return value / max_value
    
    def _noise_3d(self, x, y, z):
        """3D Noise für Höhlen-Generation"""
        value = 0
        amplitude = 1
        frequency = self.scale
        max_value = 0
        
        for i in range(self.octaves):
            value += self._interpolated_noise_3d(x * frequency, y * frequency, z * frequency) * amplitude
            max_value += amplitude
            amplitude *= self.persistence
            frequency *= 2
            
        return value / max_value
    
    def _interpolated_noise_2d(self, x, z):
        """Interpolierter 2D Noise zwischen ganzzahligen Koordinaten"""
        int_x = int(x)
        int_z = int(z)
        frac_x = x - int_x
        frac_z = z - int_z
        
        # Eckwerte holen
        a = self._smooth_noise_2d(int_x, int_z)
        b = self._smooth_noise_2d(int_x + 1, int_z)
        c = self._smooth_noise_2d(int_x, int_z + 1)
        d = self._smooth_noise_2d(int_x + 1, int_z + 1)
        
        # Interpolieren
        i1 = self._interpolate(a, b, frac_x)
        i2 = self._interpolate(c, d, frac_x)
        
        return self._interpolate(i1, i2, frac_z)
    
    def _interpolated_noise_3d(self, x, y, z):
        """Interpolierter 3D Noise zwischen ganzzahligen Koordinaten"""
        int_x = int(x)
        int_y = int(y)
        int_z = int(z)
        frac_x = x - int_x
        frac_y = y - int_y
        frac_z = z - int_z
        
        # 8 Eckpunkte eines Würfels
        n000 = self._noise_3d_raw(int_x, int_y, int_z)
        n001 = self._noise_3d_raw(int_x, int_y, int_z + 1)
        n010 = self._noise_3d_raw(int_x, int_y + 1, int_z)
        n011 = self._noise_3d_raw(int_x, int_y + 1, int_z + 1)
        n100 = self._noise_3d_raw(int_x + 1, int_y, int_z)
        n101 = self._noise_3d_raw(int_x + 1, int_y, int_z + 1)
        n110 = self._noise_3d_raw(int_x + 1, int_y + 1, int_z)
        n111 = self._noise_3d_raw(int_x + 1, int_y + 1, int_z + 1)
        
        # Trilineare Interpolation
        # Zuerst in X-Richtung
        n00 = self._interpolate(n000, n100, frac_x)
        n01 = self._interpolate(n001, n101, frac_x)
        n10 = self._interpolate(n010, n110, frac_x)
        n11 = self._interpolate(n011, n111, frac_x)
        
        # Dann in Z-Richtung
        n0 = self._interpolate(n00, n01, frac_z)
        n1 = self._interpolate(n10, n11, frac_z)
        
        # Schließlich in Y-Richtung
        return self._interpolate(n0, n1, frac_y)
    
    def _smooth_noise_2d(self, x, z):
        """Geglätteter 2D Noise-Wert"""
        corners = (self._noise_2d_raw(x-1, z-1) + self._noise_2d_raw(x+1, z-1) + 
                  self._noise_2d_raw(x-1, z+1) + self._noise_2d_raw(x+1, z+1)) / 16
        sides = (self._noise_2d_raw(x-1, z) + self._noise_2d_raw(x+1, z) + 
                self._noise_2d_raw(x, z-1) + self._noise_2d_raw(x, z+1)) / 8
        center = self._noise_2d_raw(x, z) / 4
        
        return corners + sides + center
    
    def _noise_2d_raw(self, x, z):
        """Basis 2D Noise-Funktion"""
        random.seed(x * 374761393 + z * 668265263 + self.seed)
        return (random.random() - 0.5) * 2
    
    def _noise_3d_raw(self, x, y, z):
        """Basis 3D Noise-Funktion"""
        random.seed(x * 374761393 + y * 982451653 + z * 668265263 + self.seed)
        return (random.random() - 0.5) * 2
    
    def _interpolate(self, a, b, x):
        """Cosinus-Interpolation für smooth transitions"""
        ft = x * math.pi
        f = (1 - math.cos(ft)) * 0.5
        return a * (1 - f) + b * f

class BiomeGenerator:
    """Biom-Generator mit verschiedenen Landschaftstypen"""
    
    BIOMES = {
        'plains': {
            'base_height': 8,
            'height_variation': 3,
            'surface_block': 'grass',
            'subsurface_block': 'dirt',
            'tree_chance': 0.02,
            'water_level': 5
        },
        'hills': {
            'base_height': 15,
            'height_variation': 8,
            'surface_block': 'grass',
            'subsurface_block': 'stone',
            'tree_chance': 0.03,
            'water_level': 5
        },
        'desert': {
            'base_height': 6,
            'height_variation': 4,
            'surface_block': 'sand',
            'subsurface_block': 'sand',
            'tree_chance': 0.001,
            'water_level': 3
        },
        'mountains': {
            'base_height': 25,
            'height_variation': 15,
            'surface_block': 'stone',
            'subsurface_block': 'stone',
            'tree_chance': 0.01,
            'water_level': 5
        }
    }
    
    def __init__(self, seed=None):
        self.biome_noise = NoiseGenerator(seed)
        self.biome_noise.scale = 0.008
        
    def get_biome(self, x, z):
        """Bestimmt Biom für gegebene Koordinaten"""
        noise_value = self.biome_noise.noise(x, z)
        
        if noise_value < -0.3:
            return 'desert'
        elif noise_value < 0.1:
            return 'plains'
        elif noise_value < 0.4:
            return 'hills'
        else:
            return 'mountains'

class ChunkGenerator:
    """Generiert einzelne Chunks mit Terrain und Features"""
    
    def __init__(self, seed=None, chunk_size=16):
        self.seed = seed or random.randint(0, 999999)
        self.chunk_size = chunk_size
        self.height_noise = NoiseGenerator(self.seed)
        self.cave_noise = NoiseGenerator(self.seed + 1000)
        self.biome_gen = BiomeGenerator(self.seed + 2000)
        
        # Höhlen-Parameter
        self.cave_noise.scale = 0.05
        self.cave_threshold = 0.3
        self.cave_min_y = -5
        self.cave_max_y = 10
        
    def generate_chunk(self, chunk_x, chunk_z):
        """Generiert einen vollständigen Chunk"""
        start_time = time.time()
        blocks = []
        
        world_start_x = chunk_x * self.chunk_size
        world_start_z = chunk_z * self.chunk_size
        
        # Höhenkarte für den Chunk erstellen
        height_map = self._generate_height_map(world_start_x, world_start_z)
        biome_map = self._generate_biome_map(world_start_x, world_start_z)
        
        for local_x in range(self.chunk_size):
            for local_z in range(self.chunk_size):
                world_x = world_start_x + local_x
                world_z = world_start_z + local_z
                
                height = height_map[local_x][local_z]
                biome = biome_map[local_x][local_z]
                biome_data = BiomeGenerator.BIOMES[biome]
                
                # Terrain generieren
                chunk_blocks = self._generate_column(
                    world_x, world_z, height, biome_data
                )
                blocks.extend(chunk_blocks)
                
                # Features hinzufügen
                if random.random() < biome_data['tree_chance']:
                    tree_blocks = self._generate_tree(world_x, height, world_z)
                    blocks.extend(tree_blocks)
        
        generation_time = time.time() - start_time
        print(f"[ChunkGen] Chunk ({chunk_x}, {chunk_z}) generiert in {generation_time:.3f}s - {len(blocks)} Blöcke")
        
        return blocks
    
    def _generate_height_map(self, start_x, start_z):
        """Erstellt Höhenkarte für Chunk"""
        height_map = []
        
        for local_x in range(self.chunk_size):
            row = []
            for local_z in range(self.chunk_size):
                world_x = start_x + local_x
                world_z = start_z + local_z
                
                # Basis-Höhe aus Noise
                noise_value = self.height_noise.noise(world_x, world_z)
                
                # Biom-spezifische Höhe
                biome = self.biome_gen.get_biome(world_x, world_z)
                biome_data = BiomeGenerator.BIOMES[biome]
                
                height = (biome_data['base_height'] + 
                         noise_value * biome_data['height_variation'])
                
                row.append(int(height))
            height_map.append(row)
        
        return height_map
    
    def _generate_biome_map(self, start_x, start_z):
        """Erstellt Biom-Karte für Chunk"""
        biome_map = []
        
        for local_x in range(self.chunk_size):
            row = []
            for local_z in range(self.chunk_size):
                world_x = start_x + local_x
                world_z = start_z + local_z
                biome = self.biome_gen.get_biome(world_x, world_z)
                row.append(biome)
            biome_map.append(row)
        
        return biome_map
    
    def _generate_column(self, x, z, surface_height, biome_data):
        """Generiert eine vertikale Säule von Blöcken"""
        blocks = []
        
        # Grundgestein
        for y in range(-15, -12):
            block = BlockRegistry.create('stone', position=(x, y, z))
            if block:
                blocks.append(block)
        
        # Untergrund
        for y in range(-12, surface_height - 2):
            # Höhlen-Check
            if (self.cave_min_y <= y <= self.cave_max_y and 
                abs(self.cave_noise.noise(x, y * 0.5, z)) > self.cave_threshold):
                continue  # Höhle - kein Block
            
            block = BlockRegistry.create(biome_data['subsurface_block'], position=(x, y, z))
            if block:
                blocks.append(block)
        
        # Oberflächen-Schichten
        for y in range(max(-12, surface_height - 2), surface_height):
            if y < biome_data['water_level']:
                # Unter Wasser - andere Blöcke
                if y == surface_height - 1:
                    block_type = 'dirt' if biome_data['surface_block'] == 'grass' else biome_data['subsurface_block']
                else:
                    block_type = biome_data['subsurface_block']
            else:
                # Normale Oberfläche
                if y == surface_height - 1:
                    block_type = biome_data['surface_block']
                else:
                    block_type = biome_data['subsurface_block']
            
            block = BlockRegistry.create(block_type, position=(x, y, z))
            if block:
                blocks.append(block)
        
        # Wasser hinzufügen wenn nötig
        if surface_height < biome_data['water_level']:
            for y in range(surface_height, biome_data['water_level']):
                water_block = BlockRegistry.create('water', position=(x, y, z))
                if water_block:
                    blocks.append(water_block)
        
        return blocks
    
    def _generate_tree(self, x, base_y, z):
        """Generiert einen einfachen Baum"""
        blocks = []
        tree_height = random.randint(4, 7)
        
        # Stamm
        for y in range(base_y, base_y + tree_height):
            trunk = BlockRegistry.create('wood', position=(x, y, z))
            if trunk:
                blocks.append(trunk)
        
        # Blätter
        crown_y = base_y + tree_height
        for dy in range(-2, 2):
            for dx in range(-2, 3):
                for dz in range(-2, 3):
                    if abs(dx) + abs(dz) + abs(dy) <= 3 and random.random() > 0.3:
                        if BlockRegistry.registry.get('leaves'):
                            leaf = BlockRegistry.create('leaves', 
                                                      position=(x + dx, crown_y + dy, z + dz))
                            if leaf:
                                blocks.append(leaf)
        
        return blocks

class WorldGenerator:
    """Haupt-World-Generator mit Chunk-Management"""
    
    def __init__(self, seed=None, chunk_size=16, render_distance=1):
        self.seed = seed or random.randint(0, 999999)
        self.chunk_size = chunk_size
        self.render_distance = render_distance
        self.chunk_generator = ChunkGenerator(self.seed, chunk_size)
        
        self.loaded_chunks = {}
        self.chunk_blocks = {}
        
        print(f"[WorldGen] Initialisiert mit Seed: {self.seed}")
        print(f"[WorldGen] Chunk-Größe: {chunk_size}x{chunk_size}")
        print(f"[WorldGen] Render-Distanz: {render_distance} Chunks")
    
    def get_chunk_coords(self, world_x, world_z):
        """Berechnet Chunk-Koordinaten aus Welt-Position"""
        return (
            int(world_x // self.chunk_size),
            int(world_z // self.chunk_size)
        )
    
    def update_chunks(self, player_x, player_z):
        """Aktualisiert geladene Chunks basierend auf Spieler-Position"""
        player_chunk_x, player_chunk_z = self.get_chunk_coords(player_x, player_z)
        
        # Chunks in Render-Distanz bestimmen
        chunks_to_load = set()
        for dx in range(-self.render_distance, self.render_distance + 1):
            for dz in range(-self.render_distance, self.render_distance + 1):
                chunk_x = player_chunk_x + dx
                chunk_z = player_chunk_z + dz
                chunks_to_load.add((chunk_x, chunk_z))
        
        # Neue Chunks laden
        for chunk_coords in chunks_to_load:
            if chunk_coords not in self.loaded_chunks:
                self._load_chunk(*chunk_coords)
        
        # Weit entfernte Chunks entladen
        chunks_to_unload = []
        for chunk_coords in self.loaded_chunks:
            if chunk_coords not in chunks_to_load:
                chunks_to_unload.append(chunk_coords)
        
        for chunk_coords in chunks_to_unload:
            self._unload_chunk(*chunk_coords)
        
        return len(chunks_to_load), len(chunks_to_unload)
    
    def _load_chunk(self, chunk_x, chunk_z):
        """Lädt einen einzelnen Chunk"""
        chunk_key = (chunk_x, chunk_z)
        
        if chunk_key in self.loaded_chunks:
            return
        
        start_time = time.time()
        
        # Chunk generieren
        blocks = self.chunk_generator.generate_chunk(chunk_x, chunk_z)
        
        self.loaded_chunks[chunk_key] = True
        self.chunk_blocks[chunk_key] = blocks
        
        load_time = time.time() - start_time
        print(f"[WorldGen] Chunk ({chunk_x}, {chunk_z}) geladen in {load_time:.3f}s")
    
    def _unload_chunk(self, chunk_x, chunk_z):
        """Entlädt einen einzelnen Chunk"""
        chunk_key = (chunk_x, chunk_z)
        
        if chunk_key not in self.loaded_chunks:
            return
        
        # Alle Blöcke des Chunks zerstören
        if chunk_key in self.chunk_blocks:
            for block in self.chunk_blocks[chunk_key]:
                if block and hasattr(block, 'enabled'):
                    destroy(block)
            del self.chunk_blocks[chunk_key]
        
        del self.loaded_chunks[chunk_key]
        print(f"[WorldGen] Chunk ({chunk_x}, {chunk_z}) entladen")
    
    def generate_spawn_area(self, spawn_x=0, spawn_z=0, radius=2):
        """Generiert einen kleinen Bereich um den Spawn-Punkt"""
        spawn_chunk_x, spawn_chunk_z = self.get_chunk_coords(spawn_x, spawn_z)
        
        print(f"[WorldGen] Generiere Spawn-Bereich um Chunk ({spawn_chunk_x}, {spawn_chunk_z})")
        
        for dx in range(-radius, radius + 1):
            for dz in range(-radius, radius + 1):
                chunk_x = spawn_chunk_x + dx
                chunk_z = spawn_chunk_z + dz
                self._load_chunk(chunk_x, chunk_z)
        
        print(f"[WorldGen] Spawn-Bereich generiert: {(radius * 2 + 1) ** 2} Chunks")
    
    def get_height_at(self, x, z):
        """Gibt die Terrain-Höhe an gegebener Position zurück"""
        # Für Spawn-Positionierung
        noise_value = self.chunk_generator.height_noise.noise(x, z)
        biome = self.chunk_generator.biome_gen.get_biome(x, z)
        biome_data = BiomeGenerator.BIOMES[biome]
        
        height = (biome_data['base_height'] + 
                 noise_value * biome_data['height_variation'])
        
        return int(height)
    
    def get_stats(self):
        """Gibt Statistiken über die generierte Welt zurück"""
        total_blocks = sum(len(blocks) for blocks in self.chunk_blocks.values())
        
        return {
            'seed': self.seed,
            'loaded_chunks': len(self.loaded_chunks),
            'total_blocks': total_blocks,
            'chunk_size': self.chunk_size,
            'render_distance': self.render_distance
        }

# Beispiel-Integration für main.py
def create_world_generator(seed=None, chunk_size=16, render_distance=3):
    """Factory-Funktion zum Erstellen eines World-Generators"""
    return WorldGenerator(seed, chunk_size, render_distance)

def update_world_around_player(world_gen, player):
    """Aktualisiert die Welt um den Spieler herum"""
    if hasattr(player, 'position'):
        loaded, unloaded = world_gen.update_chunks(player.x, player.z)
        if loaded > 0 or unloaded > 0:
            print(f"[WorldGen] Chunks: +{loaded} geladen, -{unloaded} entladen")
        return loaded, unloaded
    return 0, 0
