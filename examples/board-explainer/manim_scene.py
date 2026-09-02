from pathlib import Path

from manim import (
    AnimationGroup,
    Create,
    FadeIn,
    FadeOut,
    Group,
    ImageMobject,
    LEFT,
    Line,
    Scene,
    Succession,
    Text,
    Transform,
    UP,
    VGroup,
    config,
)


config.pixel_width = 720
config.pixel_height = 1280
config.frame_width = 9
config.frame_height = 16
config.frame_rate = 30
config.background_color = "#0d0d0d"

HERE = Path(__file__).resolve().parent
BUILD_ROOT = HERE.parents[1] / "dist/examples/board-explainer"
BOARD_DIR = BUILD_ROOT / "board"
PREVIEW_DIR = BUILD_ROOT / "board-routing-disabled"
NARRATION = HERE / "dist/narration.wav"

WHITE = "#f2f2f2"
GRAY = "#9b9b9b"
GREEN = WHITE
FONT = "Geist"
MONO = "Geist Mono"


def txt(value: str, size=28, color=WHITE, weight="NORMAL"):
    return Text(value, font=FONT, font_size=size, color=color, weight=weight)


def raster(path: Path, width=8.45):
    image = ImageMobject(str(path))
    image.width = width
    return image


def section(index: str, title: str, detail: str):
    number = Text(f"{index} / BOARD", font=MONO, font_size=16, color=GRAY).move_to([-3.2, 6.65, 0])
    number.align_to([-3.55, 6.65, 0], LEFT)
    name = txt(title, 40, WHITE, "SEMIBOLD").move_to([-1.2, 5.95, 0])
    name.align_to([-3.55, 5.95, 0], LEFT)
    note = txt(detail, 18, GRAY).move_to([2.9, 6.65, 0])
    note.align_to([3.55, 6.65, 0], LEFT).shift(LEFT * note.width)
    return VGroup(number, name, note)


def caption(value: str):
    copy = txt(value, 25, WHITE)
    if copy.width > 7.2:
        words = value.split()
        midpoint = len(words) // 2
        value = " ".join(words[:midpoint]) + "\n" + " ".join(words[midpoint:])
        copy = txt(value, 25, WHITE)
    copy.align_to([-3.55, -5.55, 0], LEFT).move_to([-3.55 + copy.width / 2, -5.55, 0])
    return VGroup(copy)


def measurement(start, end, value, label_offset):
    line = Line(start, end, color=GREEN, stroke_width=2)
    line.add_tip(tip_length=0.16).add_tip(at_start=True, tip_length=0.16)
    value_text = txt(value, 22, GREEN).move_to(line.get_center() + label_offset)
    return VGroup(line, value_text)


def text_cut(current, value: str):
    following = caption(value)
    return Succession(FadeOut(current), FadeIn(following)), following


