
def format_bytes(size_bytes: int) -> str:
    if size_bytes == 0:
        return "0B"
    size_names = ("B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB")
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f} {size_names[i]}"

def calculate_ratio(data_size: int, compr_size: int) -> str:
    """Calculates and formats the compression ratio."""
    if compr_size == 0:
        return "N/A"
    ratio = data_size / compr_size
    return f"{ratio:.2f}x"
