import os
import shutil

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.video import Video
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView


Window.clearcolor = (0.04, 0.04, 0.09, 1)

PURPLE = (0.48, 0.25, 0.95, 1)
DARK = (0.10, 0.10, 0.17, 1)

SAVE_DIR = "/storage/emulated/0/Pictures/PhotoFrame"


class PhotoFrameApp(App):

    def build(self):

        self.title = "Photocraft"

        self.frames = []
        self.selected = set()
        self.buttons = []
        self.video_duration = 0
        self.extract_time = 0
        self.extracting = False

        root = BoxLayout(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(9)
        )

        # HEADER

        root.add_widget(Label(
            text="[b]PHOTOCRAFT[/b]",
            markup=True,
            font_size="26sp",
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(45)
        ))

        root.add_widget(Label(
            text="VIDEO TO IMAGE EXTRACTOR",
            color=(0.7, 0.6, 1, 1),
            size_hint_y=None,
            height=dp(25)
        ))

        # VIDEO PREVIEW

        self.video = Video(
            source="",
            state="stop",
            options={"eos": "stop"},
            allow_stretch=True,
            keep_ratio=True,
            size_hint_y=None,
            height=dp(190)
        )

        root.add_widget(self.video)

        # VIDEO BUTTONS

        controls = BoxLayout(
            size_hint_y=None,
            height=dp(48),
            spacing=dp(7)
        )

        upload = self.make_button("UPLOAD VIDEO")
        upload.bind(on_press=self.open_picker)

        play = self.make_button("PLAY")
        play.bind(on_press=self.play_video)

        pause = self.make_button("PAUSE")
        pause.bind(on_press=self.pause_video)

        controls.add_widget(upload)
        controls.add_widget(play)
        controls.add_widget(pause)

        root.add_widget(controls)

        # EXTRACT BUTTON

        extract = self.make_button(
            "EXTRACT FRAMES",
            PURPLE
        )

        extract.bind(on_press=self.start_extraction)

        root.add_widget(extract)

        # STATUS

        self.status = Label(
            text="Choose a video to start",
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(35)
        )

        root.add_widget(self.status)

        # PHOTO GRID

        scroll = ScrollView()

        self.grid = GridLayout(
            cols=3,
            spacing=dp(7),
            padding=dp(4),
            size_hint_y=None
        )

        self.grid.bind(
            minimum_height=self.grid.setter("height")
        )

        scroll.add_widget(self.grid)
        root.add_widget(scroll)

        # BOTTOM BUTTONS

        bottom = BoxLayout(
            size_hint_y=None,
            height=dp(50),
            spacing=dp(7)
        )

        select = self.make_button("SELECT ALL")
        select.bind(on_press=self.select_all)

        save = self.make_button("SAVE PHOTOS", PURPLE)
        save.bind(on_press=self.save_selected)

        bottom.add_widget(select)
        bottom.add_widget(save)

        root.add_widget(bottom)

        root.add_widget(Label(
            text="Developed by MG Shankar Tech",
            color=(0.6, 0.6, 0.7, 1),
            font_size="11sp",
            size_hint_y=None,
            height=dp(22)
        ))

        return root

    # BUTTON DESIGN

    def make_button(self, text, color=DARK):

        return Button(
            text=text,
            background_normal="",
            background_color=color,
            color=(1, 1, 1, 1),
            bold=True,
            font_size="12sp"
        )

    # VIDEO PICKER

    def open_picker(self, instance):

        chooser = FileChooserListView(
            path="/storage/emulated/0",
            filters=[
                "*.mp4",
                "*.mkv",
                "*.avi",
                "*.mov",
                "*.3gp"
            ]
        )

        layout = BoxLayout(
            orientation="vertical",
            spacing=dp(7),
            padding=dp(8)
        )

        layout.add_widget(chooser)

        buttons = BoxLayout(
            size_hint_y=None,
            height=dp(45),
            spacing=dp(7)
        )

        choose = self.make_button("OPEN", PURPLE)
        cancel = self.make_button("CANCEL")

        buttons.add_widget(choose)
        buttons.add_widget(cancel)

        layout.add_widget(buttons)

        popup = Popup(
            title="Choose Video",
            content=layout,
            size_hint=(0.95, 0.9)
        )

        choose.bind(
            on_press=lambda x: self.load_video(
                chooser, popup
            )
        )

        cancel.bind(on_press=popup.dismiss)

        popup.open()

    # LOAD VIDEO

    def load_video(self, chooser, popup):

        if not chooser.selection:
            self.status.text = "Select a video first"
            return

        path = chooser.selection[0]

        popup.dismiss()

        self.video.state = "stop"
        self.video.source = path
        self.video.seek(0)

        self.frames.clear()
        self.selected.clear()
        self.grid.clear_widgets()
        self.buttons.clear()

        self.status.text = "Loading video..."

        Clock.schedule_once(
            self.check_video, 3
        )

    def check_video(self, dt):

        duration = self.video.duration

        if duration and duration > 0:

            self.video_duration = duration

            self.status.text = (
                f"Video Loaded | {duration:.1f} Seconds"
            )

        else:

            self.status.text = (
                "Video loading failed. Check video format."
            )

    # PLAY

    def play_video(self, instance):

        self.video.state = "play"

    # PAUSE

    def pause_video(self, instance):

        self.video.state = "pause"

    # START EXTRACTION

    def start_extraction(self, instance):

        if not self.video.source:
            self.status.text = "Upload a video first"
            return

        if not self.video.duration:
            self.status.text = "Video is not ready"
            return

        self.video.state = "pause"

        self.video_duration = self.video.duration
        self.extract_time = 0
        self.frames.clear()
        self.selected.clear()
        self.grid.clear_widgets()
        self.buttons.clear()

        self.extracting = True

        self.status.text = "Extracting frames..."

        self.capture_next(0)

    # CAPTURE FRAME

    def capture_next(self, dt):

        if not self.extracting:
            return

        if self.extract_time >= self.video_duration:

            self.finish_extraction()
            return

        self.video.seek(self.extract_time)

        Clock.schedule_once(
            self.save_texture,
            0.7
        )

    def save_texture(self, dt):

        if not self.extracting:
            return

        texture = self.video.texture

        if texture:

            try:

                folder = os.path.join(
                    self.user_data_dir,
                    "frames"
                )

                os.makedirs(
                    folder,
                    exist_ok=True
                )

                filename = os.path.join(
                    folder,
                    f"frame_{self.extract_time}.png"
                )

                texture.save(
                    filename,
                    flipped=True,
                    fmt="png"
                )

                self.frames.append({
                    "path": filename,
                    "time": self.extract_time
                })

            except Exception as e:

                self.status.text = str(e)
                self.finish_extraction()
                return

        self.status.text = (
            f"Extracting: {self.extract_time}s"
        )

        self.extract_time += 1

        Clock.schedule_once(
            self.capture_next,
            0.2
        )

    # FINISH

    def finish_extraction(self):

        self.extracting = False

        self.video.state = "pause"

        self.show_frames()

        self.status.text = (
            f"Extraction complete: {len(self.frames)} frames"
        )

    # DISPLAY PHOTOS

    def show_frames(self):

        self.grid.clear_widgets()
        self.buttons.clear()

        for index, frame in enumerate(self.frames):

            box = BoxLayout(
                orientation="vertical",
                size_hint_y=None,
                height=dp(140),
                spacing=dp(3)
            )

            image = Image(
                source=frame["path"],
                fit_mode="contain"
            )

            button = Button(
                text=f"{frame['time']}s",
                size_hint_y=None,
                height=dp(32),
                background_normal="",
                background_color=DARK
            )

            button.bind(
                on_press=lambda btn, i=index:
                self.toggle_select(i)
            )

            box.add_widget(image)
            box.add_widget(button)

            self.grid.add_widget(box)

            self.buttons.append(button)

    # SELECT

    def toggle_select(self, index):

        if index in self.selected:
            self.selected.remove(index)
        else:
            self.selected.add(index)

        self.update_selection()

    # SELECT ALL

    def select_all(self, instance):

        if len(self.selected) == len(self.frames):
            self.selected.clear()
        else:
            self.selected = set(
                range(len(self.frames))
            )

        self.update_selection()

    # UPDATE UI

    def update_selection(self):

        for i, button in enumerate(self.buttons):

            if i in self.selected:

                button.text = "✓ SELECTED"
                button.background_color = PURPLE

            else:

                button.text = (
                    f"{self.frames[i]['time']}s"
                )

                button.background_color = DARK

        self.status.text = (
            f"{len(self.selected)} Selected"
        )

    # SAVE PHOTOS

    def save_selected(self, instance):

        if not self.selected:

            self.status.text = "Select photos first"
            return

        try:

            os.makedirs(
                SAVE_DIR,
                exist_ok=True
            )

            count = 0

            for index in sorted(self.selected):

                frame = self.frames[index]

                filename = (
                    f"PhotoFrame_{frame['time']}s.png"
                )

                destination = os.path.join(
                    SAVE_DIR,
                    filename
                )

                shutil.copy2(
                    frame["path"],
                    destination
                )

                count += 1

            self.status.text = (
                f"{count} Photos Saved Successfully!"
            )

        except Exception as e:

            self.status.text = (
                f"Save Error: {e}"
            )


if __name__ == "__main__":
    PhotoFrameApp().run()
