
import os

def read_sysfs():
    path = "/sys/block/zram0/orig_data_size"
    if os.path.exists(path):
        with open(path, "r") as f:
            content = f.read()
            print(f"Raw content of {path}: '{content}'")
            print(f"Stripped: '{content.strip()}'")
            print(f"Bool check: {bool(content.strip())}")
    else:
        print(f"{path} does not exist")

    path2 = "/sys/block/zram0/compr_data_size"
    if os.path.exists(path2):
        with open(path2, "r") as f:
            content = f.read()
            print(f"Raw content of {path2}: '{content}'")
    else:
        print(f"{path2} does not exist")

if __name__ == "__main__":
    read_sysfs()
