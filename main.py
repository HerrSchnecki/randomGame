from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import time
import random

from block import BlockRegistry, get_performance_stats
from skybox import Skybox
from world_generator import create_world_generator, update_world_around_player
from inventory import create_inventory, handle_inventory_input, get_current_block, add_new_block_type

# Basic App Setup
app = Ursina()

window.fps_counter.enabled = True
window.title = 'HyMine - Optimized World Generator'
window.vsync = True  # Aktiviert für stabilere Performance
mouse.locked = True

class SimplePerformanceMonitor:
    """Vereinfachte Performance-Überwachung"""
    
    def __init__(self):
        self.last_time = time.time()
        self.frame_count = 0
        self.update_interval = 1.0
        self.world_gen = None
        
        # Kompakte Anzeige
        self.fps_display = Text(
            '',
            position=(-0.85, 0.45),
            color=color.yellow,
            scale=0.6
        )
        self.stats_display = Text(
            '',
            position=(-0.85, 0.38),
            color=color.light_gray,
            scale=0.5
        )
        
    def set_world_generator(self, world_gen):
        self.world_gen = world_gen
    
    def update(self):
        self.frame_count += 1
        current_time = time.time()
        
        if current_time - self.last_time >= self.update_interval:
            fps = self.frame_count / (current_time - self.last_time)
            
            self.fps_display.text = f'FPS: {fps:.1f}'
            
            if self.world_gen:
                stats = self.world_gen.get_stats()
                self.stats_display.text = (
                    f"Chunks: {stats['loaded_chunks']} | "
                    f"Blocks: {stats['total_blocks']} | "
                    f"Seed: {stats['seed']}"
                )
            
            self.frame_count = 0
            self.last_time = current_time
    
    def toggle_visibility(self):
        visible = not self.fps_display.visible
        self.fps_display.visible = visible
        self.stats_display.visible = visible

# Globale Variablen
perf_monitor = SimplePerformanceMonitor()
world_generator = None

# Player Setup
player = FirstPersonController()
player.cursor.visible = True
player.speed = 8  # Reduziert für stabilere Bewegung
player.mouse_sensitivity = Vec2(40, 40)
player.jump_height = 2
player.jump_duration = 0.4

def initialize_game():
    """Initialisiert das Spiel"""
    global world_generator
    
    print("=== HyMine - Optimized Version ===")
    start_time = time.time()
    
    # Blöcke registrieren
    print("Registriere Blöcke...")
    
    BlockRegistry.register('grass', 'assets/textures/blocks/grass')
    BlockRegistry.register('stone', 'assets/textures/blocks/stone')
    BlockRegistry.register('dirt', 'assets/textures/blocks/dirt')
    BlockRegistry.register('wood', 'assets/textures/blocks/wood')
    BlockRegistry.register('sand', 'assets/textures/blocks/sand')
    BlockRegistry.register('cobblestone', 'assets/textures/blocks/cobblestone')
    
    # Spezielle Blöcke
    BlockRegistry.register('water', 'assets/textures/blocks/water', walkthrough=True)
    BlockRegistry.register('glass', 'white_cube', color=color.clear, walkthrough=True)
    BlockRegistry.register('leaves', 'assets/textures/blocks/leaves', walkthrough=True)
    
    # Inventar erstellen
    print("Erstelle Inventar...")
    inventory = create_inventory()
    
    # Verfügbare Blöcke hinzufügen
    available_blocks = ['grass', 'stone', 'dirt', 'wood', 'sand', 'cobblestone', 'glass', 'leaves']
    for block_type in available_blocks:
        add_new_block_type(block_type)
    
    # World Generator erstellen
    print("Initialisiere World Generator...")
    
    WORLD_SEED = 12345
    RENDER_DISTANCE = 2  # Reduziert für bessere Performance
    
    world_generator = create_world_generator(
        seed=WORLD_SEED,
        render_distance=RENDER_DISTANCE
    )
    
    perf_monitor.set_world_generator(world_generator)
    
    # Spawn Bereich generieren
    print("Generiere Spawn-Bereich...")
    
    spawn_x, spawn_z = 0, 0
    spawn_height = world_generator.get_height_at(spawn_x, spawn_z)
    
    world_generator.generate_spawn_area(spawn_x, spawn_z, radius=1)
    player.position = (spawn_x, spawn_height + 2, spawn_z)
    
    # Skybox
    try:
        sky = Skybox(texture='assets/skyboxes/day')
        print("Skybox geladen")
    except:
        sky = Sky()
        print("Standard-Himmel verwendet")
    
    # Beleuchtung
    sun = DirectionalLight()
    sun.look_at(Vec3(1, -1, -1))
    sun.color = color.white
    
    AmbientLight(color=color.rgba(100, 100, 100, 0.1))
    
    total_time = time.time() - start_time
    print(f"Initialisierung abgeschlossen in {total_time:.2f}s")
    print(f"Spieler gespawnt bei ({spawn_x}, {spawn_height + 2}, {spawn_z})")
    
    print("\n=== Controls ===")
    print("F1 - Performance anzeigen/verstecken")
    print("F3 - World-Statistiken")
    print("F4 - Neue Welt generieren")
    print("ESC - Maus freigeben/sperren")

