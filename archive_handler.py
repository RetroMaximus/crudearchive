import os
from typing import Dict, Any, Optional, Union, List, Tuple
import base64
import json
import struct
import zlib
try:
    from common import ArchiveCommon
except ImportError:
    from .common import ArchiveCommon

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from crudearch.common import ArchiveCommon
except ImportError:
    try:
        from common import ArchiveCommon
    except ImportError:
        try:
            from .common import ArchiveCommon
        except ImportError as e:
            raise ImportError(
                "Failed to import ArchiveCommon. "
                "Tried:\n"
                "1. crudearch.archive_handler\n"
                "2. archive_handler\n"
                "3. .archive_handler\n"
                f"Original error: {str(e)}\n"
            )
# In ArchiveCommon class
RESTRICTED_TYPES = {'exe', 'dll', 'bat', 'sh', 'php'}

class CrudeArchiveHandler:
    """Core handler for CRUD Archive operations"""
    
    def __init__(self, filename: str = None):
        self.filename = filename
        self.files: Dict[str, Dict[str, Any]] = {}
        self._3d_metadata = {}
        
    def create(self, filename: str) -> None:
        """Create a new empty archive"""
        self.filename = filename
        self.files = {}
        
    def load(self):
        """Extended load with 3D metadata"""
        with open(self.filename, 'rb') as f:
            header = f.read(len(ArchiveCommon.MAGIC_HEADER))
            if header != ArchiveCommon.MAGIC_HEADER:
                raise ValueError("Invalid archive format")
                
            data = json.loads(f.read().decode('utf-8'))
            
        self.files = {
            name: {
                'type': file_info['type'],
                'content': ArchiveCommon.decode_content(file_info['content'])
            }
            for name, file_info in data['files'].items()
        }
        
        self._3d_metadata = {
            name: {
                'lod': {int(k): ArchiveCommon.decode_content(v) 
                       for k,v in meta['lod'].items()},
                'animations': meta['animations'],
                'materials': meta['materials']
            }
            for name, meta in data.get('3d_metadata', {}).items()
        }
    
    def ssssave(self) -> None:
        """Save the archive to disk"""
        if not self.filename:
            raise ValueError("No filename specified")
            
        with open(self.filename, 'wb') as f:
            f.write(ArchiveCommon.MAGIC_HEADER)
            f.write(ArchiveCommon.serialize_archive(self.files))

    def save(self):
        """Extended save with 3D metadata"""
        data = {
            'files': {
                name: {
                    'type': info['type'],
                    'content': ArchiveCommon.encode_content(info['content'])
                }
                for name, info in self.files.items()
            },
            '3d_metadata': {
                name: {
                    'lod': {k: ArchiveCommon.encode_content(v) 
                           for k,v in meta['lod'].items()},
                    'animations': meta['animations'],
                    'materials': meta['materials']
                }
                for name, meta in self._3d_metadata.items()
            }
        }
        
        with open(self.filename, 'wb') as f:
            f.write(ArchiveCommon.MAGIC_HEADER)
            f.write(json.dumps(data).encode('utf-8'))

    @staticmethod
    def is_restricted_type(file_type: str) -> bool:
        """Check for potentially dangerous file types"""
        return file_type.lower().strip('.') in ArchiveCommon.RESTRICTED_TYPES
    
    # Then modify validate_file_type:
    @staticmethod
    def validate_file_type(file_type: str) -> bool:
        file_type = file_type.lower().strip('.')
        return (file_type in {ft.lower() for ft in ArchiveCommon.SUPPORTED_TYPES} 
                and not ArchiveCommon.is_restricted_type(file_type))
        def add_media_file(self, name: str, file_path: str) -> None:
            """Add media file with automatic type detection"""
            ext = os.path.splitext(name)[1][1:]  # Get extension without dot
            if not ArchiveCommon.validate_file_type(ext):
                raise ValueError(f"Unsupported media type: {ext}")
            
            with open(file_path, 'rb') as f:
                self.add_file(name, f.read(), ext)
    
    def get_file_mime_type(self, filename: str) -> str:
        """Get MIME type of archived file"""
        if filename not in self.files:
            raise FileNotFoundError(f"File {filename} not in archive")
        return ArchiveCommon.get_mime_type(self.files[filename]['type'])
    

    def add_file(self, name: str, content: Union[bytes, str], file_type: str = None) -> None:
        """Add a file to the archive"""
        if file_type is None:
            file_type = name.split('.')[-1] if '.' in name else 'bin'
        
        if not ArchiveCommon.validate_file_type(file_type):
            raise ValueError(f"Unsupported file type: {file_type}")
            
        if isinstance(content, str):
            content = content.encode('utf-8')
            
        self.files[name] = {
            'content': content,
            'type': file_type
        }



    # ======================
    # 3D Model Enhancements
    # ======================
    
    def add_3d_model(self, name: str, file_path: str, optimize: bool = True) -> None:
        """Add 3D model with optional optimization"""
        ext = name.split('.')[-1].lower()
        if ext not in ArchiveCommon.MODEL_FORMATS:
            raise ValueError(f"Unsupported 3D format: {ext}")
            
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            
        # Validate before processing
        self._validate_3d_model(raw_data, ext)
        
        # Apply format-specific optimization
        processed_data = raw_data
        if optimize:
            if ext == 'obj':
                processed_data = self._optimize_obj(raw_data)
            elif ext == 'gltf':
                processed_data = self._optimize_gltf(raw_data)
                
        self.add_file(name, processed_data, ext)

        # Process features
        model_id = name.replace('.', '_')
        self._3d_metadata[model_id] = {
            'lod': self._generate_lods(data, ext, lod_levels),
            'animations': self._extract_animations(data, ext),
            'materials': self._extract_materials(data, ext),
            'textures': self._extract_textures(data, ext) if include_textures else {}
        }

    def add_3d_data_model(self, name: str, data: bytes, lod_levels: int = 1, 
                    include_textures: bool = False) -> None:
        """Enhanced 3D model importer"""
        ext = name.split('.')[-1].lower()
        if ext not in ArchiveCommon.MODEL_FORMATS:
            raise ValueError(f"Unsupported 3D format: {ext}")
    
        # Validate model structure
        if not self.validate_model_file(data, ext):
            raise ValueError(f"Invalid {ext.upper()} file structure")
    
        # Store raw model
        self.add_file(name, data, ext)
        
        # Process features
        model_id = name.replace('.', '_')
        self._3d_metadata[model_id] = {
            'lod': self._generate_lods(data, ext, lod_levels),
            'animations': self._extract_animations(data, ext),
            'materials': self._extract_materials(data, ext),
            'textures': self._extract_textures(data, ext) if include_textures else {}
        }
    
    def _extract_textures(self, data: bytes, ext: str) -> Dict:
        """Extract embedded textures from 3D models"""
        textures = {}
        if ext == 'glb':
            # Parse GLB buffers for textures
            pass
        elif ext == 'fbx':
            # Extract FBX embedded textures
            pass
        return textures
    
    def _generate_lods(self, data: bytes, ext: str, levels: int) -> Dict[int, bytes]:
        """Generate Level of Detail variants"""
        lods = {}
        if ext == 'gltf':
            for i in range(levels):
                simplified = self._simplify_gltf(data, reduction=0.2 * (i+1))
                lods[i] = zlib.compress(simplified)
        elif ext == 'obj':
            for i in range(levels):
                simplified = self._simplify_obj(data, decimate_factor=0.3 * (i+1))
                lods[i] = simplified.encode()
        return lods

    def _extract_animations(self, data: bytes, ext: str) -> List[Dict]:
        """Extract animation data from supported formats"""
        animations = []
        if ext == 'fbx':
            # FBX animation extraction (simplified)
            anim_data = {
                'name': 'Take001',
                'frames': 60,
                'tracks': self._parse_fbx_anim(data)
            }
            animations.append(anim_data)
        elif ext == 'gltf':
            # GLTF animation parsing
            pass
        return animations

    def _extract_materials(self, data: bytes, ext: str) -> Dict:
        """Extract material/texture references"""
        materials = {}
        if ext == 'obj':
            # Parse MTL references
            mtl_lines = [l for l in data.decode('utf-8').splitlines() 
                        if l.startswith('usemtl')]
            materials['mtl_refs'] = [line.split()[1] for line in mtl_lines]
        return materials

    # ======================
    # 3D Data Access Methods
    # ======================

    def get_model_lod(self, name: str, lod_level: int = 0) -> bytes:
        """Retrieve specific LOD version"""
        model_id = name.replace('.', '_')
        if lod_level not in self._3d_metadata[model_id]['lod']:
            raise ValueError(f"LOD level {lod_level} not available")
        return zlib.decompress(self._3d_metadata[model_id]['lod'][lod_level])

    def get_animations(self, name: str) -> List[Dict]:
        """Get animation data for model"""
        model_id = name.replace('.', '_')
        return self._3d_metadata.get(model_id, {}).get('animations', [])

    def update_model_animation(self, name: str, anim_data: Dict) -> None:
        """Add/update animation data"""
        model_id = name.replace('.', '_')
        if model_id not in self._3d_metadata:
            self._3d_metadata[model_id] = {'animations': []}
        self._3d_metadata[model_id]['animations'].append(anim_data)

    # ======================
    # Internal Processors
    # ======================

    def _simplify_gltf(self, data: bytes, reduction: float) -> bytes:
        """GLTF mesh simplification (placeholder implementation)"""
        # In production: Use mesh simplification algorithm
        return data  # Return original for demo

    def _parse_fbx_anim(self, data: bytes) -> List:
        """FBX animation parser (simplified)"""
        # Look for FBX animation blocks
        anim_blocks = []
        pos = data.find(b'AnimationStack')
        while pos != -1:
            end_pos = data.find(b'}', pos)
            anim_blocks.append(data[pos:end_pos+1])
            pos = data.find(b'AnimationStack', end_pos)
        return anim_blocks
    
    def get_model_as_numpy(self, filename: str) -> np.ndarray:
        """Convert supported 3D models to numpy arrays"""
        if not NUMPY_AVAILABLE:
            raise ImportError("numpy is required for this feature")
        
        if filename not in self.files:
            raise FileNotFoundError(f"{filename} not in archive")
            
        ext = self.files[filename]['type']
        data = self.get_file(filename)
        
        if ext == 'npy':
            return np.load(io.BytesIO(data))
        elif ext == 'obj':
            return self._obj_to_numpy(data)
        # Add other converters as needed
    
    def _obj_to_numpy(self, obj_data: bytes) -> np.ndarray:
        """Simple OBJ to numpy converter (vertices only)"""
        import numpy as np
        vertices = []
        for line in obj_data.decode('utf-8').splitlines():
            if line.startswith('v '):
                vertices.append([float(x) for x in line[2:].split()])
        return np.array(vertices, dtype=np.float32)
    
    def validate_media_file(self, data: bytes, file_type: str) -> bool:
        """Validate media files by magic numbers"""
        file_type = file_type.lower()
        checks = {
            'png': lambda d: d.startswith(b'\x89PNG'),
            'jpg': lambda d: d.startswith(b'\xFF\xD8'),
            'gif': lambda d: d.startswith(b'GIF'),
            'mp3': lambda d: d.startswith(b'ID3') or d[1:4] == b'MP3',
            'wav': lambda d: d.startswith(b'RIFF') and d[8:12] == b'WAVE'
        }
        return checks.get(file_type, lambda _: True)(data)
    
    @staticmethod
    def validate_model_file(data: bytes, file_type: str) -> bool:
        """Additional validation for 3D models"""
        if len(data) > ArchiveCommon.MAX_MODEL_SIZE:
            return False
            
        # Add format-specific magic number checks
        if file_type == 'glb':
            return data.startswith(b'glTF')
        elif file_type == 'fbx':
            return data[:10].find(b'Kaydara') != -1
        return True
    
    def get_file(self, name: str) -> Optional[bytes]:
        """Get file content by name"""
        if name in self.files:
            return self.files[name]['content']
        return None
    
    def get_file_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get file info by name"""
        if name in self.files:
            return self.files[name]
        return None
    
    def remove_file(self, name: str) -> None:
        """Remove a file from the archive"""
        if name in self.files:
            del self.files[name]
    
    def list_files(self) -> list:
        """List all files in the archive"""
        return list(self.files.keys())
    
    def add_numeric_data(self, name: str, array: 'np.ndarray', compress: bool = True) -> None:
        """Add numpy array with optional compression"""
        if not NUMPY_AVAILABLE:
            raise ImportError("numpy is required for numeric data support")
        
        ext = name.split('.')[-1].lower()
        if ext not in {'npy', 'npz'}:
            raise ValueError("Only .npy and .npz formats supported")
        
        bio = io.BytesIO()
        if ext == 'npy':
            np.save(bio, array)
        else:  # npz
            np.savez_compressed(bio, data=array)
        
        self.add_file(name, bio.getvalue(), ext)
    
    def get_numeric_data(self, name: str) -> 'np.ndarray':
        """Retrieve numeric data as numpy array"""
        if not NUMPY_AVAILABLE:
            raise ImportError("numpy is required for this feature")
        
        data = self.get_file(name)
        ext = name.split('.')[-1].lower()
        
        if ext == 'npy':
            return np.load(io.BytesIO(data))
        elif ext == 'npz':
            return np.load(io.BytesIO(data))['data']
        else:
            raise ValueError("Unsupported numeric format")
    
    def add_dict_as_json(self, filename: str, data_dict: dict, indent: int = 2) -> None:
        """Add a dictionary as a JSON file to the archive"""
        if not filename.lower().endswith('.json'):
            filename += '.json'
        json_str = json.dumps(data_dict, indent=indent)
        self.add_text_file(filename, json_str)
    
    def add_text_data(self, filename: str, text_data: str, file_type: str = None) -> None:
        """Add text data directly to the archive"""
        if file_type is None:
            file_type = filename.split('.')[-1] if '.' in filename else 'txt'
        self.add_file(filename, text_data.encode('utf-8'), file_type)
    
    def add_binary_data(self, filename: str, binary_data: bytes, file_type: str = None) -> None:
        """Add binary data directly to the archive"""
        if file_type is None:
            file_type = filename.split('.')[-1] if '.' in filename else 'bin'
        self.add_file(filename, binary_data, file_type)

    def add_font(self, name: str, font_data: bytes) -> None:
        """Add font file with validation"""
        ext = name.split('.')[-1].lower()
        if ext not in {'ttf', 'otf'}:
            raise ValueError("Only TTF and OTF fonts supported")
        
        # Simple font validation
        if ext == 'ttf' and not font_data.startswith(b'\x00\x01\x00\x00'):
            raise ValueError("Invalid TTF font file")
        elif ext == 'otf' and not font_data.startswith(b'OTTO'):
            raise ValueError("Invalid OTF font file")
        
        self.add_file(name, font_data, ext)
    
    def add_image(self, name: str, image_data: bytes) -> None:
        """Add image with format validation"""
        ext = name.split('.')[-1].lower()
        if ext not in {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tga'}:
            raise ValueError("Unsupported image format")
        
        # Basic magic number validation
        if ext == 'png' and not image_data.startswith(b'\x89PNG'):
            raise ValueError("Invalid PNG file")
        elif ext in {'jpg', 'jpeg'} and not image_data.startswith(b'\xFF\xD8'):
            raise ValueError("Invalid JPEG file")
        # Add similar checks for other formats
        
        self.add_file(name, image_data, ext)
    
    def get_file_as_text(self, name: str, encoding: str = 'utf-8') -> Optional[str]:
        """Get file content as text"""
        content = self.get_file(name)
        if content is not None:
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                raise ValueError(f"File {name} is not a text file or uses different encoding")
        return None
    
    def add_text_file(self, name: str, text: str, encoding: str = 'utf-8') -> None:
        """Add a text file to the archive"""
        file_type = name.split('.')[-1] if '.' in name else 'txt'
        self.add_file(name, text.encode(encoding), file_type)
    
    def import_directory(self, dir_path: str) -> None:
        """Import all files from a directory"""
        for root, _, files in os.walk(dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                with open(file_path, 'rb') as f:
                    self.add_file(file, f.read())
