import base64
import json
import os
import struct
import zlib
from typing import Dict, Any, Optional, Union, List, Set

class ArchiveCommon:
    """Shared functionality and constants for CRUD Archive"""
    
    # Version 2 header for expanded format support
    MAGIC_HEADER = b"CRUDEARCHv2"
    
    # Organized type categories
    MEDIA_TYPES = {
        'images': {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tga'},
        'audio': {'mp3', 'wav', 'ogg'},
        'video': {'mp4', 'mpg', 'avi', 'mov'}
    }
    
    MODEL_FORMATS = {
        'static': {'obj', 'stl', 'ply'},
        'animated': {'fbx', 'gltf', 'glb', 'dae'},
        'industry': {'3ds', 'blend'}
    }
    
    NUMERIC_TYPES = {'npy', 'npz', 'hdf5'}
    FONT_TYPES = {'ttf', 'otf', 'woff', 'woff2'}
    SCRIPT_TYPES = {'py', 'json', 'xml', 'yaml'}
    
    # Combined supported types
    SUPPORTED_TYPES = (
        MEDIA_TYPES['images'] | MEDIA_TYPES['audio'] | MEDIA_TYPES['video'] |
        set().union(*MODEL_FORMATS.values()) |
        NUMERIC_TYPES | FONT_TYPES | SCRIPT_TYPES |
        {'txt', 'bin', 'md'}
    )
    
    # Security restrictions
    RESTRICTED_TYPES = {'exe', 'dll', 'bat', 'sh', 'php', 'js', 'vbs'}
    
    # Size limits (bytes)
    SIZE_LIMITS = {
        'default': 100 * 1024 * 1024,  # 100MB default limit
        'mp4': 500 * 1024 * 1024,      # 500MB for videos
        'glb': 200 * 1024 * 1024       # 200MB for binary models
    }

    # Enhanced MIME type mapping
    MIME_TYPE_MAP = {
        # 3D Models
        'obj': 'application/wavefront-obj',
        'fbx': 'application/octet-stream',
        'gltf': 'model/gltf+json',
        'glb': 'model/gltf-binary',
        
        # Media
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'mp3': 'audio/mpeg',
        'mp4': 'video/mp4',
        
        # Numeric
        'npy': 'application/x-numpy-data',
        'hdf5': 'application/x-hdf5',
        
        # Fonts
        'ttf': 'font/ttf',
        'otf': 'font/otf',
        'woff': 'font/woff'
        'woff2': 'font/woff2'
    }

    @classmethod
    def get_supported_types_by_category(cls) -> Dict[str, Set[str]]:
        """Get all supported types organized by category"""
        return {
            'media_images': cls.MEDIA_TYPES['images'],
            'media_audio': cls.MEDIA_TYPES['audio'],
            'media_video': cls.MEDIA_TYPES['video'],
            'models_static': cls.MODEL_FORMATS['static'],
            'models_animated': cls.MODEL_FORMATS['animated'],
            'numeric': cls.NUMERIC_TYPES,
            'fonts': cls.FONT_TYPES,
            'scripts': cls.SCRIPT_TYPES
        }

    @staticmethod
    def get_mime_type(extension: str) -> str:
        """Get MIME type for supported extensions"""
        ext = extension.lower().strip('.')
        return ArchiveCommon.MIME_TYPE_MAP.get(ext, 'application/octet-stream')

    @staticmethod
    def encode_content(content: bytes) -> str:
        """Encode binary content for JSON storage"""
        return base64.b64encode(content).decode('utf-8')
    
    @staticmethod
    def decode_content(encoded: str) -> bytes:
        """Decode content from JSON storage"""
        return base64.b64decode(encoded.encode('utf-8'))
    
    @staticmethod
    def serialize_archive(files: Dict[str, Dict[str, Any]]) -> bytes:
        """Serialize archive data to bytes"""
        data = {
            'files': {
                name: {
                    'type': info['type'],
                    'content': ArchiveCommon.encode_content(info['content'])
                }
                for name, info in files.items()
            }
        }
        return json.dumps(data, indent=2).encode('utf-8')
    
    @staticmethod
    def deserialize_archive(data: bytes) -> Dict[str, Dict[str, Any]]:
        """Deserialize archive data from bytes"""
        return json.loads(data.decode('utf-8'))
    
    @staticmethod
    def validate_file_type(file_type: str) -> bool:
        """
        Validate if a file type is supported and not restricted
        Returns True if file can be added to archive
        """
        file_type = file_type.lower().strip('.')
        return (file_type in ArchiveCommon.SUPPORTED_TYPES and 
                file_type not in ArchiveCommon.RESTRICTED_TYPES)
    
    @staticmethod
    def validate_file_size(data: bytes, file_type: str) -> bool:
        """Check if file size is within limits"""
        file_type = file_type.lower().strip('.')
        max_size = ArchiveCommon.SIZE_LIMITS.get(file_type, 
                 ArchiveCommon.SIZE_LIMITS['default'])
        return len(data) <= max_size
     

    @classmethod
    def validate_file(cls, data: bytes, file_type: str) -> bool:
        """Comprehensive file validation"""
        file_type = file_type.lower().strip('.')
        
        # Type check
        if file_type not in cls.SUPPORTED_TYPES:
            return False
            
        # Security check
        if file_type in cls.RESTRICTED_TYPES:
            return False
            
        # Size check
        max_size = cls.SIZE_LIMITS.get(file_type, cls.SIZE_LIMITS['default'])
        if len(data) > max_size:
            return False
            
        # Magic number validation
        if not cls._check_magic_numbers(data, file_type):
            return False
            
        return True

    @staticmethod
    def _check_magic_numbers(data: bytes, file_type: str) -> bool:
        """Verify file signatures"""
        signatures = {
            'png': b'\x89PNG',
            'jpg': b'\xFF\xD8',
            'gif': b'GIF',
            'zip': b'PK\x03\x04',
            'pdf': b'%PDF',
            'mp3': (b'ID3', lambda d: d[1:4] == b'MP3'),
            'obj': (lambda d: b'v ' in d[:100]),  # OBJ has vertices early
            'fbx': (lambda d: b'Kaydara' in d[:100])
        }
        
        check = signatures.get(file_type.lower())
        if not check:
            return True  # No signature check available
            
        if isinstance(check, bytes):
            return data.startswith(check)
        elif callable(check):
            return check(data)
        elif isinstance(check, tuple):
            return any(data.startswith(s) if isinstance(s, bytes) else s(data) 
                   for s in check)
        return True

    @staticmethod
    def get_file_category(file_type: str) -> str:
        """Get category for file type"""
        file_type = file_type.lower()
        for category, types in ArchiveCommon.MEDIA_TYPES.items():
            if file_type in types:
                return f"media/{category}"
        for category, types in ArchiveCommon.MODEL_FORMATS.items():
            if file_type in types:
                return f"model/{category}"
        if file_type in ArchiveCommon.NUMERIC_TYPES:
            return "numeric"
        if file_type in ArchiveCommon.FONT_TYPES:
            return "font"
        return "other"
