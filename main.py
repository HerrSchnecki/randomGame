from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController

from block import BlockRegistry, current_block
from skybox import Skybox
from world import World


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

# === Welt generieren ===
world = World()
world.generate_area(radius=2)

# === Beispielblöcke ===
BlockRegistry.create('stone', position=(5, 1, 5))
BlockRegistry.create('dirt', position=(6, 1, 5))

# === Skybox erstellen ===
sky = Skybox(texture='assets/skyboxes/day')




def input(key):
    global current_block
    if key == '1':
        current_block = 'grass'
        print('Block: Grass')
    if key == '2':
        current_block = 'stone'
        print('Block: Stone')
    if key == '3':
        current_block = 'dirt'
        print('Block: Dirt')

    if key == 'escape':
        mouse.locked = not mouse.locked


app.run()
