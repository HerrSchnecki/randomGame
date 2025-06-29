from ursina import *

class BlockRegistry:
    registry = {}

    @classmethod
    def register(cls, name, texture):
        cls.registry[name] = texture

    @classmethod
    def create(cls, name, position=(0, 0, 0)):
        if name not in cls.registry:
            print(f"[BlockRegistry] Block '{name}' nicht registriert!")
            return None
        return Block(position=position, texture=cls.registry[name])


class Block(Button):
    def __init__(self, position=(0, 0, 0), texture='white_cube'):
        super().__init__(
            parent=scene,
            position=position,
            model='cube',
            origin_y=0.5,
            texture=texture,
            color=color.color(0, 0, random.uniform(0.9, 1)),
            scale=1
        )

    def input(self, key):
        if self.hovered:
            if key == 'right mouse down':
                BlockRegistry.create(current_block, position=self.position + mouse.normal)
            if key == 'left mouse down':
                destroy(self)


current_block = 'grass'
