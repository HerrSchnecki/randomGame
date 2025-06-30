from ursina import *
from ursina import color as ursina_color
import os

class BlockRegistry:
    registry = {}

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

    @classmethod
    def create(cls, name, position=(0, 0, 0)):
        if name not in cls.registry:
            print(f"[BlockRegistry] Block '{name}' nicht registriert!")
            return None
        
        block_data = cls.registry[name]
        
        # Custom Model laden falls URL vorhanden
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
        try:
            import urllib.request
            import urllib.parse
            
            # Erstelle models Ordner falls nicht vorhanden
            if not os.path.exists('models'):
                os.makedirs('models')
            
            # Extrahiere Dateiname und Erweiterung aus URL
            parsed_url = urllib.parse.urlparse(url)
            filename = os.path.basename(parsed_url.path)
            if not filename or '.' not in filename:
                filename = f"{block_name}_model.obj"  # Fallback-Name
            
            local_path = os.path.join('models', filename)
            
            # Download nur falls Datei nicht existiert
            if not os.path.exists(local_path):
                print(f"[BlockRegistry] Lade Model herunter: {url}")
                urllib.request.urlretrieve(url, local_path)
                print(f"[BlockRegistry] Model gespeichert als: {local_path}")
            
            return local_path
            
        except Exception as e:
            print(f"[BlockRegistry] Fehler beim Laden des Models von {url}: {e}")
            print(f"[BlockRegistry] Verwende Fallback-Model: {fallback_model}")
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
    def __init__(self, position=(0, 0, 0), texture='white_cube', model='cube', scale=1, color=None, walkthrough=False):
        # Standard-Farbe falls keine angegeben
        if color is None:
            block_color = ursina_color.color(0, 0, random.uniform(0.9, 1))
        else:
            block_color = color
            
        super().__init__(
            parent=scene,
            position=position,
            model=model,
            origin_y=0.5,
            texture=texture,
            color=block_color,
            scale=scale
        )
        
        # Walkthrough-Eigenschaft speichern
        self.walkthrough = walkthrough
        
        # Für walkthrough-Blöcke: Maus-Interaktion aktiviert lassen, aber Spieler-Kollision deaktivieren
        if walkthrough:
            # Spieler kann durch den Block laufen (kein physischer Collider)
            self.collider = None
            # Aber Maus-Interaktion bleibt aktiv für Abbau/Platzierung
            self.collision = True
        else:
            # Standard Kollision für feste Blöcke
            self.collider = 'box'
            self.collision = True

    def input(self, key):
        if self.hovered:
            if key == 'right mouse down':
                try:
                    from inventory import get_current_block
                    current_block = get_current_block()
                    if current_block:
                        new_block = BlockRegistry.create(current_block, position=self.position + mouse.normal)
                        if new_block:
                            print(f"Block '{current_block}' platziert an Position {self.position + mouse.normal}")
                    else:
                        print("Kein Block im Inventar ausgewählt!")
                except ImportError:
                    print("Inventarsystem nicht verfügbar, verwende Standard-Block")
                    current_block = 'grass'
                    BlockRegistry.create(current_block, position=self.position + mouse.normal)
            
            if key == 'left mouse down':
                block_type = "walkthrough" if self.walkthrough else "solid"
                print(f"{block_type.capitalize()}-Block abgebaut an Position {self.position}")
                destroy(self)

    def set_walkthrough(self, walkthrough):
        """Ändert die Walkthrough-Eigenschaft zur Laufzeit"""
        self.walkthrough = walkthrough
        if walkthrough:
            # Walkthrough: Keine Spieler-Kollision, aber Maus-Interaktion
            self.collider = None
            self.collision = True
        else:
            # Solid: Vollständige Kollision
            self.collider = 'box'
            self.collision = True


# Beispiel-Registrierungen verschiedener Block-Typen
def register_default_blocks():
    """Registriert Standard-Blöcke mit verschiedenen Models"""
    
    # Standard Würfel-Blöcke (solid)
    BlockRegistry.register('grass', 'grass', model='cube')
    BlockRegistry.register('stone', 'brick', model='cube')
    BlockRegistry.register('wood', 'wood', model='cube')
    
    # Walkthrough-Blöcke (kann man durchlaufen, aber trotzdem abbauen)
    BlockRegistry.register('glass', 'white_cube', model='cube', color=ursina_color.clear, walkthrough=True)
    BlockRegistry.register('air_block', 'white_cube', model='cube', color=ursina_color.rgba(255,255,255,0.1), walkthrough=True)
    BlockRegistry.register('water', 'white_cube', model='cube', color=ursina_color.blue.tint(-.3), walkthrough=True)
    
    # Blöcke mit anderen Models
    BlockRegistry.register('sphere_block', 'white_cube', model='sphere', color=ursina_color.blue)
    BlockRegistry.register('cylinder_block', 'brick', model='cylinder', color=ursina_color.red)
    BlockRegistry.register('plane_block', 'grass', model='plane', scale=0.1, color=ursina_color.green, walkthrough=True)
    
    # Custom skalierte Blöcke
    BlockRegistry.register('big_cube', 'wood', model='cube', scale=2, color=ursina_color.brown)
    BlockRegistry.register('small_sphere', 'white_cube', model='sphere', scale=0.5, color=ursina_color.yellow, walkthrough=True)
    
    # Beispiele für Custom Models aus dem Internet (URLs müssen gültig sein)
    # BlockRegistry.register('custom_tree', 'wood', 
    #                       model_url='https://example.com/models/tree.obj',
    #                       model='cube',  # Fallback
    #                       scale=1.5, 
    #                       color=ursina_color.green)
    
    # BlockRegistry.register('custom_rock', 'brick',
    #                       model_url='https://example.com/models/rock.fbx',
    #                       model='cube',  # Fallback
    #                       walkthrough=False)

# Hilfsfunktionen für erweiterte Funktionalität
def register_custom_model_block(name, texture, model_url, scale=1, color=None, walkthrough=False):
    """
    Vereinfachte Funktion zum Registrieren von Custom Model Blöcken
    """
    BlockRegistry.register(name, texture, model='cube', scale=scale, color=color, 
                          walkthrough=walkthrough, model_url=model_url)

def create_walkthrough_area(start_pos, end_pos, block_type='air_block'):
    """
    Erstellt einen Bereich mit walkthrough-Blöcken
    """
    blocks = []
    for x in range(int(start_pos[0]), int(end_pos[0]) + 1):
        for y in range(int(start_pos[1]), int(end_pos[1]) + 1):
            for z in range(int(start_pos[2]), int(end_pos[2]) + 1):
                block = BlockRegistry.create(block_type, position=(x, y, z))
                if block:
                    blocks.append(block)
    return blocks

# Standard-Blöcke registrieren
register_default_blocks()

# Globale Variable für Rückwärtskompatibilität
current_block = 'grass'

# Rückwärtskompatibilitäts-Wrapper für altes Inventarsystem
def get_block_texture(block_name):
    """Legacy-Funktion für Inventarsystem"""
    return BlockRegistry.get_texture(block_name)

def get_registered_blocks():
    """Legacy-Funktion: Gibt Dictionary mit block_name: texture zurück"""
    legacy_dict = {}
    for name in BlockRegistry.list_blocks():
        legacy_dict[name] = BlockRegistry.get_texture(name)
    return legacy_dict
