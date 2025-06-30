from ursina import *
from ursina import color as ursina_color
import os
from collections import defaultdict

class BlockRegistry:
    registry = {}
    _texture_cache = {}
    _model_cache = {}

    @classmethod
    def register(cls, name, texture, model='cube', scale=1, color=None, walkthrough=False, model_url=None):
        """
        Registriert einen Block-Typ mit optionalem Custom Model
        
        Args:
            name: Name des Blocks
            texture: Textur des Blocks
            model: 3D-Model ('cube', 'sphere', etc.) oder Pfad zu lokaler Datei
            scale: Skalierung des Blocks (Standard: 1)
            color: Farbe des Blocks (Standard: None für zufällige Farbe)
            walkthrough: Ob man durch den Block laufen kann (Standard: False)
            model_url: URL zu einem 3D-Model zum Download
        """
        cls.registry[name] = {
            'texture': texture,
            'model': model,
            'scale': scale,
            'color': color,
            'walkthrough': walkthrough,
            'model_url': model_url
        }
        
        cls._preload_texture(texture)

    @classmethod
    def _preload_texture(cls, texture_path):
        """Lädt Texturen vor und cached sie"""
        if texture_path not in cls._texture_cache:
            try:
                loaded_texture = load_texture(texture_path)
                if loaded_texture:
                    cls._texture_cache[texture_path] = loaded_texture
                else:
                    cls._texture_cache[texture_path] = 'white_cube'
            except:
                cls._texture_cache[texture_path] = 'white_cube'

    @classmethod
    def get_cached_texture(cls, texture_path):
        """Gibt gecachte Textur zurück"""
        return cls._texture_cache.get(texture_path, 'white_cube')

    @classmethod
    def create(cls, name, position=(0, 0, 0)):
        if name not in cls.registry:
            print(f"[BlockRegistry] Block '{name}' nicht registriert!")
            return None
        
        block_data = cls.registry[name]
        
        model_to_use = block_data['model']
        if block_data['model_url']:
            model_to_use = cls._load_model_from_url(name, block_data['model_url'], block_data['model'])
        
        return Block(
            position=position,
            texture=block_data['texture'],
            model=model_to_use,
            scale=block_data['scale'],
            color=block_data['color'],
            walkthrough=block_data['walkthrough']
        )

    @classmethod
    def _load_model_from_url(cls, block_name, url, fallback_model):
        """
        Lädt ein 3D-Model von einer URL herunter
        """
        cache_key = f"{block_name}_{url}"
        if cache_key in cls._model_cache:
            return cls._model_cache[cache_key]
            
        try:
            import urllib.request
            import urllib.parse
            
            if not os.path.exists('models'):
                os.makedirs('models')
            
            parsed_url = urllib.parse.urlparse(url)
            filename = os.path.basename(parsed_url.path)
            if not filename or '.' not in filename:
                filename = f"{block_name}_model.obj"
            
            local_path = os.path.join('models', filename)
            
            if not os.path.exists(local_path):
                print(f"[BlockRegistry] Lade Model herunter: {url}")
                urllib.request.urlretrieve(url, local_path)
                print(f"[BlockRegistry] Model gespeichert als: {local_path}")
            
            cls._model_cache[cache_key] = local_path
            return local_path
            
        except Exception as e:
            print(f"[BlockRegistry] Fehler beim Laden des Models von {url}: {e}")
            print(f"[BlockRegistry] Verwende Fallback-Model: {fallback_model}")
            cls._model_cache[cache_key] = fallback_model
            return fallback_model

    @classmethod
    def list_blocks(cls):
        """Gibt eine Liste aller registrierten Blöcke zurück"""
        return list(cls.registry.keys())

    @classmethod
    def get_block_info(cls, name):
        """Gibt Informationen über einen Block zurück"""
        return cls.registry.get(name, None)

    @classmethod
    def get_texture(cls, name):
        """Gibt nur die Textur eines Blocks zurück (für Rückwärtskompatibilität)"""
        block_data = cls.registry.get(name)
        if block_data:
            return block_data['texture']
        return None

    @classmethod
    def get_model(cls, name):
        """Gibt nur das Model eines Blocks zurück"""
        block_data = cls.registry.get(name)
        if block_data:
            return block_data['model']
        return 'cube'

    @classmethod
    def is_walkthrough(cls, name):
        """Prüft ob ein Block walkthrough ist"""
        block_data = cls.registry.get(name)
        if block_data:
            return block_data['walkthrough']
        return False

    @classmethod
    def register_from_file(cls, name, texture, model_path, scale=1, color=None, walkthrough=False):
        """
        Registriert einen Block mit einem lokalen 3D-Model
        """
        if os.path.exists(model_path):
            cls.register(name, texture, model=model_path, scale=scale, color=color, walkthrough=walkthrough)
        else:
            print(f"[BlockRegistry] Model-Datei nicht gefunden: {model_path}")
            cls.register(name, texture, model='cube', scale=scale, color=color, walkthrough=walkthrough)


