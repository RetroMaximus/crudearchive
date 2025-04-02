# Crude Archive - Usage Guide

## Table of Contents
1. [Setup Instructions](#setup)
2. [Using ArchiveHandler (Programmatic)](#archivehandler)
3. [Using the GUI Manager](#gui-manager)
4. [Common Operations](#common-operations)

---

## <a name="setup"></a>1. Setup Instructions

### Requirements
- Python 3.7 or newer
- No additional dependencies needed

### Installation
Choose **one** of these methods:

#### Method A: Direct Copy
1. Download the `crudearch` folder
2. Place it in your project's root directory
3. Import with `from crudearch import CrudeArchiveHandler`

#### Method B: Git Clone
```bash
git clone https://github.com/yourusername/crudarchive.git
cd crudarchive
```

## <a name="archivehandler"></a>2. Using ArchiveHandler
Basic Workflow

1. Initialize a new archive handler
2. Create/Load an archive file
3. Perform operations (add/remove/extract)
4. Save changes

Example: Creating an Archive

```python

from crudearch import CrudeArchiveHandler

# Step 1: Initialize
archive = CrudeArchiveHandler("project.crudearch")

# Step 2: Create new archive
archive.create("project.crudearch")

# Step 3: Add content
archive.add_dict_as_json("config.json", {"key": "value"})
archive.add_text_data("notes.txt", "Important project notes")

# Step 4: Save
archive.save()
```
Key Methods
Method	Description
add_file()	Add any file type from disk
add_text_data()	Add string content directly
add_dict_as_json()	Store dictionaries as JSON
get_file()	Retrieve raw file content
get_file_as_text()	Get content as decoded string
<a name="gui-manager"></a>3. Using the GUI Manager
Launching the GUI

```bash
python -m crudearch.manager
```
or
```bash
python -m crudearch/manager.py
```


First-Time Walkthrough

- Create a new archive (File → New)

1. Add files:
    - Drag-and-drop files into the window, or
    - Use Edit → Add File
2. Preview files by clicking them
3. Save your archive (File → Save)

![Manager snapshot](images/crudearchive_004.png)

GUI Workflow
Hotkeys

- Ctrl+N: New archive
- Ctrl+O: Open archive
- Ctrl+S: Save
- Del: Remove selected file

<a name="common-operations"></a>4. Common Operations
Programmatic
``` python
# Extract JSON data
config_data = json.loads(archive.get_file_as_text("config.json"))

# Update a file
archive.add_text_data("notes.txt", "Updated notes content")

# List all files
for filename in archive.list_files():
    print(filename)
```
In a seperate project we will test by puttinng this snippeting into
the __init__ to see if we can retrive anything when it initializes

![Test code snippet implementation](images/crudearchive_003.png)

This was the result

![Result of test code](images/crudearchive_002.png) 


GUI Operations

- Import folder: File → Import Directory
- Export file: Right-click → Export
- Switch theme: Edit → Toggle Theme

## OpenGL/Numpy Integration

```python
from crudearch import CrudeArchiveHandler
import numpy as np
from OpenGL.GL import *

def load_model(archive_path, model_name):
    archive = CrudeArchiveHandler(archive_path)
    archive.load()
    
    if model_name.endswith('.obj'):
        # Get vertices as numpy array
        vertices = archive.get_model_as_numpy(model_name)
        
        # OpenGL setup
        vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        return vbo
```
## Animation Handeling

```python
# Create archive with 3D model
archive = CrudeArchiveHandler("game_assets.crudearch")
with open("character.fbx", "rb") as f:
    archive.add_3d_model("hero.fbx", f.read(), lod_levels=3)

# Access model features
animations = archive.get_animations("hero.fbx")
low_poly = archive.get_model_lod("hero.fbx", lod_level=2)

# Update animation at runtime
new_anim = {
    "name": "attack",
    "frames": 24,
    "tracks": [...] 
}
archive.update_model_animation("hero.fbx", new_anim)
archive.save()

```


1. Core Archive Operations

(All file types)

- create(filename: str) - Initialize new archive

- load() - Load existing archive

- save() - Save archive to disk

- list_files() - List all files in archive

- get_file(name: str) -> bytes - Get raw file bytes

- get_file_info(name: str) -> dict - Get file metadata (type/size)

- remove_file(name: str) - Delete file from archive

- add_binary_data(filename: str, text_data: str, file_type: str = None) - Add binary data directly to the archive.

2. Text/Script Files

(.txt, .json, .xml, .py, etc.)

- add_file(name: str, content: Union[bytes, str], file_type: str) - Add text/binary file

- get_file_as_text(name: str, encoding='utf-8') -> str - Decode text content

- add_text_file(name: str, text: str, encoding='utf-8') - Helper for text files

- add_dict_as_json(filename: str, data_dict: dict, indent: int = 2) - Add a dictionary as a JSON file to the archive.

- add_text_data(filename: str, text_data: str, file_type: str = None) - Add text data directly to the archive.

3. Media Files

(Images/Audio/Video)

- add_image(name: str, image_data: bytes) - Add with PNG/JPEG validation

- add_media_file(name: str, file_path: str) - Auto-detect type from path

- validate_media_file(data: bytes, file_type: str) -> bool - Check magic numbers

4. 3D Models

(.obj, .fbx, .gltf, etc.)

- add_3d_model(name: str, file_path: str, optimize=False)

- add_3d_data_model(name: str, data: bytes, lod_levels=1, include_textures=False)

- get_model_lod(name: str, lod_level=0) -> bytes

- get_animations(name: str) -> List[Dict] (NEW)

- update_model_animation(name: str, anim_data: Dict) -> None (NEW)

- get_model_as_numpy(filename: str) -> np.ndarray (NEW)

- validate_model_file(data: bytes, file_type: str) -> bool

5. Numeric Data

(.npy, .npz, .hdf5)

- add_numeric_data(name: str, array: np.ndarray, compress=True) - Add NumPy array

- get_numeric_data(name: str) -> np.ndarray - Retrieve as NumPy array

6. Fonts

(.ttf, .otf)

- add_font(name: str, font_data: bytes) - Add with font validation

7. Utilities

- get_file_mime_type(filename: str) -> str - Get MIME type (e.g., image/png)

- is_restricted_type(file_type: str) -> bool - Check against blocked types

- import_directory(dir_path: str) - Bulk add files from folder


