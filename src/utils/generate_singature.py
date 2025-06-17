import inspect
import types
import importlib

def extract_function_signatures(module_name, output_file):
    module = importlib.import_module(module_name)
    signatures = []
    for name, obj in inspect.getmembers(module):
        if isinstance(obj, types.FunctionType):
            sig = str(inspect.signature(obj))
            ret = inspect.signature(obj).return_annotation
            ret = f" -> {ret}" if ret != inspect.Signature.empty else ""
            signatures.append(f"def {name}{sig}{ret}\n")
    with open(output_file, 'w') as f:
        f.writelines(signatures)

extract_function_signatures('manim', 'module_signatures.txt')

def list_class_methods(module_name, output_file):
    module = importlib.import_module(module_name)
    with open(output_file, 'w') as f:
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj):
                f.write(f"Class: {name}\n")
                for attr_name, attr_obj in inspect.getmembers(obj):
                    if (inspect.isfunction(attr_obj) or inspect.ismethoddescriptor(attr_obj)) and \
                       not attr_name.startswith('_'):
                        try:
                            sig = str(inspect.signature(attr_obj))
                        except ValueError:
                            sig = '(...)'
                        f.write(f"  Method: {attr_name}{sig}\n")
                    elif isinstance(attr_obj, property) and not attr_name.startswith('_'):
                        f.write(f"  Property: {attr_name}\n")
                f.write("\n")

list_class_methods('manim', 'class_methods.txt')
