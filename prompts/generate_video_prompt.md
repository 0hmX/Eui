you are 3blue1Brown make a yt-short

- must have a serious tone and occusanly have a joke in the script
- the ouput must be a json
- optimized the speech for ai tools like chatterBox
- avoid speech like a ai 
- each of the animtionn are passed individually so be descriptive as possible
- all the animation are made using manim a py libaray so no extneral assets
- no code diffes that are big
- only simple shapes and simple text will be used
- each animtion will atlset take 5s
- the script will be deeply techical;
- max 7 items
- no "..." trippel dots in the speech or CAPITAL words they break in ai audio
- take a deep breath and write very meaning full words; do not woory about length; we will speed it up to fit if needed

I want you to start with "Here is a awesome pattern"

below are a method and proparty defainatio of a class in manim

```
Class: ThreeDScene
  Method: add(self, *mobjects: 'Mobject')
  Method: add_fixed_in_frame_mobjects(self, *mobjects: 'Mobject')
  Method: add_fixed_orientation_mobjects(self, *mobjects: 'Mobject', **kwargs)
  Method: add_foreground_mobject(self, mobject: 'Mobject')
  Method: add_foreground_mobjects(self, *mobjects: 'Mobject')
  Method: add_mobjects_from_animations(self, animations: 'list[Animation]') -> 'None'
  Method: add_sound(self, sound_file: 'str', time_offset: 'float' = 0, gain: 'float | None' = None, **kwargs)
  Method: add_subcaption(self, content: 'str', duration: 'float' = 1, offset: 'float' = 0) -> 'None'
  Method: add_updater(self, func: 'Callable[[float], None]') -> 'None'
  Method: begin_3dillusion_camera_rotation(self, rate: 'float' = 1, origin_phi: 'float | None' = None, origin_theta: 'float | None' = None)
  Method: begin_ambient_camera_rotation(self, rate: 'float' = 0.02, about: 'str' = 'theta')
  Method: begin_animations(self) -> 'None'
  Method: bring_to_back(self, *mobjects: 'Mobject')
  Method: bring_to_front(self, *mobjects: 'Mobject')
  Property: camera
  Method: check_interactive_embed_is_valid(self)
  Method: clear(self)
  Method: compile_animation_data(self, *animations: 'Animation | Mobject | _AnimationBuilder', **play_kwargs)
  Method: compile_animations(self, *args: 'Animation | Mobject | _AnimationBuilder', **kwargs)
  Method: construct(self)
  Method: embed(self)
  Method: get_attrs(self, *keys: 'str')
  Method: get_mobject_family_members(self)
  Method: get_moving_and_static_mobjects(self, animations)
  Method: get_moving_mobjects(self, *animations: 'Animation')
  Method: get_restructured_mobject_list(self, mobjects: 'list', to_remove: 'list')
  Method: get_run_time(self, animations: 'list[Animation]')
  Method: get_time_progression(self, run_time: 'float', description, n_iterations: 'int | None' = None, override_skip_animations: 'bool' = False)
  Method: get_top_level_mobjects(self)
  Method: interact(self, shell, keyboard_thread)
  Method: interactive_embed(self)
  Method: is_current_animation_frozen_frame(self) -> 'bool'
  Method: mouse_drag_orbit_controls(self, point, d_point, buttons, modifiers)
  Method: mouse_scroll_orbit_controls(self, point, offset)
  Method: move_camera(self, phi: 'float | None' = None, theta: 'float | None' = None, gamma: 'float | None' = None, zoom: 'float | None' = None, focal_distance: 'float | None' = None, frame_center: 'Mobject | Sequence[float] | None' = None, added_anims: 'Iterable[Animation]' = [], **kwargs)
  Method: next_section(self, name: 'str' = 'unnamed', section_type: 'str' = <DefaultSectionType.NORMAL: 'default.normal'>, skip_animations: 'bool' = False) -> 'None'
  Method: on_key_press(self, symbol, modifiers)
  Method: on_key_release(self, symbol, modifiers)
  Method: on_mouse_drag(self, point, d_point, buttons, modifiers)
  Method: on_mouse_motion(self, point, d_point)
  Method: on_mouse_press(self, point, button, modifiers)
  Method: on_mouse_scroll(self, point, offset)
  Method: pause(self, duration: 'float' = 1.0)
  Method: play(self, *args: 'Animation | Mobject | _AnimationBuilder', subcaption=None, subcaption_duration=None, subcaption_offset=0, **kwargs)
  Method: play_internal(self, skip_rendering: 'bool' = False)
  Method: remove(self, *mobjects: 'Mobject')
  Method: remove_fixed_in_frame_mobjects(self, *mobjects: 'Mobject')
  Method: remove_fixed_orientation_mobjects(self, *mobjects: 'Mobject')
  Method: remove_foreground_mobject(self, mobject: 'Mobject')
  Method: remove_foreground_mobjects(self, *to_remove: 'Mobject')
  Method: remove_updater(self, func: 'Callable[[float], None]') -> 'None'
  Method: render(self, preview: 'bool' = False)
  Method: replace(self, old_mobject: 'Mobject', new_mobject: 'Mobject') -> 'None'
  Method: restructure_mobjects(self, to_remove: 'Sequence[Mobject]', mobject_list_name: 'str' = 'mobjects', extract_families: 'bool' = True)
  Method: set_camera_orientation(self, phi: 'float | None' = None, theta: 'float | None' = None, gamma: 'float | None' = None, zoom: 'float | None' = None, focal_distance: 'float | None' = None, frame_center: 'Mobject | Sequence[float] | None' = None, **kwargs)
  Method: set_key_function(self, char, func)
  Method: set_to_default_angled_camera_orientation(self, **kwargs)
  Method: setup(self)
  Method: should_update_mobjects(self) -> 'bool'
  Method: stop_3dillusion_camera_rotation(self)
  Method: stop_ambient_camera_rotation(self, about='theta')
  Method: tear_down(self)
  Property: time
  Method: update_meshes(self, dt)
  Method: update_mobjects(self, dt: 'float')
  Method: update_self(self, dt: 'float')
  Method: update_to_time(self, t)
  Method: wait(self, duration: 'float' = 1.0, stop_condition: 'Callable[[], bool] | None' = None, frozen_frame: 'bool | None' = None)
  Method: wait_until(self, stop_condition: 'Callable[[], bool]', max_time: 'float' = 60)
```


