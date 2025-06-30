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

# Window Settings
window.fps_counter.enabled = True
window.title = 'HyMine - Optimized World Generator'
window.vsync = False  # Disable VSync for better performance
window.borderless = False
window.fullscreen = False

# Mouse Settings
mouse.locked = True
camera.fov = 90

class SimplePerformanceMonitor:
    def __init__(self):
        self.last_time = time.time()
        self.frame_count = 0
        self.update_interval = 1.0
        self.world_gen = None
        
        # Performance Display
        self.fps_display = Text(
            text='',  # Added text parameter
            position=(-0.85, 0.45),
            color=color.yellow,
            scale=0.6
        )
        self.stats_display = Text(
            text='',  # Added text parameter
            position=(-0.85, 0.38),
            color=color.light_gray,
            scale=0.5
        )
        
        # Loading Display
        self.loading_display = Text(
            text='Initializing...',  # Added text parameter
            position=(0, 0),
            color=color.white,
            scale=1.5,
            origin=(0, 0)
        )
        
    def set_world_generator(self, world_gen):
        self.world_gen = world_gen
    
    def set_loading_text(self, text):
        if hasattr(self, 'loading_display') and self.loading_display:  # Check if attribute exists
            self.loading_display.text = text
    
    def hide_loading(self):
        if hasattr(self, 'loading_display') and self.loading_display:  # Check if attribute exists
            destroy(self.loading_display)  # Properly destroy the entity
            self.loading_display = None
    
    def update(self):
        try:
            self.frame_count += 1
            current_time = time.time()
            
            if current_time - self.last_time >= self.update_interval:
                fps = self.frame_count / (current_time - self.last_time)
                
                if hasattr(self, 'fps_display') and self.fps_display:
                    self.fps_display.text = f'FPS: {fps:.1f}'
                
                if self.world_gen and hasattr(self, 'stats_display') and self.stats_display:
                    stats = self.world_gen.get_stats()
                    if isinstance(stats, dict):  # Verify stats is a dictionary
                        self.stats_display.text = (
                            f"Chunks: {stats.get('loaded_chunks', 0)} | "
                            f"Blocks: {stats.get('total_blocks', 0)} | "
                            f"Seed: {stats.get('seed', 0)}"
                        )
                
                self.frame_count = 0
                self.last_time = current_time
        except Exception as e:
            print(f"Error in performance monitor update: {e}")
    
    def toggle_visibility(self):
        try:
            if hasattr(self, 'fps_display') and self.fps_display:
                visible = not self.fps_display.visible
                self.fps_display.visible = visible
                if hasattr(self, 'stats_display') and self.stats_display:
                    self.stats_display.visible = visible
        except Exception as e:
            print(f"Error toggling visibility: {e}")

# Global variables
perf_monitor = None  # Initialize as None
world_generator = None
game_initialized = False

# The relevant parts that need to be fixed:

def initialize_game():
    """Initializes the game with improved error handling"""
    global world_generator, game_initialized, perf_monitor, player
    
    try:
        print("=== HyMine - Optimized Version ===")
        start_time = time.time()
        
        # Initialize performance monitor
        perf_monitor = SimplePerformanceMonitor()
        
        # Block Registration with error handling
        perf_monitor.set_loading_text("Loading blocks...")
        register_blocks()
        
        # Inventory Setup
        perf_monitor.set_loading_text("Setting up inventory...")
        setup_inventory()
        
        # Create player BEFORE world setup
        player = FirstPersonController()
        player.cursor.visible = True
        player.speed = 6
        player.mouse_sensitivity = Vec2(40, 40)
        player.jump_height = 2
        player.jump_duration = 0.4
        
        # World Generation
        perf_monitor.set_loading_text("Initializing world generator...")
        setup_world()
        
        # Environment Setup
        setup_environment()
        
        perf_monitor.hide_loading()
        
        total_time = time.time() - start_time
        print(f"Initialization completed in {total_time:.2f}s")
        
        print_controls()
        
        game_initialized = True
        
    except Exception as e:
        print(f"Critical error during initialization: {e}")
        raise

