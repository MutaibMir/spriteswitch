import os
import base64
import json
import re

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.core.window import Window

Window.clearcolor = (0.1, 0.1, 0.1, 1)

def sanitize_folder_name(name):
    return re.sub(r'[<>:"/\\|?*]', '', name).strip()

def convert_json_to_pngs(json_path):
    try:
        with open(json_path, "r") as f:
            data = json.load(f)

        textures = data.get("_textures", [])
        names = data.get("_textureNames", [])

        if len(textures) != len(names):
            return "Mismatch between _textures and _textureNames. Aborted."

        raw_folder_name = data.get("Name", "")
        folder_name = sanitize_folder_name(raw_folder_name)

        if not folder_name:
            folder_name = os.path.splitext(os.path.basename(json_path))[0]

        output_dir = os.path.join(os.path.dirname(json_path), folder_name)
        os.makedirs(output_dir, exist_ok=True)

        for name, b64_data in zip(names, textures):
            output_path = os.path.join(output_dir, f"{name}.png")
            with open(output_path, "wb") as out_file:
                out_file.write(base64.b64decode(b64_data))

        return f"Converted {len(names)} sprites to:\n{output_dir}"
    except Exception as e:
        return f"Error: {e}"

def update_json_with_pngs(png_folder, json_path):
    try:
        with open(json_path, "r") as f:
            data = json.load(f)

        textures = data.get("_textures", [])
        names = data.get("_textureNames", [])

        existing_names = set(names)
        added_count = 0

        for filename in os.listdir(png_folder):
            if filename.lower().endswith(".png"):
                name_without_ext = os.path.splitext(filename)[0]
                if name_without_ext in existing_names:
                    continue

                with open(os.path.join(png_folder, filename), "rb") as img_file:
                    encoded = base64.b64encode(img_file.read()).decode("utf-8")

                textures.append(encoded)
                names.append(name_without_ext)
                added_count += 1

        data["_textures"] = textures
        data["_textureNames"] = names

        with open(json_path, "w") as f:
            json.dump(data, f, indent=2)

        return added_count

    except Exception as e:
        return -1

class FolderChooserPopup(Popup):
    def __init__(self, on_select, **kwargs):
        super().__init__(**kwargs)
        self.title = "Select PNG Folder"
        self.size_hint = (0.9, 0.9)

        layout = BoxLayout(orientation='vertical')
        self.chooser = FileChooserListView(dirselect=True)
        layout.add_widget(self.chooser)

        btn_layout = BoxLayout(size_hint_y=None, height=50)
        select_btn = Button(text="Select")
        cancel_btn = Button(text="Cancel")

        select_btn.bind(on_release=lambda x: self.select_folder(on_select))
        cancel_btn.bind(on_release=self.dismiss)

        btn_layout.add_widget(select_btn)
        btn_layout.add_widget(cancel_btn)
        layout.add_widget(btn_layout)

        self.add_widget(layout)

    def select_folder(self, callback):
        if self.chooser.selection:
            callback(self.chooser.selection[0])
            self.dismiss()

class JSONChooserPopup(Popup):
    def __init__(self, on_select, **kwargs):
        super().__init__(**kwargs)
        self.title = "Select JSON File"
        self.size_hint = (0.9, 0.9)

        layout = BoxLayout(orientation='vertical')
        self.chooser = FileChooserListView(filters=["*.json"])
        layout.add_widget(self.chooser)

        btn_layout = BoxLayout(size_hint_y=None, height=50)
        select_btn = Button(text="Select")
        cancel_btn = Button(text="Cancel")

        select_btn.bind(on_release=lambda x: self.select_file(on_select))
        cancel_btn.bind(on_release=self.dismiss)

        btn_layout.add_widget(select_btn)
        btn_layout.add_widget(cancel_btn)
        layout.add_widget(btn_layout)

        self.add_widget(layout)

    def select_file(self, callback):
        if self.chooser.selection:
            callback(self.chooser.selection[0])
            self.dismiss()

class PNGToJSONScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = FloatLayout()
        center_box = BoxLayout(orientation='vertical', size_hint=(0.9, None), height=600, spacing=30, pos_hint={'center_x': 0.5, 'center_y': 0.5})

        self.label = Label(text="[b]PNG to JSON Sprite Sheet Updater[/b]", font_size=48, markup=True, size_hint_y=None, height=80)
        self.instructions = Label(text="Select a folder of PNGs and a JSON file to embed them into the sprite sheet.", font_size=32, size_hint_y=None, height=80)
        self.folder_button = Button(text="Choose PNG Folder", size_hint=(1, None), height=100, font_size=36)
        self.folder_button.bind(on_release=self.choose_folder)
        self.json_button = Button(text="Choose JSON File", size_hint=(1, None), height=100, font_size=36)
        self.json_button.bind(on_release=self.choose_json)
        self.status_label = Label(text="Waiting for selection...", font_size=32, size_hint_y=None, height=60)
        self.back_btn = Button(text="Back", size_hint=(1, None), height=60)
        self.back_btn.bind(on_release=self.go_back)

        center_box.add_widget(self.label)
        center_box.add_widget(self.instructions)
        center_box.add_widget(self.folder_button)
        center_box.add_widget(self.json_button)
        center_box.add_widget(self.status_label)
        center_box.add_widget(self.back_btn)

        layout.add_widget(center_box)
        self.add_widget(layout)

        self.selected_folder = None
        self.selected_json = None

    def choose_folder(self, instance):
        popup = FolderChooserPopup(on_select=self.set_folder)
        popup.open()

    def choose_json(self, instance):
        popup = JSONChooserPopup(on_select=self.set_json)
        popup.open()

    def set_folder(self, path):
        self.selected_folder = path
        self.try_update()

    def set_json(self, path):
        self.selected_json = path
        self.try_update()

    def try_update(self):
        if self.selected_folder and self.selected_json:
            added = update_json_with_pngs(self.selected_folder, self.selected_json)
            if added >= 0:
                self.status_label.text = f"Added {added} new PNG(s) to JSON."
            else:
                self.status_label.text = "Failed to update JSON."
            self.selected_folder = None
            self.selected_json = None

    def go_back(self, instance):
        self.manager.current = 'main'

class JSONToPNGScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = AnchorLayout(anchor_x='center', anchor_y='center')
        content = BoxLayout(orientation='vertical', spacing=20, padding=20, size_hint=(0.9, None))
        content.bind(minimum_height=content.setter('height'))

        self.title_label = Label(text="[b]Sprite JSON to PNG Extractor[/b]", markup=True, font_size='22sp', size_hint_y=None, height=40)
        self.desc_label = Label(text="Select a JSON sprite sheet file to extract PNG textures.", font_size='16sp', size_hint_y=None, height=30)
        self.status_label = Label(text="", font_size='14sp', size_hint_y=None, height=30)

        self.convert_button = Button(text="Choose JSON File", size_hint=(1, None), height=80, font_size='18sp')
        self.convert_button.bind(on_release=self.open_file_chooser)

        self.back_btn = Button(text="Back", size_hint=(1, None), height=60)
        self.back_btn.bind(on_release=self.go_back)

        content.add_widget(self.title_label)
        content.add_widget(self.desc_label)
        content.add_widget(self.convert_button)
        content.add_widget(self.status_label)
        content.add_widget(self.back_btn)

        layout.add_widget(content)
        self.add_widget(layout)

    def open_file_chooser(self, instance):
        popup = JSONChooserPopup(on_select=self.process_json)
        popup.open()

    def process_json(self, path):
        result = convert_json_to_pngs(path)
        self.status_label.text = result

    def go_back(self, instance):
        self.manager.current = 'main'

class MainMenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = AnchorLayout(anchor_x='center', anchor_y='center')
        button_box = BoxLayout(orientation='vertical', spacing=20, size_hint=(0.6, None), height=300)

        btn1 = Button(text="PNG to JSON", size_hint=(1, None), height=100, font_size=32)
        btn2 = Button(text="JSON to PNG", size_hint=(1, None), height=100, font_size=32)

        btn1.bind(on_release=self.goto_png_to_json)
        btn2.bind(on_release=self.goto_json_to_png)

        button_box.add_widget(btn1)
        button_box.add_widget(btn2)
        layout.add_widget(button_box)
        self.add_widget(layout)

    def goto_png_to_json(self, instance):
        self.manager.current = 'png_to_json'

    def goto_json_to_png(self, instance):
        self.manager.current = 'json_to_png'

class SpriteToolApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(MainMenuScreen(name='main'))
        sm.add_widget(PNGToJSONScreen(name='png_to_json'))
        sm.add_widget(JSONToPNGScreen(name='json_to_png'))
        return sm

if __name__ == '__main__':
    SpriteToolApp().run()