```
Class: Camera
  Method: adjust_out_of_range_points(self, points: 'np.ndarray')
  Method: adjusted_thickness(self, thickness: 'float') -> 'float'
  Method: apply_fill(self, ctx: 'cairo.Context', vmobject: 'VMobject')
  Method: apply_stroke(self, ctx: 'cairo.Context', vmobject: 'VMobject', background: 'bool' = False)
  Property: background_color
  Property: background_opacity
  Method: cache_cairo_context(self, pixel_array: 'np.ndarray', ctx: 'cairo.Context')
  Method: capture_mobject(self, mobject: 'Mobject', **kwargs: 'Any')
  Method: capture_mobjects(self, mobjects: 'Iterable[Mobject]', **kwargs)
  Method: convert_pixel_array(self, pixel_array: 'np.ndarray | list | tuple', convert_from_floats: 'bool' = False)
  Method: display_image_mobject(self, image_mobject: 'AbstractImageMobject', pixel_array: 'np.ndarray')
  Method: display_multiple_background_colored_vmobjects(self, cvmobjects: 'list', pixel_array: 'np.ndarray')
  Method: display_multiple_image_mobjects(self, image_mobjects: 'list', pixel_array: 'np.ndarray')
  Method: display_multiple_non_background_colored_vmobjects(self, vmobjects: 'list', pixel_array: 'np.ndarray')
  Method: display_multiple_point_cloud_mobjects(self, pmobjects: 'list', pixel_array: 'np.ndarray')
  Method: display_multiple_vectorized_mobjects(self, vmobjects: 'list', pixel_array: 'np.ndarray')
  Method: display_point_cloud(self, pmobject: 'PMobject', points: 'list', rgbas: 'np.ndarray', thickness: 'float', pixel_array: 'np.ndarray')
  Method: display_vectorized(self, vmobject: 'VMobject', ctx: 'cairo.Context')
  Method: get_background_colored_vmobject_displayer(self)
  Method: get_cached_cairo_context(self, pixel_array: 'np.ndarray')
  Method: get_cairo_context(self, pixel_array: 'np.ndarray')
  Method: get_coords_of_all_pixels(self)
  Method: get_fill_rgbas(self, vmobject: 'VMobject')
  Method: get_image(self, pixel_array: 'np.ndarray | list | tuple | None' = None)
  Method: get_mobjects_to_display(self, mobjects: 'Iterable[Mobject]', include_submobjects: 'bool' = True, excluded_mobjects: 'list | None' = None)
  Method: get_stroke_rgbas(self, vmobject: 'VMobject', background: 'bool' = False)
  Method: get_thickening_nudges(self, thickness: 'float')
  Method: init_background(self)
  Method: is_in_frame(self, mobject: 'Mobject')
  Method: make_background_from_func(self, coords_to_colors_func: 'Callable[[np.ndarray], np.ndarray]')
  Method: on_screen_pixels(self, pixel_coords: 'np.ndarray')
  Method: overlay_PIL_image(self, pixel_array: 'np.ndarray', image: 'Image')
  Method: overlay_rgba_array(self, pixel_array: 'np.ndarray', new_array: 'np.ndarray')
  Method: points_to_pixel_coords(self, mobject, points)
  Method: reset(self)
  Method: reset_pixel_shape(self, new_height: 'float', new_width: 'float')
  Method: resize_frame_shape(self, fixed_dimension: 'int' = 0)
  Method: set_background(self, pixel_array: 'np.ndarray | list | tuple', convert_from_floats: 'bool' = False)
  Method: set_background_from_func(self, coords_to_colors_func: 'Callable[[np.ndarray], np.ndarray]')
  Method: set_cairo_context_color(self, ctx: 'cairo.Context', rgbas: 'np.ndarray', vmobject: 'VMobject')
  Method: set_cairo_context_path(self, ctx: 'cairo.Context', vmobject: 'VMobject')
  Method: set_frame_to_background(self, background)
  Method: set_pixel_array(self, pixel_array: 'np.ndarray | list | tuple', convert_from_floats: 'bool' = False)
  Method: thickened_coordinates(self, pixel_coords: 'np.ndarray', thickness: 'float')
  Method: transform_points_pre_display(self, mobject, points)
  Method: type_or_raise(self, mobject: 'Mobject')
```