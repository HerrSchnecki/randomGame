from ursina import *

class ItemStack:
    """Repräsentiert einen Stapel von Items"""
    def __init__(self, item_type=None, quantity=1):
        self.item_type = item_type
        self.quantity = quantity
    
    def is_empty(self):
        return self.item_type is None or self.quantity <= 0
    
    def clear(self):
        self.item_type = None
        self.quantity = 0


class InventorySlot(Button):
    """Ein einzelner Inventar-Slot"""
    def __init__(self, position, slot_id, inventory_manager, is_hotbar=False):
        self.slot_id = slot_id
        self.inventory_manager = inventory_manager
        self.is_hotbar = is_hotbar
        self.item_stack = ItemStack()
        self.is_being_dragged = False
        
        super().__init__(
            parent=camera.ui,
            position=position,
            scale=(0.06, 0.06),
            color=color.dark_gray,
            highlight_color=color.gray,
            text='',
            text_size=0.8
        )
        
        if is_hotbar:
            self.color = color.rgb(40, 40, 40)
            self.highlight_color = color.rgb(60, 60, 60)
        
        self.quantity_label = Text(
            '',
            parent=self,
            position=(0.35, -0.35, 0),
            scale=0.5,
            color=color.white,
            origin=(0, 0)
        )
        
        self.selection_frame = Entity(
            parent=self,
            model='cube',
            scale=1.1,
            color=color.white,
            alpha=0.5,
            visible=False
        )
    
    def set_item(self, item_type, quantity=1):
        """Setzt ein Item in den Slot"""
        self.item_stack.item_type = item_type
        self.item_stack.quantity = quantity
        self.update_display()
    
    def clear_item(self):
        """Leert den Slot"""
        self.item_stack.clear()
        self.update_display()
    
    def update_display(self):
        """Aktualisiert die visuelle Darstellung des Slots"""
        if self.item_stack.is_empty():
            self.text = ''
            self.color = color.dark_gray if not self.is_hotbar else color.rgb(40, 40, 40)
            self.quantity_label.text = ''
        else:
            item_colors = {
                'grass': color.green,
                'stone': color.gray,
                'dirt': color.brown,
                'wood': color.orange,
                'sand': color.yellow,
                'water': color.blue,
                'leaves': color.dark_green,
                'cobblestone': color.dark_gray
            }
            
            self.text = self.item_stack.item_type[0].upper()
            self.color = item_colors.get(self.item_stack.item_type, color.white)
            
            if self.item_stack.quantity > 1:
                self.quantity_label.text = str(self.item_stack.quantity)
            else:
                self.quantity_label.text = ''
    
    def set_selected(self, selected):
        """Markiert den Slot als ausgewählt (nur für Hotbar)"""
        if self.is_hotbar:
            self.selection_frame.visible = selected
    
    def on_click(self):
        """Behandelt Klicks auf den Slot"""
        self.inventory_manager.on_slot_click(self)


class CreativeInventory(Entity):
    """Creative-Inventar mit allen verfügbaren Blöcken"""
    def __init__(self, inventory_manager):
        super().__init__(parent=camera.ui)
        self.inventory_manager = inventory_manager
        self.visible = False
        
        self.background = Entity(
            parent=self,
            model='cube',
            color=color.black,
            alpha=0.8,
            scale=(0.8, 0.6, 1),
            position=(0, 0, 0)
        )
        
        self.title = Text(
            'Creative Inventar (E zum Schließen)',
            parent=self,
            position=(0, 0.25, 0),
            scale=0.7,
            color=color.white,
            origin=(0, 0)
        )
        
        self.available_items = [
            'grass', 'stone', 'dirt', 'wood', 'sand', 
            'water', 'leaves', 'cobblestone'
        ]
        
        self.creative_slots = []
        slots_per_row = 8
        start_x = -0.25
        start_y = 0.1
        slot_spacing = 0.07
        
        for i, item_type in enumerate(self.available_items):
            row = i // slots_per_row
            col = i % slots_per_row
            
            x = start_x + col * slot_spacing
            y = start_y - row * slot_spacing
            
            slot = InventorySlot((x, y), f"creative_{i}", inventory_manager, False)
            slot.parent = self
            slot.set_item(item_type, 64)
            self.creative_slots.append(slot)
    
    def toggle_visibility(self):
        """Ein-/Ausblenden des Creative-Inventars"""
        self.visible = not self.visible
        
        if self.visible:
            mouse.locked = False
        else:
            mouse.locked = True


