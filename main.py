from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController

from block import BlockRegistry
from skybox import Skybox
from world import World
from inventory import create_inventory, handle_inventory_input, get_current_block, add_new_block_type

app = Ursina()

window.fps_counter.enabled = True
window.exit_button.visible = False
mouse.locked = True

player = FirstPersonController()
player.cursor.visible = True

# === Blöcke registrieren ===
BlockRegistry.register('grass', 'assets/textures/blocks/grass')
BlockRegistry.register('stone', 'assets/textures/blocks/stone')
BlockRegistry.register('dirt', 'assets/textures/blocks/dirt')
BlockRegistry.register('wood', 'assets/textures/blocks/wood')
BlockRegistry.register('sand', 'assets/textures/blocks/sand')
BlockRegistry.register('water', 'assets/textures/blocks/water')
BlockRegistry.register('leaves', 'assets/textures/blocks/leaves')
BlockRegistry.register('cobblestone', 'assets/textures/blocks/cobblestone')

# === Inventar erstellen ===
inventory = create_inventory()

# Beispiel: Neuen Block-Typ hinzufügen (optional)
# add_new_block_type('custom_block')

# === Welt generieren ===
world = World()
world.generate_area(radius=2)

# === Beispielblöcke ===
BlockRegistry.create('stone', position=(5, 1, 5))
BlockRegistry.create('dirt', position=(6, 1, 5))

# === Skybox erstellen ===
sky = Skybox(texture='assets/skyboxes/day')


def input(key):
    if handle_inventory_input(key):
        return
    
    if key == 'escape':
        mouse.locked = not mouse.locked


app.run()
