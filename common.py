import base64
import json
from typing import Dict, Any

class ArchiveCommon:
    """Shared functionality and constants for CRUD Archive"""
    
    MAGIC_HEADER = b"CRUDARCHv1"
    SUPPORTED_TYPES = {'txt', 'json', 'py', 'bin'}
    
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
        """Check if file type is supported"""
        return file_type.lower() in ArchiveCommon.SUPPORTED_TYPES