class Block(Entity):  # Geändert von Button zu Entity für bessere Performance
    _default_color = None
    
    def __init__(self, position=(0, 0, 0), texture='white_cube', model='cube', scale=1, color=None, walkthrough=False):
        if color is None:
            if Block._default_color is None:
                Block._default_color = ursina_color.color(0, 0, random.uniform(0.9, 1))
            block_color = Block._default_color
        else:
            block_color = color
    
        cached_texture = BlockRegistry.get_cached_texture(texture)
            
        super().__init__(
            parent=scene,
            position=position,
            model=model,
            origin_y=0.5,
            texture=cached_texture,
            color=block_color,
            scale=scale
        )
        
        self.walkthrough = walkthrough
        
        # Optimierte Kollision - nur bei Bedarf
        if not walkthrough:
            self.collider = 'box'
        
        # Mouse picking für Interaktion (effizienter als Button)
        self.mouse_filter = True

    def input(self, key):
        """Vereinfachte Input-Behandlung"""
        if not mouse.hovered_entity == self:
            return
            
        if key == 'right mouse down':
            self._handle_place_block()
        elif key == 'left mouse down':
            self._handle_break_block()

    def _handle_place_block(self):
        """Optimierte Block-Platzierung"""
        try:
            from inventory import get_current_block
            current_block = get_current_block()
            if current_block:
                new_position = self.position + mouse.normal
                new_block = BlockRegistry.create(current_block, position=new_position)
                if new_block:
                    # Füge Block zum Chunk hinzu für bessere Verwaltung
                    chunk_manager.add_block_to_chunk(new_block, new_position)
            else:
                print("Kein Block im Inventar ausgewählt!")
        except ImportError:
            # Fallback ohne Inventarsystem
            current_block = 'grass'
            new_block = BlockRegistry.create(current_block, position=self.position + mouse.normal)
            if new_block:
                chunk_manager.add_block_to_chunk(new_block, self.position + mouse.normal)

    def _handle_break_block(self):
        """Optimierte Block-Zerstörung"""
        # Entferne Block aus Chunk-Management
        chunk_manager.remove_block_from_chunk(self)
        destroy(self)

    def set_walkthrough(self, walkthrough):
        """Ändert die Walkthrough-Eigenschaft zur Laufzeit"""
        self.walkthrough = walkthrough
        if walkthrough:
            self.collider = None
        else:
            self.collider = 'box'


