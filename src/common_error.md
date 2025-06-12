# Common Manim Rendering Errors and Solutions

This document summarizes common errors encountered during Manim script development and rendering, along with their solutions.

## 1. API Mismatches (Version Conflicts)

These errors typically occur when using syntax or features from a newer Manim version with an older Manim installation (e.g., v0.19.0 or similar).

### 1.1. `Code` Class Argument Errors

*   **Core Problem:** Using modern keyword arguments for the `Code` class that are not recognized by older Manim versions.
*   **Specific Errors & Solutions:**
    *   **`TypeError: ... unexpected keyword argument 'code'`**
        *   **Reason:** Older versions expect the code content as a string via a different keyword.
        *   **Solution:** Change `code=` to `code_string=`.
    *   **`TypeError: ... unexpected keyword argument 'style'`, `'font'`, `'line_spacing'`**
        *   **Reason:** These keyword arguments for styling within the constructor are not supported in older versions.
        *   **Solution:** Remove these arguments from the `Code` constructor. Styling may need to be applied via other methods or may not be directly available.
    *   **`TypeError: ... unexpected keyword argument 'font_size'`**
        *   **Reason:** Font size cannot be set directly in the constructor in older versions.
        *   **Solution:** Remove `font_size=` from the constructor. Instead, apply `.scale()` to the `Code` object instance after its creation to adjust its size.

### 1.2. Unavailable Object Methods

*   **Core Problem:** Attempting to call a method on an object that does not exist in the installed Manim version.
*   **Specific Error & Solution:**
    *   **`AttributeError: 'Tex' object has no attribute 'add_shadow'`**
        *   **Reason:** The `.add_shadow()` helper method for creating a glow/shadow effect is not available in older versions.
        *   **Solution:** Manually replicate the "glow" effect:
            1.  Create a copy of the `Tex` object: `glow_effect = my_tex_object.copy()`.
            2.  Apply a wide, semi-transparent stroke to the copy: `glow_effect.set_stroke(color=YOUR_COLOR, width=YOUR_WIDTH, opacity=YOUR_OPACITY)`.
            3.  Group the original object and the glow effect: `VGroup(glow_effect, my_tex_object)` (ensure the glow is behind the original if necessary by order or `z_index`).

## 2. Import Errors for Specialized Classes

*   **Core Problem:** `ImportError` or `NameError` for classes not included in Manim's default `from manim import *` namespace.
*   **Specific Error & Solution (Example: `Blink` animation):**
    *   **Error:** `NameError: name 'Blink' is not defined`
    *   **Reason:** Specialized animations like `Blink` reside in submodules and are not automatically imported.
    *   **Solution:** Add an explicit import statement at the top of your script: `from manim.animation.indication import Blink`. (The exact submodule may vary for other classes).

## 3. Misunderstanding `self.add()` vs. `self.play()`

*   **Core Problem:** Confusing the purpose of `self.add()` (for static Mobjects) and `self.play()` (for dynamic Animations).
*   **Explanation:**
    *   `self.add(Mobject)`: Instantly places a static Manim object (e.g., `Circle`, `Text`, `Rectangle`) on the screen. It's an immediate action.
    *   `self.play(Animation)`: Executes a process that occurs over a duration (e.g., `Write`, `FadeIn`, `Create`, `Blink`).
*   **Specific Error & Solution (Example: Using `Blink`):**
    *   **Incorrect Usage:** `self.add(Blink(my_object))`
    *   **Reason:** This attempts to instantly "add" an animation process as if it were a static object, which is invalid.
    *   **Correct Implementation:**
        1.  Add the object to the scene if it's not already there: `self.add(my_object)` (if you want it to appear instantly before blinking) or `self.play(Create(my_object))` (if you want its creation animated).
        2.  Then, play the animation on the object: `self.play(Blink(my_object))`.

## 4. Camera Related Errors

### 4.1. Manipulating Camera Frame in Standard `Scene`

*   **Core Problem:** `AttributeError: 'Camera' object has no attribute 'frame'` (or similar errors related to camera frame manipulation).
*   **Reason:** This error occurs when trying to animate camera properties (zoom, pan, rotation) in a basic `Scene` class. The standard `Scene` has a static camera.
*   **Solution:** Change the scene's inheritance from `Scene` to `MovingCameraScene` (or `ThreeDScene` which inherits from `MovingCameraScene`). These classes are designed for camera manipulation and provide the necessary animatable camera frame.
    *   Example: `class MyScene(MovingCameraScene):`

### 4.2. Camera Animation Syntax

*   **Confusion Point:** Using `self.camera.animate.set_euler_angles(...).scale(...).move_to(...)` for chained camera transformations. While `.animate` is used for mobject properties, complex camera state changes are often better handled by `move_camera`.
*   **Clarification:**
    *   For combined camera transformations (simultaneously changing orientation like `phi`/`theta`, `zoom`, and `frame_center`), the `self.move_camera(...)` method is generally more robust and straightforward.
    *   Alternatively, individual camera attributes can be animated within `self.play()`:
        `self.play(self.camera.frame.animate.scale(0.5))`
        `self.play(self.camera.animate.set_phi(70 * DEGREES))`
        (Note: Direct animation of `phi`, `theta`, `zoom` on `self.camera.animate` might depend on Manim version; `self.camera.frame.animate` is often used for position/scale).

### 4.3. Camera Aspect Ratio and Frame Dimensions

*   **Best Practice:** Avoid manually setting `self.camera.frame_height` or `self.camera.frame_width` directly unless you have a very specific reason and understand the implications for aspect ratio and coordinate systems.
*   **Recommendation:** Rely on Manim's default frame setup or use command-line flags (e.g., for resolution, which implicitly handles frame dimensions) to maintain correct aspect ratios, especially for standard outputs like shorts or social media videos. Incorrect manual settings can lead to distorted visuals.

## 5. `NumberLine` Label Animation Issues

*   **Core Problem:** `IndexError: list index out of range` when attempting to animate labels created by `NumberLine.add_labels()`.
*   **Reason:** The `add_labels()` method (in some versions) might modify the `NumberLine` object in-place or return the `NumberLine` itself, rather than a distinct `VGroup` of just the labels. If you try to animate what you assume is a group of labels but isn't, errors can occur.
*   **Solution:**
    1.  Manually create the labels as separate `Tex` or `MathTex` mobjects.
    2.  Position them correctly relative to the `NumberLine` using `number_line.n2p(number_value)` to get the point for each label.
    3.  Collect these manually created labels into their own `VGroup`.
    4.  Animate this dedicated `VGroup` of labels.
