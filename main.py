from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import time

from block import BlockRegistry, get_performance_stats
from skybox import Skybox
from world_generator import NoiseGenerator, BiomeGenerator, ChunkGenerator, WorldGenerator 
from inventory import create_inventory, handle_inventory_input, get_current_block, add_new_block_type
from world_generator import create_world_generator, update_world_around_player

application.development_mode = False
application.asset_folder = Path(__file__).parent

app = Ursina()

window.fps_counter.enabled = True
window.exit_button.visible = True
window.title = 'HyMine - Random World Generator'
window.vsync = False 
mouse.locked = True

class PerformanceMonitor:
    def __init__(self):
        self.last_time = time.time()
        self.frame_count = 0
        self.fps_display = Text(
            '',
            position=(-0.85, 0.45),
            color=color.yellow,
            scale=0.7
        )
        self.stats_display = Text(
            '',
            position=(-0.85, 0.38),
            color=color.light_gray,
            scale=0.5
        )
        self.world_display = Text(
            '',
            position=(-0.85, 0.31),
            color=color.cyan,
            scale=0.5
        )
        self.update_interval = 1.0
        self.world_gen = None
    
    def set_world_generator(self, world_gen):
        self.world_gen = world_gen
    
    def update(self):
        self.frame_count += 1
        current_time = time.time()
        
        if current_time - self.last_time >= self.update_interval:
            fps = self.frame_count / (current_time - self.last_time)
            self.fps_display.text = f'FPS: {fps:.1f}'
            
            stats = get_performance_stats()
            self.stats_display.text = (
                f"Chunks: {stats['loaded_chunks']} | "
                f"Texturen: {stats['cached_textures']} | "
                f"Blöcke: {stats['registered_blocks']}"
            )
            
            if self.world_gen:
                world_stats = self.world_gen.get_stats()
                self.world_display.text = (
                    f"Welt-Chunks: {world_stats['loaded_chunks']} | "
                    f"Welt-Blöcke: {world_stats['total_blocks']} | "
                    f"Seed: {world_stats['seed']}"
                )
            
            self.frame_count = 0
            self.last_time = current_time

perf_monitor = PerformanceMonitor()

player = FirstPersonController()
player.cursor.visible = True
player.speed = 8  # Etwas schneller für große Welt
player.mouse_sensitivity = Vec2(40, 40)

print("[Main] Registriere Blöcke...")
start_time = time.time()

# Standard-Blöcke registrieren
BlockRegistry.register('grass', 'assets/textures/blocks/grass')
BlockRegistry.register('stone', 'assets/textures/blocks/stone')
BlockRegistry.register('dirt', 'assets/textures/blocks/dirt')
BlockRegistry.register('wood', 'assets/textures/blocks/wood')
BlockRegistry.register('sand', 'assets/textures/blocks/sand')
BlockRegistry.register('water', 'assets/textures/blocks/water', walkthrough=True)
BlockRegistry.register('test', 'assets/textures/blocks/test')
BlockRegistry.register('cobblestone', 'assets/textures/blocks/cobblestone')

# Zusätzliche Blöcke für World Generation
BlockRegistry.register('glass', 'white_cube', color=color.clear, walkthrough=True)
BlockRegistry.register('leaves', 'assets/textures/blocks/leaves', walkthrough=True)

print(f"[Main] Block-Registrierung abgeschlossen in {time.time() - start_time:.2f}s")

print("[Main] Erstelle Inventarsystem...")
inventory = create_inventory()
add_new_block_type('test')
add_new_block_type('glass')
add_new_block_type('leaves')
add_new_block_type('sand')
add_new_block_type('cobblestone')

# === World Generator erstellen ===
print("[Main] Initialisiere World Generator...")
world_gen_start = time.time()

# Konfiguration für World Generator
WORLD_SEED = 12345  # Ändere das für verschiedene Welten
CHUNK_SIZE = 16     # Größe eines Chunks (16x16 Blöcke)
RENDER_DISTANCE = 4 # Wie viele Chunks um den Spieler geladen werden

world_generator = create_world_generator(
    seed=WORLD_SEED,
    chunk_size=CHUNK_SIZE,
    render_distance=RENDER_DISTANCE
)

perf_monitor.set_world_generator(world_generator)

print(f"[Main] World Generator initialisiert in {time.time() - world_gen_start:.2f}s")

