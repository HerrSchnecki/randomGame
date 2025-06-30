from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import time

from block import BlockRegistry, create_optimized_world, get_performance_stats
from skybox import Skybox
from world import World
from inventory import create_inventory, handle_inventory_input, get_current_block, add_new_block_type

application.development_mode = False
application.asset_folder = Path(__file__).parent

app = Ursina()

window.fps_counter.enabled = True
window.exit_button.visible = True
window.title = 'HyMine - Optimized'
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
        self.update_interval = 1.0
    
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
            
            self.frame_count = 0
            self.last_time = current_time

perf_monitor = PerformanceMonitor()

player = FirstPersonController()
player.cursor.visible = True
player.speed = 5
player.mouse_sensitivity = Vec2(40, 40)

print("[Main] Registriere Blöcke...")
start_time = time.time()

BlockRegistry.register('grass', 'assets/textures/blocks/grass')
BlockRegistry.register('stone', 'assets/textures/blocks/stone')
BlockRegistry.register('dirt', 'assets/textures/blocks/dirt')
BlockRegistry.register('wood', 'assets/textures/blocks/wood')
BlockRegistry.register('sand', 'assets/textures/blocks/sand')
BlockRegistry.register('water', 'assets/textures/blocks/water', walkthrough=True)
BlockRegistry.register('test', 'assets/textures/blocks/test')
BlockRegistry.register('cobblestone', 'assets/textures/blocks/cobblestone')

BlockRegistry.register('glass', 'white_cube', color=color.clear, walkthrough=True)
BlockRegistry.register('leaves', 'assets/textures/blocks/leaves', walkthrough=True)

print(f"[Main] Block-Registrierung abgeschlossen in {time.time() - start_time:.2f}s")

print("[Main] Erstelle Inventarsystem...")
inventory = create_inventory()
add_new_block_type('test')
add_new_block_type('glass')
add_new_block_type('leaves')

print("[Main] Generiere Welt...")
world_start_time = time.time()

world_size = 50
ground_thickness = 3

for y_level in range(-12, -9):
    block_type = 'stone' if y_level < -10 else 'dirt'
    for x in range(world_size):
        for z in range(world_size):
            if (x + z) % 2 == 0:
                BlockRegistry.create(block_type, position=(x, y_level, z))

for x in range(world_size):
    for z in range(world_size):
        BlockRegistry.create('grass', position=(x, -9, z))

print(f"[Main] Welt-Generierung abgeschlossen in {time.time() - world_start_time:.2f}s")

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

def input(key):
    if handle_inventory_input(key):
        return
    
    if key == 'escape':
        mouse.locked = not mouse.locked
        return
    
    if application.development_mode:
        if key == 'f1':
            perf_monitor.fps_display.visible = not perf_monitor.fps_display.visible
            perf_monitor.stats_display.visible = not perf_monitor.stats_display.visible
        
        if key == 'f2':
            for entity in scene.entities:
                if hasattr(entity, 'model') and entity.model:
                    entity.wireframe = not getattr(entity, 'wireframe', False)

def update():
    perf_monitor.update()
    
    player_chunk = (int(player.x // 16), int(player.z // 16))
    
    if hasattr(player, 'camera_pivot'):
        player.camera_pivot.rotation_x = max(-90, min(90, player.camera_pivot.rotation_x))

player.position = (world_size // 2, 0, world_size // 2)

if __name__ == "__main__":
    app.run()
