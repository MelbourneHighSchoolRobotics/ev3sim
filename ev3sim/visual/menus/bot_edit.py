import os
import shutil
import pygame
import pygame_gui
import pymunk
import yaml
import numpy as np
from ev3sim.file_helper import find_abs, find_abs_directory
from ev3sim.objects.base import DYNAMIC_CATEGORY
from ev3sim.robot import add_devices
from ev3sim.simulation.randomisation import Randomiser
from ev3sim.visual.menus.base_menu import BaseMenu
from ev3sim.visual.manager import ScreenObjectManager
from ev3sim.visual.utils import screenspace_to_worldspace
from ev3sim.search_locations import asset_locations


class BotEditMenu(BaseMenu):

    onSave = None

    MODE_NORMAL = "NORMAL"
    MODE_DEVICE_DIALOG = "DEVICE_SELECT"
    MODE_COLOUR_DIALOG = "COLOUR"
    MODE_BASEPLATE_DIALOG = "BASEPLATE"
    MODE_NAME_DIALOG = "NAME"
    MODE_PORT_DIALOG = "PORT"
    MODE_CODE_DIALOG = "CODE"

    SELECTED_CIRCLE = "CIRCLE"
    SELECTED_RECTANGLE = "RECTANGLE"
    SELECTED_POLYGON = "POLYGON"
    SELECTED_NOTHING = "NOTHING"
    SELECTED_DEVICE = "DEVICE"

    BASE_ZPOS = 1
    OBJ_ZPOS = 2
    DEV_ZPOS = 3
    HOLD_ZPOS = 4

    def clearEvents(self):
        self.onSave = None

    def initWithKwargs(self, **kwargs):
        # Try removing the baseplate dialog if it still exists.
        try:
            self.mode = self.MODE_NORMAL
            self.picker.kill()
        except:
            pass
        self.current_mpos = (0, 0)
        self.selected_index = None
        self.selected_type = self.SELECTED_NOTHING
        self.lock_grid = True
        self.grid_size = 1
        self.dragging = False
        self.bot_dir_file = kwargs.get("bot_dir_file", None)
        self.bot_file = kwargs.get("bot_file", None)
        self.current_holding = None
        if self.bot_dir_file is None or self.bot_file is None:
            if (self.bot_dir_file is not None) or (self.bot_dir_file is not None):
                raise ValueError(
                    f"bot_dir_file and bot_file are required here. Got {self.bot_dir_file} and {self.bot_file}."
                )
            self.creating = True
            self.mode = self.MODE_BASEPLATE_DIALOG
            self.previous_info = {}
            self.current_object = {}
            self.current_devices = []
        else:
            self.creating = False
            self.mode = self.MODE_NORMAL
            with open(os.path.join(self.bot_file, "config.bot"), "r") as f:
                bot = yaml.safe_load(f)
            self.previous_info = bot
            self.current_object = bot["base_plate"]
            self.current_object["type"] = "object"
            self.current_object["physics"] = True
            self.current_devices = bot["devices"]
        super().initWithKwargs(**kwargs)
        self.resetBotVisual()
        if self.mode == self.MODE_BASEPLATE_DIALOG:
            self.addBaseplatePicker()

    def getSelectedAttribute(self, attr, fallback=None, visual=True):
        if self.selected_index is None:
            raise ValueError("Nothing selected.")
        elif self.selected_index == "Holding":
            return self.current_holding_kwargs.get(attr, fallback)
        elif self.selected_index == "Baseplate":
            if visual:
                return self.current_object["visual"].get(attr, fallback)
            return self.current_object.get(attr, fallback)
        elif self.selected_index[0] == "Children":
            if visual:
                return self.current_object["children"][self.selected_index[1]]["visual"].get(attr, fallback)
            return self.current_object["children"][self.selected_index[1]].get(attr, fallback)
        elif self.selected_index[0] == "Devices":
            # Just one key in this dict.
            for key in self.current_devices[self.selected_index[1]]:
                return self.current_devices[self.selected_index[1]][key].get(attr, fallback)
        raise ValueError(f"Unknown selection {self.selected_index}")

    def setSelectedAttribute(self, attr, val, visual=True):
        if self.selected_index is None:
            raise ValueError("Nothing selected.")
        elif self.selected_index == "Holding":
            self.current_holding_kwargs[attr] = val
        elif self.selected_index == "Baseplate":
            if visual:
                self.current_object["visual"][attr] = val
            else:
                self.current_object[attr] = val
        elif self.selected_index[0] == "Children":
            if visual:
                self.current_object["children"][self.selected_index[1]]["visual"][attr] = val
            else:
                self.current_object["children"][self.selected_index[1]][attr] = val
        elif self.selected_index[0] == "Devices":
            # Just one key in this dict.
            for key in self.current_devices[self.selected_index[1]]:
                self.current_devices[self.selected_index[1]][key][attr] = val
        else:
            raise ValueError(f"Unknown selection {self.selected_index}")

    def resetBotVisual(self):
        from ev3sim.visual.manager import ScreenObjectManager
        from ev3sim.simulation.loader import ScriptLoader
        from ev3sim.simulation.world import World
        from ev3sim.visual.objects import visualFactory

        ScriptLoader.instance.reset()
        ScriptLoader.instance.startUp()
        ScreenObjectManager.instance.resetVisualElements()
        World.instance.resetWorld()
        mSize = min(*self.surf_size)
        self.customMap = {
            "SCREEN_WIDTH": self.surf_size[0],
            "SCREEN_HEIGHT": self.surf_size[1],
            "MAP_WIDTH": int(self.surf_size[0] / mSize * 24),
            "MAP_HEIGHT": int(self.surf_size[1] / mSize * 24),
        }
        bg_circ = visualFactory(
            name="Circle",
            radius=11,
            position=(0, 0),
            zPos=-1,
            fill="#404040",
            stroke_width=0,
        )
        bg_circ.customMap = self.customMap
        bg_circ.calculatePoints()
        ScreenObjectManager.instance.registerVisual(bg_circ, key="bg_circle")
        if self.current_object:
            copy_obj = self.current_object.copy()
            copy_obj["children"] = self.current_object["children"].copy()
            add_devices(copy_obj, self.current_devices)
            elems = ScriptLoader.instance.loadElements([copy_obj], preview_mode=True)
            self.robot = elems[0]
            self.robot.identifier = "Baseplate"
            for i, child in enumerate(self.robot.children):
                child.identifier = ("Children", i)
            # Just create it so we can use it.
            r = Randomiser(seed=0)
            for i, interactor in enumerate(ScriptLoader.instance.active_scripts):
                interactor.port_key = str(i)
                Randomiser.createPortRandomiserWithSeed(interactor.port_key)
                interactor.startUp()
                interactor.device_class.generateBias()
                interactor.tick(0)
                interactor.afterPhysics()
                for gen in interactor.generated:
                    gen.identifier = ("Devices", i)
            World.instance.registerObject(self.robot)
            while elems:
                new_elems = []
                for elem in elems:
                    elem.visual.customMap = self.customMap
                    elem.visual.calculatePoints()
                    new_elems.extend(elem.children)
                elems = new_elems
            # We need this for the device positions to be correctly set.
            World.instance.tick(1 / 60)

    def updateZpos(self):
        for i in range(len(self.current_devices)):
            for key in self.current_devices[i]:
                self.current_devices[i][key]["zPos"] = self.DEV_ZPOS + 1 - pow(2, -i)
        for i in range(len(self.current_object["children"])):
            self.current_object["children"][i]["visual"]["zPos"] = self.OBJ_ZPOS + 1 - pow(2, -i)
        self.current_object["visual"]["zPos"] = self.BASE_ZPOS

    def placeHolding(self, pos):
        if self.current_holding_kwargs["type"] == "device":

            def on_close(port):
                if port is None or port == "":
                    return
                dev_name = self.current_holding_kwargs["name"]
                rest = self.current_holding_kwargs.copy()
                rest["position"] = [float(self.current_mpos[0]), float(self.current_mpos[1])]
                rest["port"] = port
                del rest["type"]
                del rest["name"]
                self.current_devices.append({dev_name: rest})
                self.updateZpos()
                self.resetBotVisual()
                self.generateHoldingItem()

            self.addPortPicker(on_close)
        else:
            obj = {
                "physics": True,
                "type": "object",
                "visual": self.current_holding_kwargs.copy(),
                "position": pos,
                "rotation": self.current_holding_kwargs.get("rotation", 0),
                "restitution": 0.2,
                "friction": 0.8,
            }
            self.current_object["children"].append(obj)
            self.updateZpos()
            self.resetBotVisual()
            self.generateHoldingItem()

    def removeSelected(self):
        if self.selected_index in ["Holding", None, "Baseplate"]:
            # We can't do anything.
            return
        if self.selected_index[0] == "Children":
            del self.current_object["children"][self.selected_index[1]]
        elif self.selected_index[0] == "Devices":
            del self.current_devices[self.selected_index[1]]
        self.updateZpos()
        self.selected_index = None
        self.selected_type = self.SELECTED_NOTHING
        self.clearOptions()
        self.resetBotVisual()

    def selectObj(self, pos):
        from ev3sim.simulation.world import World

        shapes = World.instance.space.point_query(
            [float(v) for v in pos], 0.0, pymunk.ShapeFilter(mask=DYNAMIC_CATEGORY)
        )
        if shapes:
            top_shape_z = max(map(lambda x: x.shape.actual_obj.visual.zPos, shapes))
            top_shape = list(filter(lambda x: x.shape.actual_obj.visual.zPos == top_shape_z, shapes))
            assert len(top_shape) == 1
            self.selected_index = top_shape[0].shape.actual_obj.identifier
            name = self.getSelectedAttribute("name", None)
            if name == "Circle":
                self.selected_type = self.SELECTED_CIRCLE
            elif name == "Rectangle":
                self.selected_type = self.SELECTED_RECTANGLE
            elif name == "Polygon":
                self.selected_type = self.SELECTED_POLYGON
            else:
                self.selected_type = self.SELECTED_DEVICE
            self.drawOptions()
        else:
            self.selected_index = None

    def generateObjects(self):

        self.side_width = self._size[0] / 6
        self.bot_height = self._size[1] / 6

        # Bg
        self.sidebar = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(-5, -5, self.side_width, self._size[1] + 10),
            starting_layer_height=-0.5,
            manager=self,
            object_id=pygame_gui.core.ObjectID("sidebar-bot-edit", "bot_edit_bar"),
        )
        self._all_objs.append(self.sidebar)

        self.bot_bar = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(
                -10 + self.side_width,
                self._size[1] - self.bot_height + 5,
                self._size[0] - self.side_width + 20,
                self.bot_height,
            ),
            starting_layer_height=-0.5,
            manager=self,
            object_id=pygame_gui.core.ObjectID("botbar-bot-edit", "bot_edit_bar"),
        )
        self._all_objs.append(self.bot_bar)

        # Clickies
        icon_size = self.side_width / 2

        def iconPos(index):
            # Need to handle the rectangle button a bit different.
            if index < 2:
                return self.side_width / 2 - icon_size / 2, 20 + icon_size * 1.3 * index
            elif index == 2:
                return self.side_width / 2 - icon_size / 2, 20 + icon_size * 2.5
            else:
                return self.side_width / 2 - icon_size / 2, 20 + icon_size * (1.3 * (index - 3) + 3.7)

        self.select_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(*iconPos(0), icon_size, icon_size),
            text="",
            manager=self,
            object_id=pygame_gui.core.ObjectID("select-button", "invis_button"),
        )
        self.addButtonEvent("select-button", self.clickSelect)
        select_icon_path = find_abs("ui/icon_select.png", allowed_areas=asset_locations())
        self.select_icon = pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect(*iconPos(0), icon_size, icon_size),
            image_surface=pygame.image.load(select_icon_path),
            manager=self,
            object_id=pygame_gui.core.ObjectID("select-icon"),
        )
        self._all_objs.append(self.select_button)
        self._all_objs.append(self.select_icon)

        self.circle_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(*iconPos(1), icon_size, icon_size),
            text="",
            manager=self,
            object_id=pygame_gui.core.ObjectID("circle-button", "invis_button"),
        )
        self.addButtonEvent("circle-button", self.clickCircle)
        circ_icon_path = find_abs("ui/icon_circle.png", allowed_areas=asset_locations())
        self.circle_icon = pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect(*iconPos(1), icon_size, icon_size),
            image_surface=pygame.image.load(circ_icon_path),
            manager=self,
            object_id=pygame_gui.core.ObjectID("circle-icon"),
        )
        self._all_objs.append(self.circle_button)
        self._all_objs.append(self.circle_icon)

        self.rectangle_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(*iconPos(2), icon_size, icon_size),
            text="",
            manager=self,
            object_id=pygame_gui.core.ObjectID("rectangle-button", "invis_button"),
        )
        self.addButtonEvent("rectangle-button", self.clickRectangle)
        rect_loc = pygame.Rect(*iconPos(2), icon_size, icon_size)
        rect_loc.y += icon_size * 0.25
        rect_loc.height /= 2
        rect_icon_path = find_abs("ui/icon_rectangle.png", allowed_areas=asset_locations())
        self.rectangle_icon = pygame_gui.elements.UIImage(
            relative_rect=rect_loc,
            image_surface=pygame.image.load(rect_icon_path),
            manager=self,
            object_id=pygame_gui.core.ObjectID("rectangle-icon"),
        )
        self._all_objs.append(self.rectangle_button)
        self._all_objs.append(self.rectangle_icon)

        self.polygon_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(*iconPos(3), icon_size, icon_size),
            text="",
            manager=self,
            object_id=pygame_gui.core.ObjectID("polygon-button", "invis_button"),
        )
        self.addButtonEvent("polygon-button", self.clickPolygon)
        polygon_icon_path = find_abs("ui/icon_polygon.png", allowed_areas=asset_locations())
        self.polygon_icon = pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect(*iconPos(3), icon_size, icon_size),
            image_surface=pygame.image.load(polygon_icon_path),
            manager=self,
            object_id=pygame_gui.core.ObjectID("polygon-icon"),
        )
        self._all_objs.append(self.polygon_button)
        self._all_objs.append(self.polygon_icon)

        self.device_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(*iconPos(4), icon_size, icon_size),
            text="",
            manager=self,
            object_id=pygame_gui.core.ObjectID("device-button", "invis_button"),
        )
        self.addButtonEvent("device-button", self.clickDevice)
        device_icon_path = find_abs("ui/icon_device.png", allowed_areas=asset_locations())
        self.device_icon = pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect(*iconPos(4), icon_size, icon_size),
            image_surface=pygame.image.load(device_icon_path),
            manager=self,
            object_id=pygame_gui.core.ObjectID("device-icon"),
        )
        self._all_objs.append(self.device_button)
        self._all_objs.append(self.device_icon)

        # Other options
        lock_size = self.side_width / 4
        self.lock_grid_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(
                10, self._size[1] - lock_size - 60, (self.side_width - 30) - lock_size - 5, lock_size
            ),
            text="Lock Grid",
            manager=self,
            object_id=pygame_gui.core.ObjectID("lock_grid-label", "bot_edit_label"),
        )
        but_rect = pygame.Rect(self.side_width - lock_size - 20, self._size[1] - lock_size - 60, lock_size, lock_size)
        self.lock_grid_image = pygame_gui.elements.UIImage(
            relative_rect=but_rect,
            manager=self,
            image_surface=pygame.Surface((but_rect.width, but_rect.height)),
            object_id=pygame_gui.core.ObjectID("lock_grid-image"),
        )
        self.updateCheckbox()
        self.lock_grid_button = pygame_gui.elements.UIButton(
            relative_rect=but_rect,
            manager=self,
            object_id=pygame_gui.core.ObjectID(f"lock_grid-button", "checkbox-button"),
            text="",
        )

        def clickLock():
            self.lock_grid = not self.lock_grid
            self.updateCheckbox()

        self.addButtonEvent("lock_grid-button", clickLock)
        self._all_objs.append(self.lock_grid_label)
        self._all_objs.append(self.lock_grid_image)
        self._all_objs.append(self.lock_grid_button)

        self.grid_size_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(
                10, self._size[1] - lock_size - 15, (self.side_width - 30) - lock_size - 5, lock_size
            ),
            text="Grid Size",
            manager=self,
            object_id=pygame_gui.core.ObjectID("grid_size-label", "bot_edit_label"),
        )
        self.grid_size_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(
                self.side_width - lock_size - 20, self._size[1] - lock_size - 15, lock_size, lock_size
            ),
            manager=self,
            object_id=pygame_gui.core.ObjectID("grid_size-entry", "num_entry"),
        )
        self.grid_size_entry.set_text(str(self.grid_size))
        self._all_objs.append(self.grid_size_label)
        self._all_objs.append(self.grid_size_entry)

        # Save/Cancel
        self.save_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                self._size[0] - self.side_width * 0.9,
                self._size[1] - self.bot_height * 0.9,
                self.side_width * 0.8,
                self.bot_height * 0.35,
            ),
            text="Create" if self.creating else "Save",
            manager=self,
            object_id=pygame_gui.core.ObjectID("save-changes", "action_button"),
        )
        self.addButtonEvent("save-changes", self.clickSave)
        self.cancel_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                self._size[0] - self.side_width * 0.9,
                self._size[1] - self.bot_height * 0.45,
                self.side_width * 0.8,
                self.bot_height * 0.4,
            ),
            text="Cancel",
            manager=self,
            object_id=pygame_gui.core.ObjectID("cancel-changes", "action_button"),
        )
        self.addButtonEvent("cancel-changes", lambda: ScreenObjectManager.instance.popScreen())
        self._all_objs.append(self.save_button)
        self._all_objs.append(self.cancel_button)

        # Bot blitting
        self.surf_size = (self._size[0] - self.side_width + 5, self._size[1] - self.bot_height + 5)
        self.bot_screen = pygame.Surface(self.surf_size)
        if self.selected_index:
            self.drawOptions()
        self.resetBotVisual()
        super().generateObjects()

    def generateHoldingItem(self):
        from ev3sim.visual.objects import visualFactory

        if "holding" in ScreenObjectManager.instance.objects:
            ScreenObjectManager.instance.unregisterVisual("holding")

        if self.current_holding_kwargs["type"] == "device":
            from ev3sim.simulation.loader import ScriptLoader

            if "holding_bot" in ScriptLoader.instance.object_map:
                ScreenObjectManager.instance.unregisterVisual("holding_bot")
                for child in ScriptLoader.instance.object_map["holding_bot"].children:
                    ScreenObjectManager.instance.unregisterVisual(child.key)
                del ScriptLoader.instance.object_map["holding_bot"]
                to_remove = []
                for i, interactor in enumerate(ScriptLoader.instance.active_scripts):
                    if interactor.physical_object.key == "holding_bot":
                        to_remove.append(i)
                for index in to_remove[::-1]:
                    del ScriptLoader.instance.active_scripts[index]
            ScriptLoader.instance.loadElements(
                [
                    {
                        "type": "object",
                        "physics": False,
                        "visual": {
                            "name": "Circle",
                            "stroke": None,
                            "fill": None,
                            "stroke_width": 0,
                            "radius": 0,
                            "zPos": 20,
                        },
                        "children": [self.current_holding_kwargs],
                        "key": "holding_bot",
                    }
                ]
            )
            for interactor in ScriptLoader.instance.active_scripts:
                if interactor.physical_object.key == "holding_bot":
                    interactor.port_key = "holding"
                    if "holding" not in Randomiser.instance.port_randomisers:
                        Randomiser.createPortRandomiserWithSeed(interactor.port_key)
                    interactor.startUp()
                    interactor.device_class.generateBias()
                    try:
                        interactor.tick(0)
                        # Some devices can't be ticked outside of simulation.
                    except:
                        pass
                    interactor.afterPhysics()
                    self.current_holding = interactor.generated
                    for i, obj in enumerate(self.current_holding):
                        obj.visual.customMap = self.customMap
                        obj.visual.offset_position = interactor.relative_positions[i]
                        obj.visual.position = [
                            self.current_mpos[0]
                            + obj.visual.offset_position[0] * np.cos(obj.visual.rotation)
                            + obj.visual.offset_position[1] * np.sin(obj.visual.rotation),
                            self.current_mpos[1]
                            + obj.visual.offset_position[1] * np.cos(obj.visual.rotation)
                            + obj.visual.offset_position[0] * np.sin(obj.visual.rotation),
                        ]
                    break
        else:
            self.current_holding = visualFactory(**self.current_holding_kwargs)
            self.current_holding.customMap = self.customMap
            self.current_holding.position = self.current_mpos
            ScreenObjectManager.instance.registerVisual(self.current_holding, "holding")

    def clickSelect(self):
        from ev3sim.simulation.loader import ScriptLoader

        if "holding" in ScreenObjectManager.instance.objects:
            ScreenObjectManager.instance.unregisterVisual("holding")
        if "holding_bot" in ScreenObjectManager.instance.objects:
            ScreenObjectManager.instance.unregisterVisual("holding_bot")
            for child in ScriptLoader.instance.object_map["holding_bot"].children:
                ScreenObjectManager.instance.unregisterVisual(child.key)
            del ScriptLoader.instance.object_map["holding_bot"]
            to_remove = []
            for i, interactor in enumerate(ScriptLoader.instance.active_scripts):
                if interactor.physical_object.key == "holding_bot":
                    to_remove.append(i)
            for index in to_remove[::-1]:
                del ScriptLoader.instance.active_scripts[index]
        self.current_holding = None
        self.selected_type = self.SELECTED_NOTHING
        self.selected_index = None
        self.clearOptions()

    def clickCircle(self):
        self.current_holding_kwargs = {
            "type": "visual",
            "name": "Circle",
            "radius": 1,
            "fill": "#878E88",
            "stroke_width": 0.1,
            "stroke": "#ffffff",
            "zPos": self.HOLD_ZPOS,
        }
        self.selected_index = "Holding"
        self.selected_type = self.SELECTED_CIRCLE
        self.drawOptions()
        self.generateHoldingItem()

    def clickRectangle(self):
        self.current_holding_kwargs = {
            "type": "visual",
            "name": "Rectangle",
            "width": 6,
            "height": 3,
            "fill": "#878E88",
            "stroke_width": 0.1,
            "stroke": "#ffffff",
            "zPos": self.HOLD_ZPOS,
        }
        self.selected_index = "Holding"
        self.selected_type = self.SELECTED_RECTANGLE
        self.drawOptions()
        self.generateHoldingItem()

    def clickPolygon(self):
        self.current_holding_kwargs = {
            "type": "visual",
            "name": "Polygon",
            "fill": "#878E88",
            "stroke_width": 0.1,
            "stroke": "#ffffff",
            "verts": [
                [np.sin(0), np.cos(0)],
                [np.sin(2 * np.pi / 5), np.cos(2 * np.pi / 5)],
                [np.sin(4 * np.pi / 5), np.cos(4 * np.pi / 5)],
                [np.sin(6 * np.pi / 5), np.cos(6 * np.pi / 5)],
                [np.sin(8 * np.pi / 5), np.cos(8 * np.pi / 5)],
            ],
            "zPos": self.HOLD_ZPOS,
        }
        self.selected_index = "Holding"
        self.selected_type = self.SELECTED_POLYGON
        self.drawOptions()
        self.generateHoldingItem()

    def clickDevice(self):
        self.addDevicePicker()

    def clickStroke(self):
        self.colour_field = "stroke"
        start_colour = self.getSelectedAttribute("stroke", "")
        self.addColourPicker("Pick Stroke", start_colour)

    def clickFill(self):
        self.colour_field = "fill"
        start_colour = self.getSelectedAttribute("fill", "")
        self.addColourPicker("Pick Fill", start_colour)

    def updateCheckbox(self):
        img = pygame.image.load(
            find_abs("ui/box_check.png" if self.lock_grid else "ui/box_clear.png", allowed_areas=asset_locations())
        )
        if img.get_size() != self.lock_grid_image.rect.size:
            img = pygame.transform.smoothscale(img, (self.lock_grid_image.rect.width, self.lock_grid_image.rect.height))
        self.lock_grid_image.set_image(img)

    def checkBot(self):
        # Returns true if there are any errors with the bot.
        ports = set()
        for device in self.current_devices:
            ports.add(device[list(device.keys())[0]]["port"])
        if len(ports) != len(self.current_devices):
            self.addErrorDialog(
                '<font color="#cc0000">You have multiple devices using the same port.</font><br><br>'
                + "Select some of your existing devices and change the ports."
            )
            return True
        return False

    def clickSave(self):
        if self.checkBot():
            return
        if self.creating:
            self.addCodePicker()
        else:
            self.saveBot()
            ScreenObjectManager.instance.popScreen()

    def saveBot(self):
        self.previous_info["base_plate"] = self.current_object
        del self.previous_info["base_plate"]["type"]
        del self.previous_info["base_plate"]["physics"]
        verts = [[float(v2) for v2 in v1] for v1 in self.previous_info["base_plate"].get("visual", {}).get("verts", [])]
        if verts:
            self.previous_info["base_plate"]["visual"]["verts"] = verts
        for child in self.previous_info["base_plate"]["children"]:
            child["position"] = [float(v) for v in child["position"]]
            verts = [[float(v2) for v2 in v1] for v1 in child.get("verts", [])]
            if verts:
                child["verts"] = verts
            verts = [[float(v2) for v2 in v1] for v1 in child.get("visual", {}).get("verts", [])]
            if verts:
                child["visual"]["verts"] = verts

        self.previous_info["devices"] = self.current_devices
        with open(os.path.join(self.bot_file, "config.bot"), "w") as f:
            f.write(yaml.dump(self.previous_info))
        ScreenObjectManager.instance.captureBotImage(*self.bot_dir_file)
        if self.onSave is not None:
            self.onSave(self.bot_dir_file[1])

    def handleEvent(self, event):
        if self.mode == self.MODE_NORMAL:
            button_filter = lambda x: True
        else:
            button_filter = lambda x: False
        super().handleEvent(event, button_filter=button_filter)
        if self.mode == self.MODE_NORMAL:
            if event.type == pygame.MOUSEMOTION:
                self.actual_mpos = event.pos
                self.current_mpos = screenspace_to_worldspace(
                    (event.pos[0] - self.side_width, event.pos[1]), customScreen=self.customMap
                )
                if self.lock_grid and not self.dragging:
                    self.current_mpos = [
                        ((self.current_mpos[0] + self.grid_size / 2) // self.grid_size) * self.grid_size,
                        ((self.current_mpos[1] + self.grid_size / 2) // self.grid_size) * self.grid_size,
                    ]
                if self.current_holding is not None:
                    if self.current_holding_kwargs["type"] == "device":
                        for obj in self.current_holding:
                            obj.visual.position = [
                                self.current_mpos[0]
                                + obj.visual.offset_position[0] * np.cos(obj.visual.rotation)
                                + obj.visual.offset_position[1] * np.sin(obj.visual.rotation),
                                self.current_mpos[1]
                                + obj.visual.offset_position[1] * np.cos(obj.visual.rotation)
                                + obj.visual.offset_position[0] * np.sin(obj.visual.rotation),
                            ]
                    else:
                        self.current_holding.position = self.current_mpos
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mpos = screenspace_to_worldspace(
                    (event.pos[0] - self.side_width, event.pos[1]), customScreen=self.customMap
                )
                if (
                    -self.customMap["MAP_WIDTH"] / 2 <= mpos[0] <= self.customMap["MAP_WIDTH"] / 2
                    and -self.customMap["MAP_HEIGHT"] / 2 <= mpos[1] <= self.customMap["MAP_HEIGHT"] / 2
                ):
                    if self.current_holding is None:
                        self.selectObj(mpos)
                        if self.selected_index is not None:
                            self.dragging = True
                            pos = self.getSelectedAttribute("position", [0, 0])
                            if isinstance(self.selected_index, (tuple, list)) and self.selected_index[0] == "Children":
                                pos = self.current_object["children"][self.selected_index[1]]["position"]
                            self.offset_position = [pos[0] - mpos[0], pos[1] - mpos[1]]
                    else:
                        if self.lock_grid:
                            mpos = [
                                ((mpos[0] + self.grid_size / 2) // self.grid_size) * self.grid_size,
                                ((mpos[1] + self.grid_size / 2) // self.grid_size) * self.grid_size,
                            ]
                        self.placeHolding(mpos)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.dragging = False
            elif event.type == pygame.MOUSEWHEEL:
                for attr, conv, inc in [
                    ("rotation_entry", float, 1),
                    ("radius_entry", float, 0.1),
                    ("width_entry", float, 0.1),
                    ("height_entry", float, 0.1),
                    ("size_entry", float, 0.1),
                    ("stroke_entry", float, 0.05),
                    ("sides_entry", int, 1),
                ]:
                    if hasattr(self, attr):
                        rect = getattr(self, attr).get_relative_rect()
                        if (
                            rect.left <= self.actual_mpos[0] <= rect.right
                            and rect.top <= self.actual_mpos[1] <= rect.bottom
                        ):
                            try:
                                val = conv(getattr(self, attr).text)
                                val += event.y * inc
                                if conv == float:
                                    # Make 0.200001 = 0.1999999 = 0.2
                                    res = str(val + 1e-8)
                                    if "." in res:
                                        idx = res.index(".")
                                        for i in range(max(0, idx - 1), len(res)):
                                            try:
                                                if abs(float(res[:i]) - val) < 1e-5:
                                                    val = float(res[:i])
                                                    break
                                            except:
                                                continue
                                getattr(self, attr).set_text(str(val))
                            except:
                                pass
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE or event.key == pygame.K_DELETE:
                    if self.selected_type not in [None, "Holding", "Baseplate"]:
                        # Check that no entry is focused.
                        good = True
                        for attr in [
                            "rotation_entry",
                            "radius_entry",
                            "width_entry",
                            "height_entry",
                            "size_entry",
                            "stroke_entry",
                            "sides_entry",
                        ]:
                            if hasattr(self, attr) and getattr(self, attr).is_focused:
                                good = False
                        if good:
                            self.removeSelected()

    def drawOptions(self):
        self.clearOptions()
        if self.selected_type == self.SELECTED_NOTHING:
            return
        name = self.getSelectedAttribute("name", None)
        if name == "Circle":
            self.drawCircleOptions()
        elif name == "Rectangle":
            self.drawRectangleOptions()
        elif name == "Polygon":
            self.drawPolygonOptions()
        else:
            self.drawDeviceOptions()
        if self.selected_index not in ["Holding", "Baseplate", None]:
            self.drawRemove()

    def drawRemove(self):
        icon_size = self.side_width / 2
        self.remove_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                self.side_width * 0.2, 50 + icon_size * 5.8, self.side_width * 0.6, self.side_width * 0.4
            ),
            text="Remove",
            manager=self,
            object_id=pygame_gui.core.ObjectID("remove_button", "cancel-changes"),
        )
        self.addButtonEvent("remove_button", self.removeSelected)
        self._all_objs.append(self.remove_button)

    def labelRect(self, x, y):
        entry_size = self.side_width / 3
        return pygame.Rect(
            (x + 1) * self.side_width + 20 + x * 40,
            self._size[1] - ((self.bot_height - 15) if y == 0 else (entry_size)),
            (self.side_width - 30) - entry_size - 5,
            entry_size,
        )

    def entryRect(self, x, y):
        entry_size = self.side_width / 3
        return pygame.Rect(
            (x + 2) * self.side_width - 10 + 40 * x,
            self._size[1] - ((self.bot_height - 15) if y == 0 else (entry_size)) + 5,
            entry_size,
            entry_size,
        )

    def drawCircleOptions(self):
        # Radius
        self.radius_label = pygame_gui.elements.UILabel(
            relative_rect=self.labelRect(0, 0),
            text="Radius",
            manager=self,
            object_id=pygame_gui.core.ObjectID("radius-label", "bot_edit_label"),
        )
        self.radius_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=self.entryRect(0, 0),
            manager=self,
            object_id=pygame_gui.core.ObjectID("radius-entry", "num_entry"),
        )
        self.radius_entry.set_text(str(self.getSelectedAttribute("radius")))

        # Stroke width
        self.stroke_num_label = pygame_gui.elements.UILabel(
            relative_rect=self.labelRect(0, 1),
            text="Stroke",
            manager=self,
            object_id=pygame_gui.core.ObjectID("stroke-label", "bot_edit_label"),
        )
        self.stroke_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=self.entryRect(0, 1),
            manager=self,
            object_id=pygame_gui.core.ObjectID("stroke-entry", "num_entry"),
        )
        self.stroke_entry.set_text(str(self.getSelectedAttribute("stroke_width")))

        self.generateColourPickers()

    def drawRectangleOptions(self):
        # Width/Height
        self.width_label = pygame_gui.elements.UILabel(
            relative_rect=self.labelRect(0, 0),
            text="Width",
            manager=self,
            object_id=pygame_gui.core.ObjectID("width-label", "bot_edit_label"),
        )
        self.width_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=self.entryRect(0, 0),
            manager=self,
            object_id=pygame_gui.core.ObjectID("width-entry", "num_entry"),
        )
        self.width_entry.set_text(str(self.getSelectedAttribute("width")))

        self.height_label = pygame_gui.elements.UILabel(
            relative_rect=self.labelRect(0, 1),
            text="Height",
            manager=self,
            object_id=pygame_gui.core.ObjectID("height-label", "bot_edit_label"),
        )
        self.height_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=self.entryRect(0, 1),
            manager=self,
            object_id=pygame_gui.core.ObjectID("height-entry", "num_entry"),
        )
        self.height_entry.set_text(str(self.getSelectedAttribute("height")))

        self.generateColourPickers()

        # Rotation
        self.rotation_label = pygame_gui.elements.UILabel(
            relative_rect=self.labelRect(2, 0),
            text="Rotation",
            manager=self,
            object_id=pygame_gui.core.ObjectID("rotation-label", "bot_edit_label"),
        )
        self.rotation_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=self.entryRect(2, 0),
            manager=self,
            object_id=pygame_gui.core.ObjectID("rotation-entry", "num_entry"),
        )
        # Takeaway pi/2, so that pointing up is rotation 0.
        cur_rotation = self.getSelectedAttribute("rotation", 0, visual=False)
        self.rotation_entry.set_text(str(180 / np.pi * cur_rotation))

        # Stroke width
        self.stroke_num_label = pygame_gui.elements.UILabel(
            relative_rect=self.labelRect(2, 1),
            text="Stroke",
            manager=self,
            object_id=pygame_gui.core.ObjectID("stroke-label", "bot_edit_label"),
        )
        self.stroke_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=self.entryRect(2, 1),
            manager=self,
            object_id=pygame_gui.core.ObjectID("stroke-entry", "num_entry"),
        )
        self.stroke_entry.set_text(str(self.getSelectedAttribute("stroke_width")))

    def drawPolygonOptions(self):
        # Sides
        self.sides_label = pygame_gui.elements.UILabel(
            relative_rect=self.labelRect(0, 0),
            text="Sides",
            manager=self,
            object_id=pygame_gui.core.ObjectID("sides-label", "bot_edit_label"),
        )
        self.sides_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=self.entryRect(0, 0),
            manager=self,
            object_id=pygame_gui.core.ObjectID("sides-entry", "num_entry"),
        )
        self.sides_entry.set_text(str(len(self.getSelectedAttribute("verts"))))

        # Size
        self.size_label = pygame_gui.elements.UILabel(
            relative_rect=self.labelRect(0, 1),
            text="Size",
            manager=self,
            object_id=pygame_gui.core.ObjectID("size-label", "bot_edit_label"),
        )
        self.size_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=self.entryRect(0, 1),
            manager=self,
            object_id=pygame_gui.core.ObjectID("size-entry", "num_entry"),
        )
        self.size_entry.set_text(str(np.linalg.norm(self.getSelectedAttribute("verts")[0], 2)))

        self.generateColourPickers()

        # Rotation
        self.rotation_label = pygame_gui.elements.UILabel(
            relative_rect=self.labelRect(2, 0),
            text="Rotation",
            manager=self,
            object_id=pygame_gui.core.ObjectID("rotation-label", "bot_edit_label"),
        )
        self.rotation_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=self.entryRect(2, 0),
            manager=self,
            object_id=pygame_gui.core.ObjectID("rotation-entry", "num_entry"),
        )
        # Takeaway pi/2, so that pointing up is rotation 0.
        cur_rotation = (
            np.arctan2(self.getSelectedAttribute("verts")[0][1], self.getSelectedAttribute("verts")[0][0]) - np.pi / 2
        )
        while cur_rotation < 0:
            cur_rotation += np.pi
        self.rotation_entry.set_text(str(180 / np.pi * cur_rotation))

        # Stroke width
        self.stroke_num_label = pygame_gui.elements.UILabel(
            relative_rect=self.labelRect(2, 1),
            text="Stroke",
            manager=self,
            object_id=pygame_gui.core.ObjectID("stroke-label", "bot_edit_label"),
        )
        self.stroke_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=self.entryRect(2, 1),
            manager=self,
            object_id=pygame_gui.core.ObjectID("stroke-entry", "num_entry"),
        )
        self.stroke_entry.set_text(str(self.getSelectedAttribute("stroke_width")))

    def drawDeviceOptions(self):
        # Rotation
        self.rotation_label = pygame_gui.elements.UILabel(
            relative_rect=self.labelRect(0, 0),
            text="Rotation",
            manager=self,
            object_id=pygame_gui.core.ObjectID("rotation-label", "bot_edit_label"),
        )
        self.rotation_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=self.entryRect(0, 0),
            manager=self,
            object_id=pygame_gui.core.ObjectID("rotation-entry", "num_entry"),
        )
        # Takeaway pi/2, so that pointing up is rotation 0.
        cur_rotation = self.getSelectedAttribute("rotation", 0)
        self.rotation_entry.set_text(str(cur_rotation))

        # Port
        self.port_label = pygame_gui.elements.UILabel(
            relative_rect=self.labelRect(0, 1),
            text="Port",
            manager=self,
            object_id=pygame_gui.core.ObjectID("port-label", "bot_edit_label"),
        )
        rect = self.entryRect(0, 1)
        rect.width += 70
        self.port_entry = pygame_gui.elements.UIButton(
            relative_rect=rect,
            text=self.getSelectedAttribute("port"),
            manager=self,
            object_id=pygame_gui.core.ObjectID("port-value", "any_button"),
        )

        def on_close(port):
            if port is None or port == "":
                return
            self.setSelectedAttribute("port", port)

        self.addButtonEvent("port-value", lambda: self.addPortPicker(on_close))

    def generateColourPickers(self):
        # Colour pickers
        button_size = self.side_width / 3 * 0.9

        stroke_label_rect = self.labelRect(1, 0)
        stroke_label_rect.width += 40
        self.stroke_label = pygame_gui.elements.UILabel(
            relative_rect=stroke_label_rect,
            text="Stroke Colour",
            manager=self,
            object_id=pygame_gui.core.ObjectID("stroke_colour-label", "bot_edit_label"),
        )
        stroke_image_rect = self.entryRect(1, 0)
        stroke_image_rect.y += (self.side_width / 3 - button_size) / 2
        stroke_image_rect.width = button_size
        stroke_image_rect.height = button_size
        self.stroke_img = pygame_gui.elements.UIButton(
            relative_rect=stroke_image_rect,
            text="",
            manager=self,
            object_id=pygame_gui.core.ObjectID("stroke_colour-button"),
        )
        self.addButtonEvent("stroke_colour-button", self.clickStroke)

        fill_label_rect = self.labelRect(1, 1)
        fill_label_rect.width += 40
        self.fill_label = pygame_gui.elements.UILabel(
            relative_rect=fill_label_rect,
            text="Fill Colour",
            manager=self,
            object_id=pygame_gui.core.ObjectID("fill_colour-label", "bot_edit_label"),
        )
        fill_image_rect = self.entryRect(1, 1)
        fill_image_rect.y += (self.side_width / 3 - button_size) / 2
        fill_image_rect.width = button_size
        fill_image_rect.height = button_size
        self.fill_img = pygame_gui.elements.UIButton(
            relative_rect=fill_image_rect,
            text="",
            manager=self,
            object_id=pygame_gui.core.ObjectID("fill_colour-button"),
        )
        self.addButtonEvent("fill_colour-button", self.clickFill)
        data = {
            "fill_colour-button": {
                "colours": {
                    "normal_bg": self.getSelectedAttribute("fill"),
                    "hovered_bg": self.getSelectedAttribute("fill"),
                    "active_bg": self.getSelectedAttribute("fill"),
                }
            },
            "stroke_colour-button": {
                "colours": {
                    "normal_bg": self.getSelectedAttribute("stroke"),
                    "hovered_bg": self.getSelectedAttribute("stroke"),
                    "active_bg": self.getSelectedAttribute("stroke"),
                }
            },
        }
        self.ui_theme._load_element_colour_data_from_theme("colours", "fill_colour-button", data)
        self.fill_img.rebuild_from_changed_theme_data()
        self.ui_theme._load_element_colour_data_from_theme("colours", "stroke_colour-button", data)
        self.stroke_img.rebuild_from_changed_theme_data()

    def addCodePicker(self):
        self.mode = self.MODE_CODE_DIALOG

        class CodePicker(pygame_gui.elements.UIWindow):
            def kill(self2):
                super().kill()
                self.removeCodePicker()

            def process_event(self2, event: pygame.event.Event):
                if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                    if "pick_mindstorms" in event.ui_object_id:
                        self.previous_info["type"] = "mindstorms"
                        self2.kill()
                        self.addNamePicker()
                    elif "pick_python" in event.ui_object_id:
                        self.previous_info["type"] = "python"
                        self2.kill()
                        self.addNamePicker()
                return super().process_event(event)

        picker_size = (self._size[0] * 0.7, self._size[1] * 0.6)

        self.picker = CodePicker(
            rect=pygame.Rect(self._size[0] * 0.15, self._size[1] * 0.15, *picker_size),
            manager=self,
            window_display_title="How will you program?",
            object_id=pygame_gui.core.ObjectID("code_dialog"),
        )

        horiz_size = picker_size[0] - 40

        self.mindstorms_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(horiz_size / 16, picker_size[1] / 4 - 75, horiz_size * 3 / 8, picker_size[1] / 2),
            manager=self,
            object_id=pygame_gui.core.ObjectID("pick_mindstorms", "invis_button"),
            container=self.picker,
            text="Mindstorms",
        )
        self.mindstorms_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(
                horiz_size / 16, picker_size[1] * 2 / 8 - 75, horiz_size * 3 / 8, picker_size[1] * 1 / 8
            ),
            text="Mindstorms",
            manager=self,
            container=self.picker,
            object_id=pygame_gui.core.ObjectID("mindstorms_label", "bot_edit_label"),
        )
        mindstorms = pygame.image.load(find_abs(f"ui/mindstorms.png", asset_locations()))
        self.mindstorms_image = pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect(
                horiz_size / 16, picker_size[1] * 3 / 8 - 75, horiz_size * 3 / 8, picker_size[1] * 3 / 8
            ),
            image_surface=mindstorms,
            manager=self,
            container=self.picker,
            object_id=pygame_gui.core.ObjectID(f"mindstorms_img", "baseplate_img"),
        )
        self.python_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                horiz_size * 9 / 16, picker_size[1] / 4 - 75, horiz_size * 3 / 8, picker_size[1] / 2
            ),
            manager=self,
            object_id=pygame_gui.core.ObjectID("pick_python", "invis_button"),
            container=self.picker,
            text="Python",
        )
        self.python_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(
                horiz_size * 9 / 16, picker_size[1] * 2 / 8 - 75, horiz_size * 3 / 8, picker_size[1] * 1 / 8
            ),
            text="Python",
            manager=self,
            container=self.picker,
            object_id=pygame_gui.core.ObjectID("python_label", "bot_edit_label"),
        )
        python = pygame.image.load(find_abs(f"ui/python.png", asset_locations()))
        self.python_image = pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect(
                horiz_size * 9 / 16, picker_size[1] * 3 / 8 - 75, horiz_size * 3 / 8, picker_size[1] * 3 / 8
            ),
            image_surface=python,
            manager=self,
            container=self.picker,
            object_id=pygame_gui.core.ObjectID(f"python_img", "baseplate_img"),
        )

    def addNamePicker(self):
        self.mode = self.MODE_NAME_DIALOG

        class NamePicker(pygame_gui.elements.UIWindow):
            def kill(self2):
                super().kill()
                self.removeNamePicker()

            def process_event(self2, event: pygame.event.Event):
                if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                    if "create_bot" in event.ui_object_id:
                        name = self.bot_name_entry.text
                        found = False
                        try:
                            find_abs(name, ["workspace/robots/"])
                            found = True
                        except:
                            pass
                        if found:
                            self.addErrorDialog('<font color="#cc0000">This name is already taken.</font>')
                            return True
                        # Now, create the necessary files/folders.
                        self.bot_file = os.path.join(find_abs_directory("workspace/robots/"), name)
                        self.bot_dir_file = ["workspace/robots/", name]
                        os.mkdir(self.bot_file)
                        if self.previous_info.get("type", "python") == "python":
                            _ = open(os.path.join(self.bot_file, "code.py"), "w")
                        else:
                            shutil.copy(
                                find_abs("default_mindstorms.ev3", ["package/presets/"]),
                                os.path.join(self.bot_file, "program.ev3"),
                            )
                        self.removeNamePicker()
                        self.saveBot()
                        ScreenObjectManager.instance.popScreen()
                return super().process_event(event)

        picker_size = (self._size[0] * 0.7, max(self._size[1] * 0.4, 100))

        self.picker = NamePicker(
            rect=pygame.Rect(self._size[0] * 0.15, self._size[1] * 0.15, *picker_size),
            manager=self,
            window_display_title="Name Your Bot",
            object_id=pygame_gui.core.ObjectID("name_dialog"),
        )

        self.bot_name_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(
                30,
                40,
                picker_size[0] - 105,
                40,
            ),
            manager=self,
            container=self.picker,
            object_id=pygame_gui.core.ObjectID("bot_name_entry"),
        )
        self.bot_name_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(picker_size[0] - 195, picker_size[1] - 150, 120, 40),
            manager=self,
            object_id=pygame_gui.core.ObjectID("create_bot", "action_button"),
            container=self.picker,
            text="Create",
        )

    def addColourPicker(self, title, start_colour):
        from ev3sim.visual.utils import rgb_to_hex

        self.mode = self.MODE_COLOUR_DIALOG

        class ColourPicker(pygame_gui.windows.UIColourPickerDialog):
            def process_event(self2, event: pygame.event.Event) -> bool:
                consumed_event = pygame_gui.elements.UIWindow.process_event(self2, event)
                if (
                    event.type == pygame.USEREVENT
                    and event.user_type == pygame_gui.UI_BUTTON_PRESSED
                    and event.ui_element == self2.cancel_button
                ):
                    self2.kill()
                    return consumed_event

                if (
                    event.type == pygame.USEREVENT
                    and event.user_type == pygame_gui.UI_BUTTON_PRESSED
                    and event.ui_element == self2.ok_button
                ):
                    new_col = rgb_to_hex(
                        self2.red_channel.current_value,
                        self2.green_channel.current_value,
                        self2.blue_channel.current_value,
                    )
                    self.setSelectedAttribute(self.colour_field, new_col)
                    self.resetBotVisual()
                    if self.selected_index == "Holding":
                        self.generateHoldingItem()
                    self2.kill()
                    return consumed_event

                return super().process_event(event)

            def kill(self2):
                super().kill()
                self.removeColourPicker()

        self.picker = ColourPicker(
            rect=pygame.Rect(self._size[0] * 0.15, self._size[1] * 0.15, self._size[0] * 0.7, self._size[1] * 0.7),
            manager=self,
            initial_colour=pygame.Color(start_colour),
            window_title=title,
            object_id=pygame_gui.core.ObjectID("colour_dialog"),
        )

    def addPortPicker(self, on_close):

        self.mode = self.MODE_PORT_DIALOG

        device_type = (
            self.current_holding_kwargs["name"]
            if self.selected_index == "Holding"
            else list(self.current_devices[self.selected_index[1]].keys())[0]
        )
        if device_type in ["UltrasonicSensor", "ColorSensor", "InfraredSensor", "CompassSensor"]:
            ports = ["in1", "in2", "in3", "in4"]
        elif device_type in ["Button"]:
            ports = ["up", "down", "left", "right", "enter", "backspace"]
        else:
            ports = ["outA", "outB", "outC", "outD"]

        class PortPicker(pygame_gui.elements.UIWindow):
            def kill(self2):
                super().kill()
                self.removePortPicker()

            def process_event(self2, event: pygame.event.Event):
                if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                    for port in ports:
                        if f"{port}_button" in event.ui_object_id:
                            on_close(port)
                            self2.kill()
                    if "custom_accept" in event.ui_object_id:
                        on_close(self.custom_port_entry.get_text())
                        self2.kill()
                return super().process_event(event)

        picker_size = (self._size[0] * 0.7, self._size[1] * 0.7)

        self.picker = PortPicker(
            rect=pygame.Rect(self._size[0] * 0.15, self._size[1] * 0.15, *picker_size),
            manager=self,
            window_display_title="Pick Port",
            object_id=pygame_gui.core.ObjectID("port_dialog"),
        )

        for i, port in enumerate(ports):
            but_rect = (
                pygame.Rect(
                    80 + ((i % 2)) * ((picker_size[0] - 120) / 2 + 30),
                    50 + ((picker_size[1] - 160) / 3 + 20) * (i // 2),
                    (picker_size[0] - 150) / 3,
                    (picker_size[1] - 160) / 3 - 30,
                )
                if len(ports) == 4
                else pygame.Rect(
                    30 + ((i % 3) + (i // 6)) * ((picker_size[0] - 150) / 3 + 30),
                    20 + ((picker_size[1] - 160) / 3 + 20) * (i // 3),
                    (picker_size[0] - 150) / 3,
                    (picker_size[1] - 160) / 3 - 30,
                )
            )
            setattr(
                self,
                f"{port}_button",
                pygame_gui.elements.UIButton(
                    relative_rect=but_rect,
                    text=port,
                    manager=self,
                    container=self.picker,
                    object_id=pygame_gui.core.ObjectID(f"{port}_button", "any_button"),
                ),
            )
        self.custom_port_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(80, picker_size[1] - 130, (picker_size[0] - 150) / 3 - 50, self.side_width / 3),
            text="Custom Port",
            manager=self,
            container=self.picker,
            object_id=pygame_gui.core.ObjectID("custom-port-label", "bot_edit_label"),
        )
        self.custom_port_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(
                80 + (picker_size[0] - 150) / 3, picker_size[1] - 125, (picker_size[0] - 150) / 3, self.side_width / 3
            ),
            manager=self,
            container=self.picker,
            object_id=pygame_gui.core.ObjectID("port-entry", "num_entry"),
        )
        self.custom_port_accept = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                80 + 2 * (picker_size[0] - 150) / 3 + 50,
                picker_size[1] - 130,
                (picker_size[0] - 150) / 3 - 100,
                self.side_width / 3,
            ),
            text="Ok",
            manager=self,
            container=self.picker,
            object_id=pygame_gui.core.ObjectID(f"custom_accept", "any_button"),
        )

    def addDevicePicker(self):

        self.mode = self.MODE_DEVICE_DIALOG

        device_data = [
            ("Ultrasonic", "ultrasonic", "ultrasonic", "UltrasonicSensor"),
            ("Colour", "colour", "colour", "ColorSensor"),
            ("Infrared", "infrared", "infrared", "InfraredSensor"),
            ("Compass", "compass", "compass", "CompassSensor"),
            ("Large Motor", "large_motor", "motor", "LargeMotor"),
            ("Medium Motor", "medium_motor", "motor", "MediumMotor"),
            ("Button", "button", "button", "Button"),
        ]

        class DevicePicker(pygame_gui.elements.UIWindow):
            def kill(self2):
                super().kill()
                self.removeDevicePicker()

            def process_event(self2, event: pygame.event.Event):
                if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                    for device in device_data:
                        if f"{device[1]}_button" in event.ui_object_id:
                            # Select that device.
                            self.current_holding_kwargs = {
                                "type": "device",
                                "name": device[3],
                                "port": "in1" if device[2] != "motor" else "outA",
                                "rotation": 0,
                            }
                            self.selected_type = self.SELECTED_DEVICE
                            self.selected_index = "Holding"
                            self.generateHoldingItem()
                            self2.kill()
                return super().process_event(event)

        picker_size = (self._size[0] * 0.7, self._size[1] * 0.7)

        self.picker = DevicePicker(
            rect=pygame.Rect(self._size[0] * 0.15, self._size[1] * 0.15, *picker_size),
            manager=self,
            window_display_title="Pick Device",
            object_id=pygame_gui.core.ObjectID("device_dialog"),
        )

        for i, (show, device, file, sensor_name) in enumerate(device_data):
            setattr(
                self,
                f"{device}_label",
                pygame_gui.elements.UILabel(
                    relative_rect=pygame.Rect(
                        30 + ((i % 3) + (i // 6)) * ((picker_size[0] - 150) / 3 + 30),
                        20 + ((picker_size[1] - 160) / 3 + 20) * (i // 3),
                        (picker_size[0] - 150) / 3,
                        25,
                    ),
                    text=show,
                    manager=self,
                    container=self.picker,
                    object_id=pygame_gui.core.ObjectID(f"{device}_label", "device_label"),
                ),
            )
            img = pygame.image.load(find_abs(f"ui/devices/{file}.png", asset_locations()))
            img.set_colorkey((0, 255, 0))
            but_rect = pygame.Rect(
                30 + ((i % 3) + (i // 6)) * ((picker_size[0] - 150) / 3 + 30),
                50 + ((picker_size[1] - 160) / 3 + 20) * (i // 3),
                (picker_size[0] - 150) / 3,
                (picker_size[1] - 160) / 3 - 30,
            )
            setattr(
                self,
                f"{device}_img",
                pygame_gui.elements.UIImage(
                    relative_rect=but_rect,
                    image_surface=img,
                    manager=self,
                    container=self.picker,
                    object_id=pygame_gui.core.ObjectID(f"{device}_img", "device_img"),
                ),
            )
            setattr(
                self,
                f"{device}_button",
                pygame_gui.elements.UIButton(
                    relative_rect=but_rect,
                    text="",
                    manager=self,
                    container=self.picker,
                    object_id=pygame_gui.core.ObjectID(f"{device}_button", "invis_button"),
                ),
            )

    def addBaseplatePicker(self):
        self.mode = self.MODE_BASEPLATE_DIALOG

        baseplate_options = [
            (
                "Circle",
                {
                    "name": "Circle",
                    "radius": 8,
                    "fill": "#878E88",
                    "stroke_width": 0.1,
                    "stroke": "#ffffff",
                    "zPos": self.BASE_ZPOS,
                },
                "circle",
                self.SELECTED_CIRCLE,
            ),
            (
                "Rectangle",
                {
                    "name": "Rectangle",
                    "fill": "#878E88",
                    "stroke_width": 0.1,
                    "stroke": "#ffffff",
                    "zPos": self.BASE_ZPOS,
                    "width": 8,
                    "height": 4,
                },
                "rectangle",
                self.SELECTED_RECTANGLE,
            ),
            (
                "Polygon",
                {
                    "name": "Polygon",
                    "fill": "#878E88",
                    "stroke_width": 0.1,
                    "stroke": "#ffffff",
                    "verts": [
                        [8 * np.sin(0), 8 * np.cos(0)],
                        [8 * np.sin(2 * np.pi / 5), 8 * np.cos(2 * np.pi / 5)],
                        [8 * np.sin(4 * np.pi / 5), 8 * np.cos(4 * np.pi / 5)],
                        [8 * np.sin(6 * np.pi / 5), 8 * np.cos(6 * np.pi / 5)],
                        [8 * np.sin(8 * np.pi / 5), 8 * np.cos(8 * np.pi / 5)],
                    ],
                    "zPos": self.BASE_ZPOS,
                },
                "polygon",
                self.SELECTED_POLYGON,
            ),
        ]

        class BaseplatePicker(pygame_gui.elements.UIWindow):
            def kill(self2):
                if self.selected_index != "Baseplate" and self.mode == self.MODE_BASEPLATE_DIALOG:
                    # We cannot close this until a baseplate has been selected.
                    return
                super().kill()
                self.removeBaseplatePicker()

            def process_event(self2, event: pygame.event.Event):
                if event.type == pygame.MOUSEWHEEL:
                    self.scroll_container.vert_scroll_bar.scroll_position -= event.y * 10
                    self.scroll_container.vert_scroll_bar.scroll_position = min(
                        max(
                            self.scroll_container.vert_scroll_bar.scroll_position,
                            self.scroll_container.vert_scroll_bar.top_limit,
                        ),
                        self.scroll_container.vert_scroll_bar.bottom_limit
                        - self.scroll_container.vert_scroll_bar.sliding_button.relative_rect.height,
                    )
                    x_pos = 0
                    y_pos = (
                        self.scroll_container.vert_scroll_bar.scroll_position
                        + self.scroll_container.vert_scroll_bar.arrow_button_height
                    )
                    self.scroll_container.vert_scroll_bar.sliding_button.set_relative_position((x_pos, y_pos))
                    self.scroll_container.vert_scroll_bar.start_percentage = (
                        self.scroll_container.vert_scroll_bar.scroll_position
                        / self.scroll_container.vert_scroll_bar.scrollable_height
                    )
                    self.scroll_container.vert_scroll_bar.has_moved_recently = True
                if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                    for show, obj, name, select in baseplate_options:
                        if f"{name}_button" in event.ui_object_id:
                            # Select that baseplate
                            self.selected_type = select
                            self.selected_index = "Baseplate"
                            self.current_object = {
                                "type": "object",
                                "physics": True,
                                "visual": obj,
                                "mass": 5,
                                "restitution": 0.2,
                                "friction": 0.8,
                                "children": [],
                                "key": "phys_obj",
                            }
                            self.updateZpos()
                            self2.kill()
                            return True
                return super().process_event(event)

        picker_size = (self._size[0] * 0.7, self._size[1] * 0.7)

        self.picker = BaseplatePicker(
            rect=pygame.Rect(self._size[0] * 0.15, self._size[1] * 0.15, *picker_size),
            manager=self,
            window_display_title="Pick Device",
            object_id=pygame_gui.core.ObjectID("device_dialog"),
        )

        self.scroll_container = pygame_gui.elements.UIScrollingContainer(
            relative_rect=pygame.Rect(20, 10, picker_size[0] - 60, picker_size[1] - 80),
            container=self.picker,
            manager=self,
        )

        self.text = pygame_gui.elements.UITextBox(
            html_text="""\
All bots require a <font color="#06d6a0">baseplate</font>.<br><br>\
All other objects are placed on this baseplate. After creating it, the baseplate type <font color="#e63946">cannot</font> be changed. (Although it's characteristics can).\
""",
            relative_rect=pygame.Rect(0, 0, picker_size[0] - 80, 140),
            manager=self,
            container=self.scroll_container,
            object_id=pygame_gui.core.ObjectID("text_dialog_baseplate", "text_dialog"),
        )

        for i, (show, obj, name, select) in enumerate(baseplate_options):
            setattr(
                self,
                f"{name}_label",
                pygame_gui.elements.UILabel(
                    relative_rect=pygame.Rect(
                        (i % 2) * ((picker_size[0] - 140) / 2 + 30),
                        140 + (picker_size[1] - 250 + 20) * (i // 2),
                        (picker_size[0] - 140) / 2,
                        25,
                    ),
                    text=show,
                    manager=self,
                    container=self.scroll_container,
                    object_id=pygame_gui.core.ObjectID(f"{name}_label", "baseplate_label"),
                ),
            )
            self.scroll_container.set_scrollable_area_dimensions(
                (picker_size[0] - 80, 150 + (picker_size[1] - 230) * ((len(baseplate_options) + 1) // 2))
            )
            img = pygame.image.load(find_abs(f"ui/icon_{name}.png", allowed_areas=asset_locations()))
            img.set_colorkey((0, 255, 0))
            but_rect = pygame.Rect(
                (i % 2) * ((picker_size[0] - 140) / 2 + 30),
                170 + (picker_size[1] - 250 + 20) * (i // 2),
                (picker_size[0] - 140) / 2,
                picker_size[1] - 250 - 30,
            )
            setattr(
                self,
                f"{name}_button",
                pygame_gui.elements.UIButton(
                    relative_rect=but_rect,
                    text="",
                    manager=self,
                    container=self.scroll_container,
                    object_id=pygame_gui.core.ObjectID(f"{name}_button", "invis_button"),
                ),
            )
            # So it isn't a square.
            if name == "rectangle":
                but_rect.height /= 2
                but_rect.top += but_rect.height / 2
            setattr(
                self,
                f"{name}_img",
                pygame_gui.elements.UIImage(
                    relative_rect=but_rect,
                    image_surface=img,
                    manager=self,
                    container=self.scroll_container,
                    object_id=pygame_gui.core.ObjectID(f"{name}_img", "baseplate_img"),
                ),
            )

    def removeBaseplatePicker(self):
        try:
            self.mode = self.MODE_NORMAL
            self.drawOptions()
            self.resetBotVisual()
        except:
            pass

    def removeDevicePicker(self):
        try:
            self.mode = self.MODE_NORMAL
            self.drawOptions()
        except:
            pass

    def removePortPicker(self):
        try:
            self.mode = self.MODE_NORMAL
            self.drawOptions()
        except:
            pass

    def removeColourPicker(self):
        try:
            self.mode = self.MODE_NORMAL
            self.drawOptions()
        except:
            pass

    def removeNamePicker(self):
        try:
            self.mode = self.MODE_NORMAL
            self.drawOptions()
        except:
            pass

    def removeCodePicker(self):
        try:
            self.mode = self.MODE_NORMAL
            self.drawOptions()
        except:
            pass

    def removeColourOptions(self):
        try:
            self.fill_label.kill()
            self.fill_img.kill()
            self.stroke_label.kill()
            self.stroke_img.kill()
            self.removeButtonEvent("stroke_colour-button")
            self.removeButtonEvent("fill_colour-button")
        except:
            pass

    def removeCircleOptions(self):
        try:
            self.radius_label.kill()
            self.radius_entry.kill()
            self.stroke_num_label.kill()
            self.stroke_entry.kill()
        except:
            pass

    def removeRectangleOptions(self):
        try:
            self.width_label.kill()
            self.width_entry.kill()
            self.height_label.kill()
            self.height_entry.kill()
            self.rotation_label.kill()
            self.rotation_label.kill()
            self.stroke_num_label.kill()
            self.stroke_entry.kill()
        except:
            pass

    def removePolygonOptions(self):
        try:
            self.sides_label.kill()
            self.sides_entry.kill()
            self.size_label.kill()
            self.size_entry.kill()
            self.stroke_num_label.kill()
            self.stroke_entry.kill()
            self.rotation_label.kill()
            self.rotation_entry.kill()
        except:
            pass

    def removeDeviceOptions(self):
        try:
            self.rotation_label.kill()
            self.rotation_entry.kill()
            self.port_label.kill()
            self.port_entry.kill()
        except:
            pass

    def clearOptions(self):
        try:
            self.remove_button.kill()
            self.removeButtonEvent("remove_button")
        except:
            pass
        self.removeColourOptions()
        self.removeCircleOptions()
        self.removeRectangleOptions()
        self.removePolygonOptions()
        self.removeDeviceOptions()

    def clearObjects(self):
        super().clearObjects()
        self.clearOptions()

    def updateAttribute(self, attr, entry, conv, generate, old_v=None):
        if old_v is None:
            old_v = self.getSelectedAttribute(attr)
        try:
            new_v = conv(entry.text)
            if old_v != new_v:
                self.setSelectedAttribute(attr, new_v)
                generate()
        except:
            self.setSelectedAttribute(attr, old_v)

    def draw_ui(self, window_surface: pygame.surface.Surface):
        def bounded_gen(conv, positive=True):
            def func(x):
                res = conv(x)
                if res < 0 or res < 1e-4 and positive:
                    raise ValueError("Expected a positive value!")
                if res > 1000:
                    raise ValueError("Value is too big!")
                return res

            return func

        if self.selected_index is not None:
            if self.selected_index == "Holding":
                generate = lambda: self.generateHoldingItem()
            else:
                generate = lambda: self.resetBotVisual()
            if self.mode == self.MODE_NORMAL and self.selected_type == self.SELECTED_CIRCLE:
                self.updateAttribute("radius", self.radius_entry, bounded_gen(float), generate)
                self.updateAttribute("stroke_width", self.stroke_entry, bounded_gen(float, positive=False), generate)
            if self.mode == self.MODE_NORMAL and self.selected_type == self.SELECTED_RECTANGLE:
                self.updateAttribute("width", self.width_entry, bounded_gen(float), generate)
                self.updateAttribute("height", self.height_entry, bounded_gen(float), generate)
                self.updateAttribute("stroke_width", self.stroke_entry, bounded_gen(float, positive=False), generate)

                # Rotation is tricky. Do this explicitly.
                cur_rotation = self.getSelectedAttribute("rotation", 0, visual=False)
                cur_rotation *= 180 / np.pi
                try:
                    new_rot = float(self.rotation_entry.text)
                    self.setSelectedAttribute("rotation", new_rot * np.pi / 180, visual=False)
                    generate()
                except:
                    pass
            if self.mode == self.MODE_NORMAL and self.selected_type == self.SELECTED_POLYGON:
                self.updateAttribute("stroke_width", self.stroke_entry, bounded_gen(float, positive=False), generate)
                # Polygon drawing isn't as simple, do this explicitly.
                old_sides = len(self.getSelectedAttribute("verts"))
                old_size = np.linalg.norm(self.getSelectedAttribute("verts")[0], 2)
                cur_rotation = (
                    np.arctan2(self.getSelectedAttribute("verts")[0][1], self.getSelectedAttribute("verts")[0][0])
                    - np.pi / 2
                )
                while cur_rotation < 0:
                    cur_rotation += np.pi
                cur_rotation *= 180 / np.pi
                try:
                    new_sides = int(self.sides_entry.text)
                    if new_sides > 100:
                        raise ValueError("Too many sides!")
                    new_size = float(self.size_entry.text)
                    new_rot = float(self.rotation_entry.text)
                    assert new_sides > 2
                    if old_sides != new_sides or old_size != new_size or new_rot != cur_rotation:
                        self.setSelectedAttribute(
                            "verts",
                            [
                                [
                                    new_size * np.sin(i * 2 * np.pi / new_sides + new_rot * np.pi / 180),
                                    new_size * np.cos(i * 2 * np.pi / new_sides + new_rot * np.pi / 180),
                                ]
                                for i in range(new_sides)
                            ],
                        )
                    generate()
                except:
                    pass
            if self.mode == self.MODE_NORMAL and self.selected_type == self.SELECTED_DEVICE:
                self.updateAttribute("rotation", self.rotation_entry, float, generate)
            if self.mode == self.MODE_NORMAL:
                try:
                    self.grid_size = float(self.grid_size_entry.text)
                except:
                    pass
            if self.dragging:
                if not isinstance(self.selected_index, str):
                    new_pos = [
                        self.current_mpos[0] + self.offset_position[0],
                        self.current_mpos[1] + self.offset_position[1],
                    ]
                    # We need to relock position.
                    if self.lock_grid:
                        new_pos = [
                            ((new_pos[0] + self.grid_size / 2) // self.grid_size) * self.grid_size,
                            ((new_pos[1] + self.grid_size / 2) // self.grid_size) * self.grid_size,
                        ]
                    if self.selected_index[0] == "Children":
                        old_pos = self.current_object["children"][self.selected_index[1]]["position"]
                        if old_pos[0] != new_pos[0] or old_pos[1] != new_pos[1]:
                            self.current_object["children"][self.selected_index[1]]["position"] = [
                                float(v) for v in new_pos
                            ]
                            generate()
                    elif self.selected_index[0] == "Devices":
                        old_pos = self.getSelectedAttribute("position", [0, 0])
                        if old_pos[0] != new_pos[0] or old_pos[1] != new_pos[1]:
                            self.setSelectedAttribute("position", [float(v) for v in new_pos])
                            generate()

        ScreenObjectManager.instance.applyToScreen(to_screen=self.bot_screen)
        ScreenObjectManager.instance.screen.blit(self.bot_screen, pygame.Rect(self.side_width - 5, 0, *self.surf_size))
        super().draw_ui(window_surface)

    def changeMode(self, value):
        # Remove/Add dialog components if necessary.
        self.mode = value

    def onPop(self):
        from ev3sim.simulation.loader import ScriptLoader
        from ev3sim.visual.manager import ScreenObjectManager
        from ev3sim.simulation.world import World

        ScreenObjectManager.instance.resetVisualElements()
        World.instance.resetWorld()
        ScriptLoader.instance.reset()
