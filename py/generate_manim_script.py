import json
import os
import requests

common_error = """
Of course. Here is a summary of the common rendering errors encountered, presented in bullet points.

### Summary of Common Manim Rendering Errors (v0.19.0)

#### **1. Incorrect `Code` Class Arguments (API Mismatch)**

*   **Core Problem:** The most frequent issue was a series of `TypeError` exceptions caused by using modern syntax for the `Code` class on an older Manim version.

*   **Specific Errors & Solutions:**
    *   **`TypeError: ... unexpected keyword argument 'code'`**
        *   **Solution:** Changed the keyword argument from `code=` to `code_string=`. The older version requires this specific keyword to interpret the input as a string instead of a file path.
    *   **`TypeError: ... unexpected keyword argument 'style'`, `'font'`, `'line_spacing'`**
        *   **Solution:** Removed these arguments entirely, as they are not supported in the `Code` constructor of this Manim version.
    *   **`TypeError: ... unexpected keyword argument 'font_size'`**
        *   **Solution:** Removed the argument from the constructor and instead applied the `.scale()` method to the `Code` object after its creation to adjust its size.


#### **3. Unavailable Object Methods (API Mismatch)**

*   **Core Problem:** Attempting to use a method on an object that does not exist in this version of Manim.

*   **Specific Error & Solution:**
    *   **`AttributeError: Tex object has no attribute 'add_shadow'`**
        *   **Solution:** Manually replicated the "glow" effect since the `.add_shadow()` helper method was not available. This was done by:
            1.  Creating a `.copy()` of the `Tex` object.
            2.  Applying a wide, semi-transparent stroke to the copy using `.set_stroke()`.
            3.  Grouping the original object and the stroke-copy into a `VGroup`.

### 4. Here is a point-wise breakdown of the Manim rendering errors.
*   **Explicit Imports are Required:** The primary error, `ImportError` or `NameError`, occurs because specialized classes like `Blink` are not included in Manim's default namespace. Relying on `from manim import *` is insufficient. You must explicitly import such classes from their specific submodule.
    *   **Solution:** Add the line `from manim.animation.indication import Blink` at the top of your script.

*   **`add()` is for Objects, `play()` is for Animations:** This is the core logical mistake.
    *   `self.add(Mobject)`: This command instantly places a static object (like `Text`, `Circle`, `Rectangle`) on the screen. It is an instantaneous action.
    *   `self.play(Animation)`: This command executes a process that occurs over time (like `Write`, `FadeIn`, or `Blink`).
    *   **The Error:** `Blink` is an `Animation`, not a static `Mobject`. Trying to use `self.add(Blink(cursor))` fails because you are telling Manim to instantly add a process, which is not a valid operation.

*   **The Correct Implementation:**
    *   To make an object appear, use `self.add(my_object)`.
    *   To make that object perform the `Blink` animation, you must then use `self.play(Blink(my_object))`.

### 5. Alwaays use default for camera aspects do not edit the below values
 NVER DO THIS self.camera.frame_height = any value # Common aspect ratio for shorts
 NEVER DO THIS self.camera.frame_width = any value
"""