# Chunk Update System
last_chunk_update = time.time()
chunk_update_interval = 0.5  # Weniger häufige Updates
last_player_chunk = None

def input(key):
    """Eingabe-Handler"""
    global world_generator, last_player_chunk
    
    # Inventar Input hat Priorität
    if handle_inventory_input(key):
        return
    
    if key == 'escape':
        mouse.locked = not mouse.locked
        return
    
    if key == 'f1':
        perf_monitor.toggle_visibility()
    
    elif key == 'f3':
        # World Statistiken
        if world_generator:
            stats = world_generator.get_stats()
            print("\n=== World Statistics ===")
            print(f"Seed: {stats['seed']}")
            print(f"Loaded Chunks: {stats['loaded_chunks']}")
            print(f"Total Blocks: {stats['total_blocks']}")
            print(f"Render Distance: {stats['render_distance']}")
            print("========================\n")
    
    elif key == 'f4':
        # Neue Welt generieren
        if world_generator:
            print("Generiere neue Welt...")
            new_seed = random.randint(0, 999999)
            
            world_generator = create_world_generator(
                seed=new_seed,
                render_distance=2
            )
            perf_monitor.set_world_generator(world_generator)
            
            # Neuen Spawn
            spawn_height = world_generator.get_height_at(0, 0)
            world_generator.generate_spawn_area(0, 0, radius=1)
            player.position = (0, spawn_height + 2, 0)
            last_player_chunk = None
            
            print(f"Neue Welt mit Seed {new_seed} generiert")

def update():
    """Haupt-Update-Loop"""
    global last_chunk_update, last_player_chunk
    
    # Performance Monitor
    perf_monitor.update()
    
    # Kamera Rotation begrenzen
    if hasattr(player, 'camera_pivot'):
        player.camera_pivot.rotation_x = max(-90, min(90, player.camera_pivot.rotation_x))
    
    # Chunk Updates
    current_time = time.time()
    if current_time - last_chunk_update > chunk_update_interval:
        if world_generator:
            current_player_chunk = world_generator.get_chunk_coords(player.x, player.z)
            
            # Update nur bei Chunk-Wechsel
            if current_player_chunk != last_player_chunk:
                loaded, unloaded = update_world_around_player(world_generator, player)
                last_player_chunk = current_player_chunk
                
                if loaded > 0 or unloaded > 0:
                    print(f"Chunks: +{loaded} -{unloaded}")
        
        last_chunk_update = current_time
    
    # Anti-Fall-System
    if world_generator and player.y < -20:
        ground_height = world_generator.get_height_at(player.x, player.z)
        player.position = (player.x, ground_height + 2, player.z)
        print("Spieler aus Void gerettet")

# Hauptprogramm
if __name__ == "__main__":
    try:
        initialize_game()
        print("Starte Spiel...")
        app.run()
        
    except KeyboardInterrupt:
        print("\nSpiel beendet")
    except Exception as e:
        print(f"Fehler: {e}")
        import traceback
        traceback.print_exc()
