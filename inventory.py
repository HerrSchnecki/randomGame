from ursina import *
from ursina import color as ursina_color

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
            color=ursina_color.rgb(60, 60, 60),
            highlight_color=ursina_color.rgb(80, 80, 80),
            text='',
            text_size=0.8,
            model='cube'
        )
        
        if is_hotbar:
            self.color = ursina_color.rgb(45, 45, 45)
            self.highlight_color = ursina_color.rgb(70, 70, 70)
        
        # 3D Block-Icon in der Mitte des Slots
        self.block_icon = Entity(
            parent=self,
            model='cube',
            scale=0.6,
            position=(0, 0, -0.1),
            color=ursina_color.white,
            visible=False
        )
        
        self.quantity_label = Text(
            '',
            parent=self,
            position=(0.35, -0.35, -0.1),
            scale=0.5,
            color=ursina_color.white,
            origin=(0, 0)
        )
        
        self.selection_frame = Entity(
            parent=self,
            model='cube',
            scale=1.15,
            color=ursina_color.yellow,
            alpha=0.3,
            visible=False,
            position=(0, 0, 0.05)
        )
        
        # Slot-Rahmen für bessere Optik
        self.slot_border = Entity(
            parent=self,
            model='cube',
            scale=1.05,
            color=ursina_color.rgb(30, 30, 30),
            alpha=0.8,
            position=(0, 0, 0.02)
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
            self.block_icon.visible = False
            self.quantity_label.text = ''
        else:
            # Block-Icon anzeigen
            self.block_icon.visible = True
            
            # Textur und Model vom BlockRegistry holen
            try:
                from block import BlockRegistry
                texture_path = BlockRegistry.get_texture(self.item_stack.item_type)
                model_path = BlockRegistry.get_model(self.item_stack.item_type)
                
                if texture_path:
                    self.block_icon.texture = texture_path
                else:
                    self.block_icon.texture = 'white_cube'
                
                # Model für Block-Icon setzen (für bessere Darstellung)
                if model_path and model_path != 'cube':
                    # Für spezielle Models das passende Icon-Model verwenden
                    if model_path == 'sphere':
                        self.block_icon.model = 'sphere'
                    elif model_path == 'cylinder':
                        self.block_icon.model = 'cylinder'
                    else:
                        self.block_icon.model = 'cube'  # Standard für Custom Models
                else:
                    self.block_icon.model = 'cube'
                    
            except (ImportError, AttributeError):
                self.block_icon.texture = 'white_cube'
                self.block_icon.model = 'cube'
            
            # Leichte Rotation für 3D-Effekt
            self.block_icon.rotation = (15, 45, 0)
            
            # Anzahl anzeigen
            if self.item_stack.quantity > 1:
                self.quantity_label.text = str(self.item_stack.quantity)
            else:
                self.quantity_label.text = ''
    
    def set_selected(self, selected):
        """Markiert den Slot als ausgewählt (nur für Hotbar)"""
        if self.is_hotbar:
            self.selection_frame.visible = selected
            if selected:
                # Leichte Animation für ausgewählten Slot
                self.selection_frame.animate_scale(1.2, duration=0.1)
            else:
                self.selection_frame.scale = 1.15
    
    def on_click(self):
        """Behandelt Klicks auf den Slot"""
        if self.inventory_manager:
            self.inventory_manager.on_slot_click(self)


class CreativeInventory(Entity):
    """Creative-Inventar mit allen verfügbaren Blöcken"""
    def __init__(self, inventory_manager):
        super().__init__(parent=camera.ui)
        self.inventory_manager = inventory_manager
        self.visible = False
        
        # Hintergrund mit Glasmorphismus-Effekt
        self.background = Entity(
            parent=self,
            model='cube',
            color=ursina_color.rgb(20, 20, 30),
            alpha=0.9,
            scale=(0.9, 0.7, 1),
            position=(0, 0, 0)
        )
        
        # Titel mit besserem Styling
        self.title = Text(
            'Creative Inventar',
            parent=self,
            position=(0, 0.28, -0.1),
            scale=0.9,
            color=ursina_color.white,
            origin=(0, 0)
        )
        
        self.subtitle = Text(
            'Drücke E zum Schließen | Klicke Blöcke um sie zur Hotbar hinzuzufügen',
            parent=self,
            position=(0, 0.24, -0.1),
            scale=0.5,
            color=ursina_color.light_gray,
            origin=(0, 0)
        )
        
        # Alle verfügbaren Blöcke aus der BlockRegistry laden
        self.load_available_items()
        
        self.creative_slots = []
        self.create_slots()
    
    def load_available_items(self):
        """Lädt alle verfügbaren Items aus der BlockRegistry"""
        try:
            from block import BlockRegistry
            self.available_items = BlockRegistry.list_blocks()
            # Falls keine Blöcke registriert sind, Fallback verwenden
            if not self.available_items:
                self.available_items = ['grass', 'stone', 'dirt', 'wood']
        except ImportError:
            # Fallback falls BlockRegistry nicht verfügbar
            self.available_items = [
                'grass', 'stone', 'dirt', 'wood', 'sand', 
                'water', 'leaves', 'cobblestone'
            ]
    
    def create_slots(self):
        """Erstellt die Creative-Inventory-Slots"""
        # Alte Slots löschen falls vorhanden
        for slot in self.creative_slots:
            destroy(slot)
        self.creative_slots = []
        
        slots_per_row = 8
        start_x = -0.28
        start_y = 0.15
        slot_spacing = 0.075
        
        for i, item_type in enumerate(self.available_items):
            row = i // slots_per_row
            col = i % slots_per_row
            
            x = start_x + col * slot_spacing
            y = start_y - row * slot_spacing
            
            slot = InventorySlot((x, y), f"creative_{i}", self.inventory_manager, False)
            slot.parent = self
            slot.set_item(item_type, 64)
            
            # Hover-Effekt für Creative-Slots
            original_color = slot.color
            def make_hover_effect(s, orig_color):
                s.on_hover = lambda: setattr(s, 'color', ursina_color.rgb(90, 90, 90))
                s.on_mouse_exit = lambda: setattr(s, 'color', orig_color)
            
            make_hover_effect(slot, original_color)
            
            self.creative_slots.append(slot)
    
    def refresh_items(self):
        """Aktualisiert die verfügbaren Items (nützlich wenn neue Blöcke hinzugefügt werden)"""
        self.load_available_items()
        self.create_slots()
    
    def toggle_visibility(self):
        """Ein-/Ausblenden des Creative-Inventars"""
        self.visible = not self.visible
        
        if self.visible:
            mouse.locked = False
            # Items beim Öffnen aktualisieren
            self.refresh_items()
        else:
            mouse.locked = True


class InventoryManager:
    """Verwaltet das komplette Inventarsystem"""
    def __init__(self):
        self.hotbar_slots = []
        self.current_hotbar_slot = 0
        self.dragged_item = None
        self.creative_inventory = None
        self.current_block_text = None
        self.instructions = None
        self.hotbar_bg = None
        
        self.setup_ui() 
        self.setup_hotbar()
        self.setup_creative_inventory()
        self.update_current_block_display()
    
    def setup_hotbar(self):
        """Erstellt die Hotbar (Schnellzugriff-Leiste)"""
        hotbar_size = 9
        start_x = -0.32
        slot_spacing = 0.08
        
        # Hotbar Hintergrund mit modernem Design
        self.hotbar_bg = Entity(
            parent=camera.ui,
            model='cube',
            color=ursina_color.rgb(25, 25, 25),
            alpha=0.8,
            scale=(0.78, 0.12, 1),
            position=(0, -0.45, 0.01)
        )
        
        # Hotbar Rahmen
        self.hotbar_frame = Entity(
            parent=camera.ui,
            model='cube',
            color=ursina_color.rgb(60, 60, 60),
            alpha=0.6,
            scale=(0.8, 0.14, 1),
            position=(0, -0.45, 0.02)
        )
        
        for i in range(hotbar_size):
            x = start_x + i * slot_spacing
            slot = InventorySlot((x, -0.45), i, self, is_hotbar=True)
            self.hotbar_slots.append(slot)
        
        if len(self.hotbar_slots) > 0:
            self.select_hotbar_slot(0)
    
    def setup_creative_inventory(self):
        """Erstellt das Creative-Inventar"""
        self.creative_inventory = CreativeInventory(self)
    
    def setup_ui(self):
        """Erstellt UI-Elemente"""
        self.current_block_text = Text(
            'Aktueller Block: Leer',
            parent=camera.ui,
            position=(0, 0.4, 0),
            scale=0.9,
            color=ursina_color.yellow,
            origin=(0, 0)
        )
        
        self.instructions = Text(
            'Steuerung: 1-9 Hotbar | E Creative-Inventar | Rechtsklick Platzieren | Linksklick Abbauen',
            parent=camera.ui,
            position=(0, 0.45, 0),
            scale=0.5,
            color=ursina_color.rgb(200, 200, 200),
            origin=(0, 0)
        )
        
        # Hotbar-Nummern anzeigen
        self.hotbar_numbers = []
        for i in range(9):
            number_text = Text(
                str(i + 1),
                parent=camera.ui,
                position=(-0.32 + i * 0.08, -0.38, -0.1),
                scale=0.4,
                color=ursina_color.white,
                origin=(0, 0)
            )
            self.hotbar_numbers.append(number_text)
    
    def add_new_item_type(self, item_type):
        """Fügt einen neuen Item-Typ zum Creative-Inventar hinzu"""
        if self.creative_inventory:
            # Creative-Inventar aktualisieren
            self.creative_inventory.refresh_items()
            print(f"Inventar aktualisiert - Block verfügbar: {item_type}")
    
    def select_hotbar_slot(self, slot_index):
        """Wählt einen Hotbar-Slot aus"""
        if 0 <= slot_index < len(self.hotbar_slots):
            # Alten Slot deselektieren
            if self.current_hotbar_slot < len(self.hotbar_slots):
                self.hotbar_slots[self.current_hotbar_slot].set_selected(False)
            
            self.current_hotbar_slot = slot_index
            self.hotbar_slots[self.current_hotbar_slot].set_selected(True)
            
            self.update_current_block_display()
    
    def update_current_block_display(self):
        """Aktualisiert die Anzeige des aktuellen Blocks"""
        if not self.current_block_text or len(self.hotbar_slots) == 0:
            return
            
        current_slot = self.hotbar_slots[self.current_hotbar_slot]
        if current_slot.item_stack.is_empty():
            self.current_block_text.text = 'Aktueller Block: Leer'
        else:
            block_name = current_slot.item_stack.item_type.replace('_', ' ').title()
            # Zusätzliche Info über Block-Eigenschaften anzeigen
            try:
                from block import BlockRegistry
                if BlockRegistry.is_walkthrough(current_slot.item_stack.item_type):
                    block_name += " (Walkthrough)"
            except (ImportError, AttributeError):
                pass
            
            self.current_block_text.text = f'Aktueller Block: {block_name}'
    
    def get_current_block(self):
        """Gibt den aktuell ausgewählten Block zurück"""
        if len(self.hotbar_slots) == 0:
            return None
            
        current_slot = self.hotbar_slots[self.current_hotbar_slot]
        if not current_slot.item_stack.is_empty():
            return current_slot.item_stack.item_type
        return None
    
    def on_slot_click(self, clicked_slot):
        """Behandelt Klicks auf Inventar-Slots"""
        if self.creative_inventory and self.creative_inventory.visible and clicked_slot in self.creative_inventory.creative_slots:
            if not clicked_slot.item_stack.is_empty():
                self.add_to_hotbar(clicked_slot.item_stack.item_type)
        elif clicked_slot in self.hotbar_slots:
            slot_index = self.hotbar_slots.index(clicked_slot)
            self.select_hotbar_slot(slot_index)
    
    def add_to_hotbar(self, item_type):
        """Fügt ein Item zur Hotbar hinzu"""
        # Erst versuchen vorhandene Stacks zu erhöhen
        for slot in self.hotbar_slots:
            if not slot.item_stack.is_empty() and slot.item_stack.item_type == item_type:
                if slot.item_stack.quantity < 64:
                    slot.item_stack.quantity = min(64, slot.item_stack.quantity + 1)
                    slot.update_display()
                    return
        
        # Dann leeren Slot suchen
        for slot in self.hotbar_slots:
            if slot.item_stack.is_empty():
                slot.set_item(item_type, 1)
                self.update_current_block_display()
                return
        
        # Falls kein leerer Slot, aktuellen Slot überschreiben
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
            if self.creative_inventory:
                self.creative_inventory.toggle_visibility()
            return True
        
        return False


# Globale Variable für das Inventarsystem
inventory_manager = None

def create_inventory():
    """Erstellt das Inventarsystem"""
    global inventory_manager
    inventory_manager = InventoryManager()
    
    # Startitems zur Hotbar hinzufügen
    inventory_manager.add_to_hotbar('grass')
    inventory_manager.add_to_hotbar('stone')
    inventory_manager.add_to_hotbar('wood')
    
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
