import random
import math
import time
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed
from ursina import *
from block import BlockRegistry, chunk_manager
import numpy as np


class FastNoiseGenerator:
    """Hochperformanter Noise-Generator mit NumPy-Optimierung"""
    
    def __init__(self, seed=None):
        self.seed = seed or random.randint(0, 999999)
        np.random.seed(self.seed)
        self.octaves = 4
        self.persistence = 0.5
        self.scale = 0.02
        
        # Precomputed permutation table for better performance
        self.perm = np.arange(256, dtype=int)
        np.random.shuffle(self.perm)
        self.perm = np.stack([self.perm, self.perm]).flatten()
        
    def noise_batch_2d(self, x_coords, z_coords):
        """Generiert Noise für Arrays von Koordinaten gleichzeitig"""
        x_coords = np.asarray(x_coords)
        z_coords = np.asarray(z_coords)
        
        value = np.zeros_like(x_coords, dtype=float)
        amplitude = 1.0
        frequency = self.scale
        max_value = 0.0
        
        for i in range(self.octaves):
            noise_vals = self._fast_noise_2d(x_coords * frequency, z_coords * frequency)
            value += noise_vals * amplitude
            max_value += amplitude
            amplitude *= self.persistence
            frequency *= 2
            
        return value / max_value
    
    def _fast_noise_2d(self, x, z):
        """Optimierte 2D Noise-Funktion mit NumPy"""
        xi = x.astype(int) & 255
        zi = z.astype(int) & 255
        xf = x - x.astype(int)
        zf = z - z.astype(int)
        
        # Fade functions
        u = self._fade(xf)
        v = self._fade(zf)
        
        # Hash coordinates
        aa = self.perm[self.perm[xi] + zi]
        ab = self.perm[self.perm[xi] + zi + 1]
        ba = self.perm[self.perm[xi + 1] + zi]
        bb = self.perm[self.perm[xi + 1] + zi + 1]
        
        # Gradients
        x1 = self._lerp(self._grad_2d(aa, xf, zf), 
                       self._grad_2d(ba, xf - 1, zf), u)
        x2 = self._lerp(self._grad_2d(ab, xf, zf - 1),
                       self._grad_2d(bb, xf - 1, zf - 1), u)
        
        return self._lerp(x1, x2, v)
    
    def _fade(self, t):
        """Fade function for smooth interpolation"""
        return t * t * t * (t * (t * 6 - 15) + 10)
    
    def _lerp(self, a, b, t):
        """Linear interpolation"""
        return a + t * (b - a)
    
    def _grad_2d(self, hash_val, x, z):
        """2D gradient function"""
        h = hash_val & 3
        u = np.where(h < 2, x, z)
        v = np.where(h < 2, z, x)
        return np.where(h & 1, -u, u) + np.where(h & 2, -v, v)
    
    def noise(self, x, z, y=None):
        """Einzelner Noise-Wert (Fallback für Kompatibilität)"""
        if y is None:
            return self.noise_batch_2d(np.array([x]), np.array([z]))[0]
        else:
            return self._noise_3d_single(x, y, z)
    
    def _noise_3d_single(self, x, y, z):
        """3D Noise für Höhlen (vereinfacht aber performant)"""
        # Kombiniere mehrere 2D Noise-Werte für 3D-Effekt
        noise1 = self.noise_batch_2d(np.array([x + y * 0.1]), np.array([z]))[0]
        noise2 = self.noise_batch_2d(np.array([x]), np.array([z + y * 0.1]))[0]
        return (noise1 + noise2) * 0.5


