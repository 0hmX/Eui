import re

def extract_class_info_from_file(file_path, class_name):
    pattern = rf'^Class: {class_name}\n((?:  (?:Method|Property): .+\n)+)'
    with open(file_path, 'r') as f:
        content = f.read()
    match = re.search(pattern, content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return ""