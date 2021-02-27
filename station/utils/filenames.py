
def is_safe_filename_character(c: str) -> bool:
    return c.isalpha() or c.isdigit() or c in (' ', '.', '-', ' ', '_')

def safe_filename(filename: str, replacement: str="_") -> str:
    chars = [c if is_safe_filename_character(c) else replacement for c in filename]
    return "".join(chars).rstrip()