class InventoryManager:
    """Verwaltet das komplette Inventarsystem"""
    def __init__(self):
        self.hotbar_slots = []
        self.current_hotbar_slot = 0
        self.dragged_item = None
        self.creative_inventory = None
        
        self.setup_ui() 
        self.setup_hotbar()
        self.setup_creative_inventory()
        self.update_current_block_display()
    
    def setup_hotbar(self):
        """Erstellt die Hotbar (Schnellzugriff-Leiste)"""
        hotbar_size = 9
        start_x = -0.32
        slot_spacing = 0.08
        
        for i in range(hotbar_size):
            x = start_x + i * slot_spacing
            slot = InventorySlot((x, -0.45), i, self, is_hotbar=True)
            self.hotbar_slots.append(slot)
        
        if len(self.hotbar_slots) > 0:
            self.select_hotbar_slot(0)
        
        self.hotbar_bg = Entity(
            parent=camera.ui,
            model='cube',
            color=color.black,
            alpha=0.5,
            scale=(0.75, 0.1, 1),
            position=(0, -0.45, 0)
        )
    
    def setup_creative_inventory(self):
        """Erstellt das Creative-Inventar"""
        self.creative_inventory = CreativeInventory(self)
    
    def setup_ui(self):
        """Erstellt UI-Elemente"""
        self.current_block_text = Text(
            'Aktueller Block: Leer',
            parent=camera.ui,
            position=(0, 0.4, 0),
            scale=0.8,
            color=color.yellow,
            origin=(0, 0)
        )
        
        self.instructions = Text(
            'Steuerung: 1-9 Hotbar | E Creative-Inventar | Rechtsklick Platzieren | Linksklick Abbauen',
            parent=camera.ui,
            position=(0, 0.45, 0),
            scale=0.5,
            color=color.light_gray,
            origin=(0, 0)
        )
    
    def add_new_item_type(self, item_type):
        """Fügt einen neuen Item-Typ zum Creative-Inventar hinzu"""
        if item_type not in self.creative_inventory.available_items:
            self.creative_inventory.available_items.append(item_type)
            self.creative_inventory.destroy()
            self.setup_creative_inventory()
            print(f"Neuer Block hinzugefügt: {item_type}")
    
    def select_hotbar_slot(self, slot_index):
        """Wählt einen Hotbar-Slot aus"""
        if 0 <= slot_index < len(self.hotbar_slots):
            self.hotbar_slots[self.current_hotbar_slot].set_selected(False)
            
            self.current_hotbar_slot = slot_index
            self.hotbar_slots[self.current_hotbar_slot].set_selected(True)
            
            self.update_current_block_display()
    
    def update_current_block_display(self):
        """Aktualisiert die Anzeige des aktuellen Blocks"""
        if not hasattr(self, 'current_block_text') or len(self.hotbar_slots) == 0:
            return
            
        current_slot = self.hotbar_slots[self.current_hotbar_slot]
        if current_slot.item_stack.is_empty():
            self.current_block_text.text = 'Aktueller Block: Leer'
        else:
            self.current_block_text.text = f'Aktueller Block: {current_slot.item_stack.item_type.title()}'
    
    def get_current_block(self):
        """Gibt den aktuell ausgewählten Block zurück"""
        current_slot = self.hotbar_slots[self.current_hotbar_slot]
        if not current_slot.item_stack.is_empty():
            return current_slot.item_stack.item_type
        return None
    
    def on_slot_click(self, clicked_slot):
        """Behandelt Klicks auf Inventar-Slots"""
        if self.creative_inventory.visible and clicked_slot in self.creative_inventory.creative_slots:
            if not clicked_slot.item_stack.is_empty():
                self.add_to_hotbar(clicked_slot.item_stack.item_type)
        elif clicked_slot in self.hotbar_slots:
            slot_index = self.hotbar_slots.index(clicked_slot)
            self.select_hotbar_slot(slot_index)
    
    def add_to_hotbar(self, item_type):
        """Fügt ein Item zur Hotbar hinzu"""
        for slot in self.hotbar_slots:
            if not slot.item_stack.is_empty() and slot.item_stack.item_type == item_type:
                if slot.item_stack.quantity < 64:
                    slot.item_stack.quantity = min(64, slot.item_stack.quantity + 1)
                    slot.update_display()
                    return
        
        for slot in self.hotbar_slots:
            if slot.item_stack.is_empty():
                slot.set_item(item_type, 1)
                self.update_current_block_display()
                return
        
        current_slot = self.hotbar_slots[self.current_hotbar_slot]
        current_slot.set_item(item_type, 1)
        self.update_current_block_display()
    
    def handle_input(self, key):
        """Behandelt Eingaben für das Inventarsystem"""
        if key in '123456789':
            slot_index = int(key) - 1
            if slot_index < len(self.hotbar_slots):
                self.select_hotbar_slot(slot_index)
                return True
        
        if key == 'e':
            self.creative_inventory.toggle_visibility()
            return True
        
        return False


inventory_manager = None

def create_inventory():
    """Erstellt das Inventarsystem"""
    global inventory_manager
    inventory_manager = InventoryManager()
    
    inventory_manager.add_to_hotbar('grass')
    inventory_manager.add_to_hotbar('stone')
    inventory_manager.add_to_hotbar('dirt')
    
    return inventory_manager

def get_current_block():
    """Gibt den aktuell ausgewählten Block zurück"""
    global inventory_manager
    if inventory_manager:
        return inventory_manager.get_current_block()
    return None

def handle_inventory_input(key):
    """Behandelt Eingaben für das Inventar"""
    global inventory_manager
    if not inventory_manager:
        return False
    
    return inventory_manager.handle_input(key)

def add_new_block_type(block_type):
    """Fügt einen neuen Block-Typ hinzu (für einfache Erweiterung)"""
    global inventory_manager
    if inventory_manager:
        inventory_manager.add_new_item_type(block_type)