def setup_world():
    """Helper function to setup world generation"""
    global world_generator
    
    try:
        WORLD_SEED = random.randint(0, 999999)  # Random seed for variety
        RENDER_DISTANCE = 2
        CHUNK_SIZE = 8
        
        world_generator = create_world_generator(
            seed=WORLD_SEED,
            chunk_size=CHUNK_SIZE,
            render_distance=RENDER_DISTANCE
        )
        
        if perf_monitor:
            perf_monitor.set_world_generator(world_generator)
        
        # Generate spawn area
        spawn_x, spawn_z = 0, 0
        spawn_height = world_generator.get_height_at(spawn_x, spawn_z)
        world_generator.generate_spawn_area(spawn_x, spawn_z, radius=1)
        
        # Move player to spawn position if it exists
        if 'player' in globals():
            player.position = (spawn_x, spawn_height + 2, spawn_z)
            
    except Exception as e:
        print(f"Error in world setup: {e}")
        raise

def register_blocks():
    """Helper function to register blocks with error handling"""
    try:
        block_definitions = [
            ('grass', 'assets/textures/blocks/grass'),
            ('stone', 'assets/textures/blocks/stone'),
            ('dirt', 'assets/textures/blocks/dirt'),
            ('wood', 'assets/textures/blocks/wood'),
            ('sand', 'assets/textures/blocks/sand'),
            ('cobblestone', 'assets/textures/blocks/cobblestone'),
            ('water', 'assets/textures/blocks/water', True),
            ('glass', 'white_cube', True, color.clear),
            ('leaves', 'assets/textures/blocks/leaves', True)
        ]
        
        for block_def in block_definitions:
            try:
                if len(block_def) == 2:
                    BlockRegistry.register(block_def[0], block_def[1])
                elif len(block_def) == 3:
                    BlockRegistry.register(block_def[0], block_def[1], walkthrough=block_def[2])
                elif len(block_def) == 4:
                    BlockRegistry.register(block_def[0], block_def[1], walkthrough=block_def[2], color=block_def[3])
            except Exception as block_error:
                print(f"Failed to register block {block_def[0]}, using fallback: {block_error}")
                # Fallback registration with basic cube
                BlockRegistry.register(block_def[0], 'white_cube', color=color.rgb(128, 128, 128))
    except Exception as e:
        print(f"Error in block registration: {e}")
        raise

def setup_inventory():
    """Helper function to setup inventory"""
    try:
        inventory = create_inventory()
        available_blocks = ['grass', 'stone', 'dirt', 'wood', 'sand', 'cobblestone', 'glass', 'leaves']
        for block_type in available_blocks:
            try:
                add_new_block_type(block_type)
            except Exception as block_error:
                print(f"Failed to add block type to inventory: {block_type}: {block_error}")
    except Exception as e:
        print(f"Error in inventory setup: {e}")
        raise

def setup_world():
    """Helper function to setup world generation"""
    global world_generator, player
    
    try:
        WORLD_SEED = random.randint(0, 999999)  # Random seed for variety
        RENDER_DISTANCE = 2
        CHUNK_SIZE = 8
        
        world_generator = create_world_generator(
            seed=WORLD_SEED,
            chunk_size=CHUNK_SIZE,
            render_distance=RENDER_DISTANCE
        )
        
        if perf_monitor:
            perf_monitor.set_world_generator(world_generator)
        
        # Generate spawn area
        spawn_x, spawn_z = 0, 0
        spawn_height = world_generator.get_height_at(spawn_x, spawn_z)
        world_generator.generate_spawn_area(spawn_x, spawn_z, radius=1)
        
        if player:
            player.position = (spawn_x, spawn_height + 2, spawn_z)
            
    except Exception as e:
        print(f"Error in world setup: {e}")
        raise

def setup_environment():
    """Helper function to setup environment"""
    try:
        # Skybox setup with fallback
        try:
            sky = Skybox(texture='assets/skyboxes/day')
        except Exception as sky_error:
            print(f"Skybox error: {sky_error}, using default sky")
            sky = Sky()
        
        # Lighting setup with fixed shadow map resolution
        sun = DirectionalLight()
        sun.look_at(Vec3(1, -1, -1))
        sun.color = color.white
        # Fix: Pass single integer for shadow map resolution instead of trying to access it as array
        sun.shadow_map_resolution = (1024, 1024)  # Or use sun.set_shadow_map_resolution(1024)
        
        AmbientLight(color=color.rgba(100, 100, 100, 0.1))
        
    except Exception as e:
        print(f"Error in environment setup: {e}")
        raise