class OptimizedBiomeGenerator:
    """Optimierter Biom-Generator mit Caching"""
    
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
        self.biome_noise = FastNoiseGenerator(seed)
        self.biome_noise.scale = 0.008
        self._biome_cache = {}
        
    def get_biome_batch(self, x_coords, z_coords):
        """Bestimmt Biome für Arrays von Koordinaten"""
        noise_values = self.biome_noise.noise_batch_2d(x_coords, z_coords)
        
        biomes = np.empty(len(noise_values), dtype=object)
        biomes[noise_values < -0.3] = 'desert'
        biomes[(noise_values >= -0.3) & (noise_values < 0.1)] = 'plains'
        biomes[(noise_values >= 0.1) & (noise_values < 0.4)] = 'hills'
        biomes[noise_values >= 0.4] = 'mountains'
        
        return biomes
    
    def get_biome(self, x, z):
        """Einzelnes Biom (Fallback für Kompatibilität)"""
        cache_key = (int(x // 16), int(z // 16))  # Cache pro Chunk
        if cache_key not in self._biome_cache:
            noise_value = self.biome_noise.noise(x, z)
            if noise_value < -0.3:
                biome = 'desert'
            elif noise_value < 0.1:
                biome = 'plains'
            elif noise_value < 0.4:
                biome = 'hills'
            else:
                biome = 'mountains'
            self._biome_cache[cache_key] = biome
        
        return self._biome_cache[cache_key]


class HighPerformanceChunkGenerator:
    """Hochperformanter Chunk-Generator mit Batch-Processing"""
    
    def __init__(self, seed=None, chunk_size=16):
        self.seed = seed or random.randint(0, 999999)
        self.chunk_size = chunk_size
        self.height_noise = FastNoiseGenerator(self.seed)
        self.cave_noise = FastNoiseGenerator(self.seed + 1000)
        self.biome_gen = OptimizedBiomeGenerator(self.seed + 2000)
        
        # Höhlen-Parameter
        self.cave_noise.scale = 0.05
        self.cave_threshold = 0.3
        self.cave_min_y = -5
        self.cave_max_y = 10
        
        # Block-Type-Cache für bessere Performance
        self._block_cache = {}
        
    def generate_chunk_async(self, chunk_x, chunk_z):
        """Generiert einen Chunk asynchron (Thread-safe)"""
        try:
            return self._generate_chunk_optimized(chunk_x, chunk_z)
        except Exception as e:
            print(f"[ChunkGen] Fehler bei Chunk ({chunk_x}, {chunk_z}): {e}")
            return []
    
    def _generate_chunk_optimized(self, chunk_x, chunk_z):
        """Optimierte Chunk-Generierung mit Batch-Processing"""
        start_time = time.time()
        
        world_start_x = chunk_x * self.chunk_size
        world_start_z = chunk_z * self.chunk_size
        
        # Koordinaten-Arrays erstellen
        x_coords = []
        z_coords = []
        for local_x in range(self.chunk_size):
            for local_z in range(self.chunk_size):
                x_coords.append(world_start_x + local_x)
                z_coords.append(world_start_z + local_z)
        
        x_coords = np.array(x_coords)
        z_coords = np.array(z_coords)
        
        # Batch-Generierung von Höhen und Biomen
        height_values = self._generate_height_batch(x_coords, z_coords)
        biome_values = self.biome_gen.get_biome_batch(x_coords, z_coords)
        
        # Blöcke effizient generieren
        blocks = self._generate_blocks_batch(
            x_coords, z_coords, height_values, biome_values
        )
        
        # Features hinzufügen (Trees etc.)
        feature_blocks = self._generate_features_batch(
            x_coords, z_coords, height_values, biome_values
        )
        blocks.extend(feature_blocks)
        
        generation_time = time.time() - start_time
        print(f"[ChunkGen] Chunk ({chunk_x}, {chunk_z}) generiert in {generation_time:.3f}s - {len(blocks)} Blöcke")
        
        return blocks
    
    def _generate_height_batch(self, x_coords, z_coords):
        """Generiert Höhenwerte für alle Koordinaten gleichzeitig"""
        noise_values = self.height_noise.noise_batch_2d(x_coords, z_coords)
        biomes = self.biome_gen.get_biome_batch(x_coords, z_coords)
        
        heights = np.zeros(len(x_coords), dtype=int)
        
        for i, (noise_val, biome) in enumerate(zip(noise_values, biomes)):
            biome_data = OptimizedBiomeGenerator.BIOMES[biome]
            height = int(biome_data['base_height'] + noise_val * biome_data['height_variation'])
            heights[i] = height
        
        return heights
    
    def _generate_blocks_batch(self, x_coords, z_coords, heights, biomes):
        """Generiert alle Terrain-Blöcke in einem Batch"""
        blocks = []
        
        # Vorgenerierte Block-Listen für bessere Performance
        block_positions = {
            'stone': [],
            'dirt': [],
            'grass': [],
            'sand': [],
            'water': []
        }
        
        for i, (x, z, height, biome) in enumerate(zip(x_coords, z_coords, heights, biomes)):
            biome_data = OptimizedBiomeGenerator.BIOMES[biome]
            
            # Terrain-Säule generieren
            self._add_column_to_batch(
                block_positions, x, z, height, biome_data
            )
        
        # Alle Blöcke eines Typs gleichzeitig erstellen
        for block_type, positions in block_positions.items():
            if positions and BlockRegistry.registry.get(block_type):
                for pos in positions:
                    block = BlockRegistry.create(block_type, position=pos)
                    if block:
                        blocks.append(block)
        
        return blocks
    
    def _add_column_to_batch(self, block_positions, x, z, surface_height, biome_data):
        """Fügt eine Terrain-Säule zu den Batch-Listen hinzu"""
        # Grundgestein
        for y in range(-15, -12):
            block_positions['stone'].append((x, y, z))
        
        # Untergrund mit Höhlen-Check
        for y in range(-12, surface_height - 2):
            if (self.cave_min_y <= y <= self.cave_max_y and 
                abs(self.cave_noise.noise(x, y * 0.5, z)) > self.cave_threshold):
                continue  # Höhle
            
            block_type = biome_data['subsurface_block']
            if block_type in block_positions:
                block_positions[block_type].append((x, y, z))
        
        # Oberflächen-Schichten
        for y in range(max(-12, surface_height - 2), surface_height):
            if y < biome_data['water_level']:
                block_type = 'dirt' if biome_data['surface_block'] == 'grass' else biome_data['subsurface_block']
            else:
                block_type = biome_data['surface_block'] if y == surface_height - 1 else biome_data['subsurface_block']
            
            if block_type in block_positions:
                block_positions[block_type].append((x, y, z))
        
        # Wasser
        if surface_height < biome_data['water_level']:
            for y in range(surface_height, biome_data['water_level']):
                block_positions['water'].append((x, y, z))
    
    def _generate_features_batch(self, x_coords, z_coords, heights, biomes):
        """Generiert Features (Bäume etc.) für den Chunk"""
        blocks = []
        
        for i, (x, z, height, biome) in enumerate(zip(x_coords, z_coords, heights, biomes)):
            biome_data = OptimizedBiomeGenerator.BIOMES[biome]
            
            # Tree generation mit optimierter Zufallszahl
            if random.random() < biome_data['tree_chance']:
                tree_blocks = self._generate_tree_fast(x, height, z)
                blocks.extend(tree_blocks)
        
        return blocks
    
    def _generate_tree_fast(self, x, base_y, z):
        """Optimierte Baum-Generierung"""
        blocks = []
        tree_height = random.randint(4, 7)
        
        # Stamm
        if BlockRegistry.registry.get('wood'):
            for y in range(base_y, base_y + tree_height):
                trunk = BlockRegistry.create('wood', position=(x, y, z))
                if trunk:
                    blocks.append(trunk)
        
        # Blätter (vereinfacht für bessere Performance)
        if BlockRegistry.registry.get('leaves'):
            crown_y = base_y + tree_height
            for dy in range(-1, 2):  # Kleinere Krone für bessere Performance
                for dx in range(-1, 2):
                    for dz in range(-1, 2):
                        if abs(dx) + abs(dz) + abs(dy) <= 2 and random.random() > 0.4:
                            leaf = BlockRegistry.create('leaves', 
                                                      position=(x + dx, crown_y + dy, z + dz))
                            if leaf:
                                blocks.append(leaf)
        
        return blocks


class ThreadedWorldGenerator:
    """Thread-basierter World-Generator mit asynchroner Chunk-Generierung"""
    
    def __init__(self, seed=None, chunk_size=16, render_distance=3, max_workers=4):
        self.seed = seed or random.randint(0, 999999)
        self.chunk_size = chunk_size
        self.render_distance = render_distance
        self.max_workers = max_workers
        
        self.chunk_generator = HighPerformanceChunkGenerator(self.seed, chunk_size)
        
        # Thread-Management
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.generation_futures = {}
        self.generation_queue = queue.Queue()
        
        # Chunk-Storage
        self.loaded_chunks = {}
        self.chunk_blocks = {}
        self.loading_chunks = set()
        
        # Performance-Tracking
        self.stats = {
            'chunks_generated': 0,
            'total_generation_time': 0,
            'average_generation_time': 0
        }
        
        print(f"[ThreadedWorldGen] Initialisiert mit Seed: {self.seed}")
        print(f"[ThreadedWorldGen] Worker-Threads: {max_workers}")
        print(f"[ThreadedWorldGen] Chunk-Größe: {chunk_size}x{chunk_size}")
        print(f"[ThreadedWorldGen] Render-Distanz: {render_distance} Chunks")
    
    def get_chunk_coords(self, world_x, world_z):
        """Berechnet Chunk-Koordinaten aus Welt-Position"""
        return (
            int(world_x // self.chunk_size),
            int(world_z // self.chunk_size)
        )
    
    def update_chunks(self, player_x, player_z):
        """Aktualisiert Chunks mit asynchroner Generierung"""
        player_chunk_x, player_chunk_z = self.get_chunk_coords(player_x, player_z)
        
        # Chunks in Render-Distanz bestimmen
        chunks_needed = set()
        for dx in range(-self.render_distance, self.render_distance + 1):
            for dz in range(-self.render_distance, self.render_distance + 1):
                chunk_x = player_chunk_x + dx
                chunk_z = player_chunk_z + dz
                chunks_needed.add((chunk_x, chunk_z))
        
        # Abgeschlossene Generierungen verarbeiten
        self._process_completed_generations()
        
        # Neue Chunks zur Generierung einreihen
        chunks_started = 0
        for chunk_coords in chunks_needed:
            if (chunk_coords not in self.loaded_chunks and 
                chunk_coords not in self.loading_chunks):
                self._start_chunk_generation(*chunk_coords)
                chunks_started += 1
        
        # Entfernte Chunks entladen
        chunks_unloaded = 0
        chunks_to_unload = []
        for chunk_coords in list(self.loaded_chunks.keys()):
            if chunk_coords not in chunks_needed:
                chunks_to_unload.append(chunk_coords)
        
        for chunk_coords in chunks_to_unload:
            self._unload_chunk(*chunk_coords)
            chunks_unloaded += 1
        
        return chunks_started, chunks_unloaded
    
    def _start_chunk_generation(self, chunk_x, chunk_z):
        """Startet asynchrone Chunk-Generierung"""
        chunk_coords = (chunk_x, chunk_z)
        self.loading_chunks.add(chunk_coords)
        
        future = self.executor.submit(
            self.chunk_generator.generate_chunk_async, 
            chunk_x, chunk_z
        )
        self.generation_futures[chunk_coords] = {
            'future': future,
            'start_time': time.time()
        }
    
    def _process_completed_generations(self):
        """Verarbeitet abgeschlossene Chunk-Generierungen"""
        completed_chunks = []
        
        for chunk_coords, generation_data in self.generation_futures.items():
            future = generation_data['future']
            if future.done():
                completed_chunks.append(chunk_coords)
                
                try:
                    blocks = future.result()
                    generation_time = time.time() - generation_data['start_time']
                    
                    # Chunk als geladen markieren
                    self.loaded_chunks[chunk_coords] = True
                    self.chunk_blocks[chunk_coords] = blocks
                    self.loading_chunks.discard(chunk_coords)
                    
                    # Statistiken aktualisieren
                    self.stats['chunks_generated'] += 1
                    self.stats['total_generation_time'] += generation_time
                    self.stats['average_generation_time'] = (
                        self.stats['total_generation_time'] / 
                        self.stats['chunks_generated']
                    )
                    
                    print(f"[ThreadedWorldGen] Chunk {chunk_coords} fertig in {generation_time:.3f}s")
                    
                except Exception as e:
                    print(f"[ThreadedWorldGen] Fehler bei Chunk {chunk_coords}: {e}")
                    self.loading_chunks.discard(chunk_coords)
        
        # Abgeschlossene Futures entfernen
        for chunk_coords in completed_chunks:
            del self.generation_futures[chunk_coords]
    
    def _unload_chunk(self, chunk_x, chunk_z):
        """Entlädt einen Chunk"""
        chunk_key = (chunk_x, chunk_z)
        
        if chunk_key not in self.loaded_chunks:
            return
        
        # Blöcke zerstören (auf Main-Thread)
        if chunk_key in self.chunk_blocks:
            for block in self.chunk_blocks[chunk_key]:
                if block and hasattr(block, 'enabled'):
                    destroy(block)
            del self.chunk_blocks[chunk_key]
        
        del self.loaded_chunks[chunk_key]
    
    def generate_spawn_area(self, spawn_x=0, spawn_z=0, radius=2):
        """Generiert Spawn-Bereich synchron für sofortige Verfügbarkeit"""
        spawn_chunk_x, spawn_chunk_z = self.get_chunk_coords(spawn_x, spawn_z)
        
        print(f"[ThreadedWorldGen] Generiere Spawn-Bereich um Chunk ({spawn_chunk_x}, {spawn_chunk_z})")
        
        spawn_chunks = []
        for dx in range(-radius, radius + 1):
            for dz in range(-radius, radius + 1):
                chunk_x = spawn_chunk_x + dx
                chunk_z = spawn_chunk_z + dz
                spawn_chunks.append((chunk_x, chunk_z))
        
        # Spawn-Chunks parallel generieren
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self.chunk_generator.generate_chunk_async, cx, cz): (cx, cz)
                for cx, cz in spawn_chunks
            }
            
            for future in as_completed(futures):
                chunk_x, chunk_z = futures[future]
                try:
                    blocks = future.result()
                    chunk_key = (chunk_x, chunk_z)
                    self.loaded_chunks[chunk_key] = True
                    self.chunk_blocks[chunk_key] = blocks
                except Exception as e:
                    print(f"[ThreadedWorldGen] Spawn-Chunk ({chunk_x}, {chunk_z}) Fehler: {e}")
        
        print(f"[ThreadedWorldGen] Spawn-Bereich generiert: {len(spawn_chunks)} Chunks")
    
    def get_height_at(self, x, z):
        """Gibt Terrain-Höhe an Position zurück"""
        noise_value = self.chunk_generator.height_noise.noise(x, z)
        biome = self.chunk_generator.biome_gen.get_biome(x, z)
        biome_data = OptimizedBiomeGenerator.BIOMES[biome]
        
        height = (biome_data['base_height'] + 
                 noise_value * biome_data['height_variation'])
        
        return int(height)
    
    def get_stats(self):
        """Gibt Statistiken zurück"""
        return {
            'seed': self.seed,
            'loaded_chunks': len(self.loaded_chunks),
            'loading_chunks': len(self.loading_chunks),
            'total_blocks': sum(len(blocks) for blocks in self.chunk_blocks.values()),
            'chunk_size': self.chunk_size,
            'render_distance': self.render_distance,
            'worker_threads': self.max_workers,
            'generation_stats': self.stats.copy()
        }
    
    def shutdown(self):
        """Beendet alle Worker-Threads sauber"""
        print("[ThreadedWorldGen] Beende Worker-Threads...")
        self.executor.shutdown(wait=True)
        print("[ThreadedWorldGen] Alle Threads beendet")


# Factory-Funktionen für Kompatibilität mit main.py
def create_world_generator(seed=None, chunk_size=16, render_distance=3, max_workers=4):
    """Factory-Funktion zum Erstellen eines optimierten World-Generators"""
    return ThreadedWorldGenerator(seed, chunk_size, render_distance, max_workers)

def update_world_around_player(world_gen, player):
    """Aktualisiert die Welt um den Spieler herum"""
    if hasattr(player, 'position'):
        loaded, unloaded = world_gen.update_chunks(player.x, player.z)
        if loaded > 0 or unloaded > 0:
            print(f"[WorldGen] Chunks: +{loaded} gestartet, -{unloaded} entladen")
        return loaded, unloaded
    return 0, 0