# === Spawn-Bereich generieren ===
print("[Main] Generiere Spawn-Bereich...")
spawn_start = time.time()

# Spawn-Position festlegen
spawn_x, spawn_z = 0, 0
spawn_height = world_generator.get_height_at(spawn_x, spawn_z)

# Kleinen Bereich um Spawn generieren
world_generator.generate_spawn_area(spawn_x, spawn_z, radius=2)

print(f"[Main] Spawn-Bereich generiert in {time.time() - spawn_start:.2f}s")

# === Skybox erstellen ===
print("[Main] Erstelle Skybox...")
try:
    sky = Skybox(texture='assets/skyboxes/day')
except:
    print("[Main] Skybox-Texture nicht gefunden, verwende Standard-Himmel")
    sky = Sky()

# === Beleuchtung optimieren ===
sun = DirectionalLight()
sun.look_at(Vec3(1, -1, -1))
sun.color = color.white
sun.shadows = True

# Ambiente Beleuchtung
AmbientLight(color=color.rgba(100, 100, 100, 0.1))

# === Variablen für Chunk-Updates ===
last_chunk_update = time.time()
chunk_update_interval = 0.5  # Chunks alle 0.5 Sekunden überprüfen
last_player_chunk = None

def input(key):
    global world_generator  # Global-Deklaration am Anfang der Funktion
    
    if handle_inventory_input(key):
        return
    
    if key == 'escape':
        mouse.locked = not mouse.locked
        return
    
    # Debug-Keys
    if application.development_mode:
        if key == 'f1':
            perf_monitor.fps_display.visible = not perf_monitor.fps_display.visible
            perf_monitor.stats_display.visible = not perf_monitor.stats_display.visible
            perf_monitor.world_display.visible = not perf_monitor.world_display.visible
        
        if key == 'f2':
            for entity in scene.entities:
                if hasattr(entity, 'model') and entity.model:
                    entity.wireframe = not getattr(entity, 'wireframe', False)
        
        if key == 'f3':
            # World Stats ausgeben
            stats = world_generator.get_stats()
            print(f"[Debug] World Stats: {stats}")
        
        if key == 'f4':
            # Neue Welt mit zufälligem Seed
            new_seed = random.randint(0, 999999)
            print(f"[Debug] Generiere neue Welt mit Seed: {new_seed}")
            
            # Alte Welt aufräumen (vereinfacht)
            world_generator = create_world_generator(
                seed=new_seed,
                chunk_size=CHUNK_SIZE,
                render_distance=RENDER_DISTANCE
            )
            perf_monitor.set_world_generator(world_generator)
            
            # Neuen Spawn generieren
            new_spawn_height = world_generator.get_height_at(0, 0)
            world_generator.generate_spawn_area(0, 0, radius=2)
            player.position = (0, new_spawn_height + 2, 0)


def update():
    global last_chunk_update, last_player_chunk
    
    perf_monitor.update()
    
    # Kamera-Rotation begrenzen
    if hasattr(player, 'camera_pivot'):
        player.camera_pivot.rotation_x = max(-90, min(90, player.camera_pivot.rotation_x))
    
    # Chunk-Updates (nicht jeden Frame)
    current_time = time.time()
    if current_time - last_chunk_update > chunk_update_interval:
        current_player_chunk = world_generator.get_chunk_coords(player.x, player.z)
        
        # Nur updaten wenn Spieler Chunk gewechselt hat
        if current_player_chunk != last_player_chunk:
            loaded, unloaded = update_world_around_player(world_generator, player)
            last_player_chunk = current_player_chunk
        
        last_chunk_update = current_time
    
    # Spieler über Wasser halten (einfache Kollision)
    ground_height = world_generator.get_height_at(player.x, player.z)
    if player.y < ground_height:
        player.y = ground_height + 2

# === Spieler-Startposition setzen ===
player.position = (spawn_x, spawn_height + 2, spawn_z)

print(f"[Main] Spieler gespawnt at ({spawn_x}, {spawn_height + 2}, {spawn_z})")
if application.development_mode:
    print("=== Debug-Keys ===")
    print("F1 - Performance-Anzeige umschalten")
    print("F2 - Wireframe-Modus")
    print("F3 - World-Statistiken")
    print("F4 - Neue zufällige Welt")

if __name__ == "__main__":
    app.run()
