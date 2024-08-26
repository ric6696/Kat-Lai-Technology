from pathlib import Path
from ..internal.Debug.utils import print_warn, print_info

# This file exports Available_Elements for use in models

ELEMENT_FILE = "Available_Elements.txt"


def get_elements_from_file(file_path: Path) -> set[str]:
    element_set = set()
    with open(file_path) as file:
        # Discard the two initial comment lines
        _, _, line = file.readline(), file.readline(), file.readline()
        while line:
            element_set.add(line.strip())
            line = file.readline()
    return element_set


try:
    Available_Elements = get_elements_from_file(Path(__file__).parent / ELEMENT_FILE)
except FileNotFoundError:
    Available_Elements = {
        "metal",
        "wood",
        "fire",
        "earth",
        "off",
    }  # Fallback elements

    print_warn("Elements file not found, creating a new file")
    with open(Path(__file__).parent / ELEMENT_FILE, "w") as file:
        file.write(
            "### File Format: Add elements in separate lines, "
            + "ensure that all elements are lowercase ###\n"
        )

        file.write(
            "### For implementation reference, refer to: "
            + f"{Path(__file__).relative_to(Path.cwd().parent)} ###\n"
        )

        for element in Available_Elements:
            file.write(element + "\n")
    print_info("Available_Elements.txt created, please edit the file for as needed")
