from ursina import *
from ursina import color as ursina_color
import os

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


class Block(Button):
    _default_color = None
    _collision_enabled = True
    
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
        
        self._setup_collision(walkthrough)

    def _setup_collision(self, walkthrough):
        """Optimierte Kollisions-Setup"""
        if walkthrough:
            self.collider = None
            self.collision = True
        else:
            self.collider = 'box'
            self.collision = True

    def input(self, key):
        if not self.hovered:
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
                    print(f"Block '{current_block}' platziert an Position {new_position}")
            else:
                print("Kein Block im Inventar ausgewählt!")
        except ImportError:
            print("Inventarsystem nicht verfügbar, verwende Standard-Block")
            current_block = 'grass'
            BlockRegistry.create(current_block, position=self.position + mouse.normal)

    def _handle_break_block(self):
        """Optimierte Block-Zerstörung"""
        block_type = "walkthrough" if self.walkthrough else "solid"
        print(f"{block_type.capitalize()}-Block abgebaut an Position {self.position}")
        destroy(self)

    def set_walkthrough(self, walkthrough):
        """Ändert die Walkthrough-Eigenschaft zur Laufzeit"""
        self.walkthrough = walkthrough
        self._setup_collision(walkthrough)


class ChunkManager:
    """Verwaltet Chunks für bessere Performance bei großen Welten"""
    def __init__(self, chunk_size=16):
        self.chunk_size = chunk_size
        self.chunks = {}
        self.loaded_chunks = set()
    
    def get_chunk_coords(self, world_pos):
        """Berechnet Chunk-Koordinaten aus Welt-Position"""
        return (
            int(world_pos[0] // self.chunk_size),
            int(world_pos[2] // self.chunk_size)
        )
    
    def load_chunk(self, chunk_x, chunk_z):
        """Lädt einen Chunk"""
        chunk_key = (chunk_x, chunk_z)
        if chunk_key not in self.loaded_chunks:
            self.chunks[chunk_key] = []
            self.loaded_chunks.add(chunk_key)
            return True
        return False
    
    def unload_chunk(self, chunk_x, chunk_z):
        """Entlädt einen Chunk"""
        chunk_key = (chunk_x, chunk_z)
        if chunk_key in self.loaded_chunks:
            if chunk_key in self.chunks:
                for block in self.chunks[chunk_key]:
                    if block:
                        destroy(block)
                del self.chunks[chunk_key]
            self.loaded_chunks.remove(chunk_key)
    
    def add_block_to_chunk(self, block, world_pos):
        """Fügt Block zum entsprechenden Chunk hinzu"""
        chunk_coords = self.get_chunk_coords(world_pos)
        if chunk_coords not in self.chunks:
            self.load_chunk(*chunk_coords)
        self.chunks[chunk_coords].append(block)

chunk_manager = ChunkManager()

def register_default_blocks():
    """Registriert Standard-Blöcke mit verschiedenen Models"""
    
    BlockRegistry.register('grass', 'grass', model='cube')
    BlockRegistry.register('stone', 'brick', model='cube')
    BlockRegistry.register('wood', 'wood', model='cube')
    
    BlockRegistry.register('glass', 'white_cube', model='cube', color=ursina_color.clear, walkthrough=True)
    BlockRegistry.register('air_block', 'white_cube', model='cube', color=ursina_color.rgba(255,255,255,0.1), walkthrough=True)
    BlockRegistry.register('water', 'white_cube', model='cube', color=ursina_color.blue.tint(-.3), walkthrough=True)
    
    BlockRegistry.register('sphere_block', 'white_cube', model='sphere', color=ursina_color.blue)
    BlockRegistry.register('cylinder_block', 'brick', model='cylinder', color=ursina_color.red)
    BlockRegistry.register('plane_block', 'grass', model='plane', scale=0.1, color=ursina_color.green, walkthrough=True)
    
    BlockRegistry.register('big_cube', 'wood', model='cube', scale=2, color=ursina_color.brown)
    BlockRegistry.register('small_sphere', 'white_cube', model='sphere', scale=0.5, color=ursina_color.yellow, walkthrough=True)
    
    print(f"[BlockRegistry] {len(BlockRegistry.registry)} Standard-Blöcke registriert")

def register_custom_model_block(name, texture, model_url, scale=1, color=None, walkthrough=False):
    """
    Vereinfachte Funktion zum Registrieren von Custom Model Blöcken
    """
    BlockRegistry.register(name, texture, model='cube', scale=scale, color=color, 
                          walkthrough=walkthrough, model_url=model_url)

def create_walkthrough_area(start_pos, end_pos, block_type='air_block'):
    """
    Erstellt einen Bereich mit walkthrough-Blöcken (optimiert für große Bereiche)
    """
    blocks = []
    total_blocks = (end_pos[0] - start_pos[0] + 1) * (end_pos[1] - start_pos[1] + 1) * (end_pos[2] - start_pos[2] + 1)
    
    if total_blocks > 1000:
        print(f"[Performance] Erstelle {total_blocks} Blöcke - das kann einen Moment dauern...")
    
    for x in range(int(start_pos[0]), int(end_pos[0]) + 1):
        for y in range(int(start_pos[1]), int(end_pos[1]) + 1):
            for z in range(int(start_pos[2]), int(end_pos[2]) + 1):
                block = BlockRegistry.create(block_type, position=(x, y, z))
                if block:
                    blocks.append(block)
                    chunk_manager.add_block_to_chunk(block, (x, y, z))
    
    print(f"[Performance] {len(blocks)} Blöcke erstellt")
    return blocks

def create_optimized_world(width, height, depth, ground_level=-10, block_type='grass'):
    """
    Optimierte Welt-Generierung mit Chunk-System
    """
    print(f"[Performance] Generiere optimierte Welt: {width}x{height}x{depth}")
    
    blocks_created = 0
    for x in range(width):
        for z in range(depth):
            for y in range(ground_level, ground_level + height):
                block = BlockRegistry.create(block_type, position=(x, y, z))
                if block:
                    chunk_manager.add_block_to_chunk(block, (x, y, z))
                    blocks_created += 1
        
        if x % 10 == 0:
            print(f"[Performance] Fortschritt: {x}/{width} Spalten erstellt ({blocks_created} Blöcke)")
    
    print(f"[Performance] Welt-Generierung abgeschlossen: {blocks_created} Blöcke erstellt")

register_default_blocks()

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
    """Gibt Performance-Statistiken zurück"""
    return {
        'loaded_chunks': len(chunk_manager.loaded_chunks),
        'cached_textures': len(BlockRegistry._texture_cache),
        'cached_models': len(BlockRegistry._model_cache),
        'registered_blocks': len(BlockRegistry.registry)
    }
