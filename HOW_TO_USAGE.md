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
First-Time Walkthrough

- Create a new archive (File → New)

1. Add files:
    - Drag-and-drop files into the window, or
    - Use Edit → Add File
2. Preview files by clicking them
3. Save your archive (File → Save)

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
GUI Operations

- Import folder: File → Import Directory
- Export file: Right-click → Export
- Switch theme: Edit → Toggle Theme