class BoardExplainer(Scene):
    def construct(self):
        self.add_sound(str(NARRATION))

        intro_section = section("00", "<board />", "root PCB element")
        hero = raster(BOARD_DIR / "3d.png", 8.25).move_to([0, 0.55, 0])
        origin = Text("40 × 30 mm   ·   4 layers", font=MONO, font_size=17, color=GRAY).move_to([0, -3.82, 0])
        current_caption = caption("In tscircuit, the board element is the")
        self.play(
            FadeIn(intro_section, shift=UP * 0.1),
            FadeIn(hero, shift=UP * 0.18),
            FadeIn(origin),
            FadeIn(current_caption),
            run_time=0.6,
        )
        self.wait(1.6)

        cap_change, current_caption = text_cut(current_caption, "root of your printed circuit board. Think")
        self.play(cap_change, run_time=0.16)
        self.wait(2.24)

        root_section = section("01", "root container", "components + traces")
        cap_change, current_caption = text_cut(current_caption, "of it like the body element in")
        self.play(
            Succession(FadeOut(intro_section), FadeIn(root_section)),
            hero.animate.scale(1.08),
            cap_change,
            run_time=0.42,
        )
        intro_section = root_section
        self.wait(1.21)

        pcb = raster(BOARD_DIR / "pcb.png", 8.4).move_to([0, 0.25, 0])
        topology = txt("R1  ·  LED1  ·  C1  ·  U1  /  3 nets", 20, GRAY).move_to([0, -3.83, 0])
        cap_change, current_caption = text_cut(current_caption, "HTML: components and traces live inside it.")
        self.play(
            FadeOut(hero),
            FadeIn(pcb),
            FadeOut(origin),
            FadeIn(topology),
            cap_change,
            run_time=0.42,
        )
        self.wait(2.114)

        size_section = section("02", "physical size", "millimetres")
        width_mark = measurement([-3.35, 3.92, 0], [3.35, 3.92, 0], "40 mm", UP * 0.25)
        height_mark = measurement([-3.62, 3.4, 0], [-3.62, -2.45, 0], "30 mm", LEFT * 0.24)
        height_mark[1].rotate(1.5708)
        cap_change, current_caption = text_cut(current_caption, "Width and height define the physical board")
        self.play(
            Succession(FadeOut(intro_section), FadeIn(size_section)),
            FadeOut(topology),
            Create(width_mark[0]),
            FadeIn(width_mark[1]),
            Create(height_mark[0]),
            FadeIn(height_mark[1]),
            cap_change,
            run_time=0.46,
        )
        intro_section = size_section
        self.wait(2.004)

        coords = txt("bounding box  /  40.00 × 30.00 mm", 20, GRAY).move_to([0, -3.83, 0])
        cap_change, current_caption = text_cut(current_caption, "size in millimeters. Set layers to four")
        self.play(
            FadeIn(coords),
            cap_change,
            run_time=0.2,
        )
        self.wait(2.067)

        layer_section = section("03", "copper stack", "layers = 4")
        board_3d = raster(BOARD_DIR / "3d.png", 8.2).move_to([0, 0.65, 0])
        layer_names = Text(
            "TOP   ·   INNER 1   ·   INNER 2   ·   BOTTOM",
            font=MONO,
            font_size=17,
            color=WHITE,
        ).move_to([0, -3.55, 0])
        cap_change, current_caption = text_cut(current_caption, "when you need two internal copper layers.")
        self.play(
            Succession(FadeOut(intro_section), FadeIn(layer_section)),
            FadeOut(Group(pcb, width_mark, height_mark, coords)),
            FadeIn(board_3d),
            FadeIn(layer_names),
            cap_change,
            run_time=0.48,
        )
        intro_section = layer_section
        self.wait(1.918)

        route_section = section("04", "routing state", "placement preview")
        preview = raster(PREVIEW_DIR / "pcb.png", 8.4).move_to([0, 0.25, 0])
        state = Text("routingDisabled = true", font=MONO, font_size=19, color=WHITE).move_to([0, -3.68, 0])
        cap_change, current_caption = text_cut(current_caption, "During placement, routingDisabled gives faster previews. Remove")
        self.play(
            Succession(FadeOut(intro_section), FadeIn(route_section)),
            FadeOut(Group(board_3d, layer_names)),
            FadeIn(preview),
            FadeIn(state),
            cap_change,
            run_time=0.48,
        )
        intro_section = route_section
        self.wait(3.42)

        final_route_section = section("05", "resolved traces", "routing enabled")
        final_board = raster(BOARD_DIR / "pcb.png", 8.4).move_to(preview)
        final_state = Text("routingDisabled = false", font=MONO, font_size=19, color=WHITE).move_to(state)
        cap_change, current_caption = text_cut(current_caption, "it before your final routing checks. You")
        self.play(
            Succession(FadeOut(intro_section), FadeIn(final_route_section)),
            FadeOut(preview),
            FadeIn(final_board),
            Transform(state, final_state),
            cap_change,
            run_time=0.3,
        )
        intro_section = final_route_section
        self.wait(2.03)

        material_section = section("06", "board controls", "fabrication data")
        finish = raster(BOARD_DIR / "3d.png", 8.15).move_to([0, 0.65, 0])
        specs = VGroup(
            txt("outline", 19, GRAY).move_to([-3.28, -2.85, 0]),
            txt("rectangle  /  r 2 mm", 19, WHITE).move_to([2.0, -2.85, 0]),
            txt("material", 19, GRAY).move_to([-3.28, -3.25, 0]),
            txt("FR4", 19, WHITE).move_to([2.0, -3.25, 0]),
            txt("thickness", 19, GRAY).move_to([-3.28, -3.65, 0]),
            txt("1.60 mm", 19, WHITE).move_to([2.0, -3.65, 0]),
            txt("solder mask", 19, GRAY).move_to([-3.28, -4.05, 0]),
            txt("green", 19, GREEN).move_to([2.0, -4.05, 0]),
        )
        for item in specs:
            if item.get_center()[0] < 0:
                item.align_to([-3.55, item.get_center()[1], 0], LEFT)
            else:
                item.align_to([3.55, item.get_center()[1], 0], LEFT).shift(LEFT * item.width)
        cap_change, current_caption = text_cut(current_caption, "can also control the outline, material, thickness,")
        self.play(
            Succession(FadeOut(intro_section), FadeIn(material_section)),
            FadeOut(Group(final_board, state)),
            FadeIn(finish),
            AnimationGroup(*[FadeIn(item) for item in specs], lag_ratio=0.05),
            cap_change,
            run_time=0.48,
        )
        intro_section = material_section
        self.wait(2.55)

        cap_change, current_caption = text_cut(current_caption, "solder mask, and manufacturing clearances.")
        self.play(cap_change, run_time=0.16)
        self.wait(2.44)