def print_controls():
    """Helper function to print controls"""
    print("\n=== Controls ===")
    print("F1 - Toggle performance display")
    print("F3 - Show world statistics")
    print("F4 - Generate new world")
    print("ESC - Toggle mouse lock")

# Update system
last_chunk_update = time.time()
chunk_update_interval = 0.3
last_player_chunk = None

def input(key):
    """Input handler with improved error handling"""
    global world_generator, last_player_chunk
    
    if not game_initialized:
        return
    
    try:
        # Handle inventory input
        if handle_inventory_input(key):
            return
        
        if key == 'escape':
            mouse.locked = not mouse.locked
        elif key == 'f1' and perf_monitor:
            perf_monitor.toggle_visibility()
        elif key == 'f3':
            show_world_stats()
        elif key == 'f4':
            generate_new_world()
            
    except Exception as e:
        print(f"Error handling input {key}: {e}")

def show_world_stats():
    """Helper function to show world statistics"""
    if world_generator:
        try:
            stats = world_generator.get_stats()
            print("\n=== World Statistics ===")
            print(f"Seed: {stats.get('seed', 'Unknown')}")
            print(f"Loaded Chunks: {stats.get('loaded_chunks', 0)}")
            print(f"Total Blocks: {stats.get('total_blocks', 0)}")
            print(f"Render Distance: {stats.get('render_distance', 0)}")
            print("========================\n")
        except Exception as e:
            print(f"Error showing world stats: {e}")

def generate_new_world():
    """Helper function to generate new world"""
    global world_generator, last_player_chunk
    
    try:
        if world_generator:
            print("Generating new world...")
            new_seed = random.randint(0, 999999)
            
            world_generator = create_world_generator(
                seed=new_seed,
                chunk_size=8,
                render_distance=2
            )
            
            if perf_monitor:
                perf_monitor.set_world_generator(world_generator)
            
            # New spawn location
            spawn_height = world_generator.get_height_at(0, 0)
            world_generator.generate_spawn_area(0, 0, radius=1)
            if player:
                player.position = (0, spawn_height + 2, 0)
            last_player_chunk = None
            
            print(f"Generated new world with seed {new_seed}")
    except Exception as e:
        print(f"Error generating new world: {e}")

def update():
    """Main update loop with improved error handling"""
    global last_chunk_update, last_player_chunk
    
    if not game_initialized:
        return
    
    try:
        # Update performance monitor
        if perf_monitor:
            perf_monitor.update()
        
        # Limit camera rotation
        if player and hasattr(player, 'camera_pivot'):
            player.camera_pivot.rotation_x = max(-90, min(90, player.camera_pivot.rotation_x))
        
        # Update chunks
        current_time = time.time()
        if current_time - last_chunk_update > chunk_update_interval:
            update_chunks()
            last_chunk_update = current_time
        
        # Anti-fall system
        check_player_fall()
        
    except Exception as e:
        print(f"Error in update loop: {e}")

def update_chunks():
    """Helper function to update chunks"""
    global last_player_chunk
    
    if world_generator and player:
        try:
            current_player_chunk = world_generator.get_chunk_coords(player.x, player.z)
            
            if current_player_chunk != last_player_chunk:
                loaded, unloaded = update_world_around_player(world_generator, player)
                last_player_chunk = current_player_chunk
                
                if loaded > 0 or unloaded > 0:
                    print(f"Chunks updated: +{loaded} -{unloaded}")
                    
        except Exception as e:
            print(f"Error updating chunks: {e}")

def check_player_fall():
    """Helper function to prevent player falling through the world"""
    if world_generator and player and player.y < -10:
        try:
            ground_height = world_generator.get_height_at(player.x, player.z)
            player.position = (player.x, ground_height + 2, player.z)
            print("Player rescued from void")
        except Exception as e:
            print(f"Error rescuing player: {e}, using fallback position")
            player.position = (0, 110, 0)

if __name__ == "__main__":
    try:
        initialize_game()
        print("Starting game...")
        app.run()
    except KeyboardInterrupt:
        print("\nGame terminated by user")
    except Exception as e:
        print(f"Critical error: {e}")
        import traceback
        traceback.print_exc()