def generate_python_code_with_gemini(animation_description: str, previous_code: str | None = None, previous_problem: str | None = None) -> str:
    api_key = "AIzaSyBlnzDrAQ0zAO84OS9JNGzze4SC6vdPZIY"
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set.")

    model_name = "gemini-2.5-pro-preview-06-05"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"

    headers = {
        'Content-Type': 'application/json',
    }

    context_prompt = ""
    if previous_code:
        context_prompt += f"""
Context from the previous generation:
Previous Code:
'''python
{previous_code}
'''"""
    if previous_problem:
        context_prompt += f"""
Problem with previous code/generation: {previous_problem}"""

    prompt = f"""
    
Generate a complete, runnable Manim Python script for the
following animation description. The script should be a single scene
class that inherits from Scene. Do not include any
explanation, just the code inside a single python code block.
Optimized for youtube shorts; Keep animations at the center;
No code diffes that are too big. Always use simple shapes.
{context_prompt}

Current Animation Description: {animation_description}


make sure the old and new verison have coharance;
the old COULD BE the starting point for the new scean if present. ALSO NOT DEPENDS ON YOU.

Common Errors to avoid: {common_error}"""

    data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }

    print(f"Attempting Gemini API call for: {animation_description}")

    try:
        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 200:
            response_json = response.json()
            print("response_json:", response_json)
            
            try:
                generated_code = response_json['candidates'][0]['content']['parts'][0]['text']
                
                if generated_code.strip().startswith("```python"):
                    generated_code = generated_code.strip()[9:]
                    if generated_code.strip().endswith("```"):
                        generated_code = generated_code.strip()[:-3]
                
                return generated_code.strip()
            except (KeyError, IndexError) as e:
                error_message = f"Could not parse content from API response: {e}. Full response: {response_json}"
                print(error_message)
                return f"# Error: {error_message}"
        else:
            error_message = f"API request failed with status code {response.status_code}: {response.text}"
            print(error_message)
            return f"# Error: {error_message}"

    except requests.exceptions.RequestException as e:
        error_message = f"An error occurred during the HTTP request: {e}"
        print(error_message)
        return f"# Error: {error_message}"


def main():
    # Determine the workspace root dynamically
    script_file_path = os.path.abspath(__file__)
    script_directory = os.path.dirname(script_file_path)
    actual_workspace_root = os.path.abspath(os.path.join(script_directory, ".."))
    
    os.chdir(actual_workspace_root)

    # The old definitions for script_json_path, code_md_path, error_md_path,
    # workspace_root, and abs_... paths are replaced by these relative paths:
    script_json_path = os.path.join("md","script.json")
    code_md_path = os.path.join("md", "code.md")
    error_md_path = os.path.join("md", "error.md")

    # The following block is updated to use the new relative script_json_path
    if not os.path.exists(script_json_path):
        print(f"Error: {script_json_path} not found.")
        return

    try:
        with open(script_json_path, 'r', encoding='utf-8') as f:
            script_data = json.load(f)
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {script_json_path}.")
        return
    except Exception as e:
        print(f"Error reading {script_json_path}: {e}")
        return

    # Reset code.md before processing (This existing block will now use the updated code_md_path)
    try:
        with open(code_md_path, 'w', encoding='utf-8') as md_file:
            md_file.write(f"# Generated Manim Scripts (via {os.path.basename(__file__)})\n")
        print(f"Successfully reset {code_md_path}")
    except IOError as e:
        print(f"Error: Could not reset {code_md_path}. {e}")
        # Depending on requirements, you might want to return here or allow continuation

    # Reset error.md before processing (This existing block will now use the updated error_md_path)
    try:
        with open(error_md_path, 'w', encoding='utf-8') as err_file:
            err_file.write(f"# Error Log (via {os.path.basename(__file__)})\n\n")
        print(f"Successfully reset {error_md_path}")
    except IOError as e:
        print(f"Error: Could not reset {error_md_path}. {e}")
        # Depending on requirements, you might want to return here or allow continuation

    previous_generated_code = ""
    previous_generation_problem = ""

    with open(code_md_path, 'a', encoding='utf-8') as md_file:
        # The initial header is now written during the reset phase.
        # The is_empty check and conditional header writing previously here are removed.
        
        for index, item in enumerate(script_data):
            animation_description = item.get("animation-description")
            if animation_description:
                print(f"Processing animation description {index + 1}/{len(script_data)}...")
                python_code = generate_python_code_with_gemini(animation_description, previous_generated_code, previous_generation_problem)

                md_file.write(f"### Animation Scene {index + 1}\n")
                md_file.write(f"**Description:** {animation_description}\n\n")
                md_file.write("```python\n")
                md_file.write(python_code)
                md_file.write("\n```\n\n")
                print(f"Appended code for scene {index + 1} to {code_md_path}")

                if python_code.startswith("# Error:"):
                    previous_generation_problem = python_code
                else:
                    previous_generation_problem = "" 
                previous_generated_code = python_code
            else:
                print(f"Warning: No 'animation-description' found for item {index + 1}.")

    print(f"Processing complete. Manim Python code snippets appended to {code_md_path}")

if __name__ == "__main__":
    main()