class OptimizedChunkManager:
    """Hochoptimierter Chunk-Manager für bessere Performance"""
    def __init__(self, chunk_size=16, max_loaded_chunks=25):
        self.chunk_size = chunk_size
        self.max_loaded_chunks = max_loaded_chunks  # Limitiere geladene Chunks
        self.chunks = {}
        self.loaded_chunks = set()
        self.chunk_blocks = defaultdict(list)  # Optimierte Block-Verwaltung
        self.last_cleanup = 0
        self.cleanup_interval = 5.0  # Cleanup alle 5 Sekunden
    
    def get_chunk_coords(self, world_pos):
        """Berechnet Chunk-Koordinaten aus Welt-Position"""
        if isinstance(world_pos, (tuple, list)) and len(world_pos) >= 3:
            return (
                int(world_pos[0] // self.chunk_size),
                int(world_pos[2] // self.chunk_size)
            )
        else:
            # Fallback für einzelne Koordinaten
            return (
                int(world_pos // self.chunk_size) if isinstance(world_pos, (int, float)) else 0,
                0
            )
    
    def load_chunk(self, chunk_x, chunk_z):
        """Lädt einen Chunk mit Performance-Optimierung"""
        chunk_key = (chunk_x, chunk_z)
        if chunk_key not in self.loaded_chunks:
            # Prüfe Chunk-Limit
            if len(self.loaded_chunks) >= self.max_loaded_chunks:
                self._cleanup_distant_chunks(chunk_x, chunk_z)
            
            self.chunks[chunk_key] = []
            self.loaded_chunks.add(chunk_key)
            return True
        return False
    
    def _cleanup_distant_chunks(self, center_x, center_z):
        """Entlädt weit entfernte Chunks"""
        chunks_to_unload = []
        for chunk_x, chunk_z in self.loaded_chunks:
            distance = abs(chunk_x - center_x) + abs(chunk_z - center_z)
            if distance > 3:  # Entlade Chunks die weiter als 3 Chunks entfernt sind
                chunks_to_unload.append((chunk_x, chunk_z))
        
        # Entlade die Hälfte der entfernten Chunks
        for chunk_key in chunks_to_unload[:len(chunks_to_unload)//2]:
            self.unload_chunk(chunk_key[0], chunk_key[1])
    
    def unload_chunk(self, chunk_x, chunk_z):
        """Entlädt einen Chunk mit Batch-Destruction"""
        chunk_key = (chunk_x, chunk_z)
        if chunk_key in self.loaded_chunks:
            if chunk_key in self.chunk_blocks:
                # Batch-Destruction für bessere Performance
                blocks_to_destroy = self.chunk_blocks[chunk_key]
                for block in blocks_to_destroy:
                    if block and hasattr(block, 'enabled'):
                        destroy(block)
                del self.chunk_blocks[chunk_key]
            
            if chunk_key in self.chunks:
                del self.chunks[chunk_key]
            self.loaded_chunks.remove(chunk_key)
    
    def add_block_to_chunk(self, block, world_pos):
        """Fügt Block zum entsprechenden Chunk hinzu - Optimiert"""
        chunk_coords = self.get_chunk_coords(world_pos)
        if chunk_coords not in self.loaded_chunks:
            self.load_chunk(*chunk_coords)
        
        self.chunk_blocks[chunk_coords].append(block)
        if chunk_coords in self.chunks:
            self.chunks[chunk_coords].append(block)
    
    def remove_block_from_chunk(self, block):
        """Entfernt Block aus Chunk-Management"""
        # Finde den Chunk des Blocks
        block_pos = (block.x, block.y, block.z)
        chunk_coords = self.get_chunk_coords(block_pos)
        
        if chunk_coords in self.chunk_blocks:
            try:
                self.chunk_blocks[chunk_coords].remove(block)
            except ValueError:
                pass  # Block nicht in Liste
        
        if chunk_coords in self.chunks:
            try:
                self.chunks[chunk_coords].remove(block)
            except ValueError:
                pass  # Block nicht in Liste
    
    def get_nearby_chunks(self, center_x, center_z, radius=2):
        """Gibt nahegelegene Chunks zurück"""
        nearby_chunks = []
        for x in range(center_x - radius, center_x + radius + 1):
            for z in range(center_z - radius, center_z + radius + 1):
                if (x, z) in self.loaded_chunks:
                    nearby_chunks.append((x, z))
        return nearby_chunks
    
    def periodic_cleanup(self):
        """Periodische Bereinigung für Performance"""
        import time
        current_time = time.time()
        if current_time - self.last_cleanup > self.cleanup_interval:
            # Entferne None-Referenzen aus Chunk-Listen
            for chunk_key in list(self.chunk_blocks.keys()):
                self.chunk_blocks[chunk_key] = [
                    block for block in self.chunk_blocks[chunk_key] 
                    if block and hasattr(block, 'enabled')
                ]
                if not self.chunk_blocks[chunk_key]:
                    del self.chunk_blocks[chunk_key]
            
            self.last_cleanup = current_time


# Globaler optimierter Chunk-Manager
chunk_manager = OptimizedChunkManager(chunk_size=16, max_loaded_chunks=20)

def register_default_blocks():
    """Registriert Standard-Blöcke - Reduziert für bessere Performance"""
    
    # Basis-Blöcke
    BlockRegistry.register('grass', 'grass', model='cube')
    BlockRegistry.register('stone', 'brick', model='cube')
    BlockRegistry.register('wood', 'wood', model='cube')
    BlockRegistry.register('dirt', 'wood', model='cube', color=ursina_color.brown)  # Fallback texture
    BlockRegistry.register('sand', 'white_cube', model='cube', color=ursina_color.yellow)
    BlockRegistry.register('cobblestone', 'brick', model='cube', color=ursina_color.gray)
    
    # Spezielle Blöcke
    BlockRegistry.register('glass', 'white_cube', model='cube', color=ursina_color.clear, walkthrough=True)
    BlockRegistry.register('water', 'white_cube', model='cube', color=ursina_color.blue.tint(-.3), walkthrough=True)
    BlockRegistry.register('leaves', 'white_cube', model='cube', color=ursina_color.green, walkthrough=True)
    
    print(f"[BlockRegistry] {len(BlockRegistry.registry)} Blöcke registriert")

def create_optimized_world(width, height, depth, ground_level=-10, block_type='grass'):
    """
    Hochoptimierte Welt-Generierung mit Batch-Creation
    """
    print(f"[Performance] Generiere optimierte Welt: {width}x{height}x{depth}")
    
    # Batch-Erstellung für bessere Performance
    blocks_to_create = []
    for x in range(width):
        for z in range(depth):
            for y in range(ground_level, ground_level + height):
                blocks_to_create.append((x, y, z))
    
    # Erstelle Blöcke in Batches
    batch_size = 100
    blocks_created = 0
    
    for i in range(0, len(blocks_to_create), batch_size):
        batch = blocks_to_create[i:i+batch_size]
        for x, y, z in batch:
            block = BlockRegistry.create(block_type, position=(x, y, z))
            if block:
                chunk_manager.add_block_to_chunk(block, (x, y, z))
                blocks_created += 1
        
        # Progress-Update
        if i % (batch_size * 10) == 0:
            progress = (i / len(blocks_to_create)) * 100
            print(f"[Performance] Fortschritt: {progress:.1f}% ({blocks_created} Blöcke)")
    
    print(f"[Performance] Welt-Generierung abgeschlossen: {blocks_created} Blöcke erstellt")

def create_performance_optimized_area(start_pos, end_pos, block_type='grass'):
    """
    Erstellt einen Bereich mit maximaler Performance-Optimierung
    """
    blocks = []
    positions = []
    
    # Sammle alle Positionen
    for x in range(int(start_pos[0]), int(end_pos[0]) + 1):
        for y in range(int(start_pos[1]), int(end_pos[1]) + 1):
            for z in range(int(start_pos[2]), int(end_pos[2]) + 1):
                positions.append((x, y, z))
    
    # Batch-Erstellung
    batch_size = 50
    for i in range(0, len(positions), batch_size):
        batch = positions[i:i+batch_size]
        for pos in batch:
            block = BlockRegistry.create(block_type, position=pos)
            if block:
                blocks.append(block)
                chunk_manager.add_block_to_chunk(block, pos)
    
    return blocks

# Registriere Standard-Blöcke beim Import
register_default_blocks()

# Legacy-Funktionen für Kompatibilität
current_block = 'grass'

def get_block_texture(block_name):
    """Legacy-Funktion für Inventarsystem"""
    return BlockRegistry.get_texture(block_name)

def get_registered_blocks():
    """Legacy-Funktion: Gibt Dictionary mit block_name: texture zurück"""
    legacy_dict = {}
    for name in BlockRegistry.list_blocks():
        legacy_dict[name] = BlockRegistry.get_texture(name)
    return legacy_dict

def get_performance_stats():
    """Gibt erweiterte Performance-Statistiken zurück"""
    return {
        'loaded_chunks': len(chunk_manager.loaded_chunks),
        'cached_textures': len(BlockRegistry._texture_cache),
        'cached_models': len(BlockRegistry._model_cache),
        'registered_blocks': len(BlockRegistry.registry),
        'total_blocks_in_chunks': sum(len(blocks) for blocks in chunk_manager.chunk_blocks.values()),
        'max_loaded_chunks': chunk_manager.max_loaded_chunks
    }

# Periodische Cleanup-Funktion
def update_performance():
    """Sollte regelmäßig aufgerufen werden für optimale Performance"""
    chunk_manager.periodic_cleanup()
