from ursina import *

class Skybox(Entity):
    def __init__(self, texture='default_sky'):
        super().__init__(
            parent=scene,
            model='sphere',
            texture=texture,
            scale=500,
            double_sided=True
        )
        # Alternative Rotationen falls nötig:
        # self.rotation_x = 90    # Falls Himmel unten ist
        # self.rotation_y = 180   # Falls Textur gespiegelt ist
        # self.rotation_z = 180   # Falls auf dem Kopf steht
