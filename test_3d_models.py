import os
from archive_handler import CrudeArchiveHandler

def test_3d_support():
    archive = CrudeArchiveHandler("game_assets.crudearch")
    archive.create("game_assets.crudearch")
    
    models_dir = "test_assets/3d_models"
    for model_file in os.listdir(models_dir):
        path = os.path.join(models_dir, model_file)
        print(f"Adding {model_file}...")
        archive.add_3d_model(model_file, path, optimize=True)
    
    archive.save()
    print(f"Archive created with {len(archive.list_files())} 3D models")

if __name__ == "__main__":
    test_3d_support()
