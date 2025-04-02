import os
from typing import Dict, Any, Optional, Union
try:
    from common import ArchiveCommon
except ImportError:
    from .common import ArchiveCommon


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

class CrudeArchiveHandler:
    """Core handler for CRUD Archive operations"""
    
    def __init__(self, filename: str = None):
        self.filename = filename
        self.files: Dict[str, Dict[str, Any]] = {}
        
    def create(self, filename: str) -> None:
        """Create a new empty archive"""
        self.filename = filename
        self.files = {}
        
    def load(self) -> None:
        """Load an existing archive"""
        if not self.filename:
            raise ValueError("No filename specified")
            
        with open(self.filename, 'rb') as f:
            header = f.read(len(ArchiveCommon.MAGIC_HEADER))
            if header != ArchiveCommon.MAGIC_HEADER:
                raise ValueError("Invalid CRUD archive format")
                
            data = ArchiveCommon.deserialize_archive(f.read())
            self.files = {
                name: {
                    'type': file_info['type'],
                    'content': ArchiveCommon.decode_content(file_info['content'])
                }
                for name, file_info in data['files'].items()
            }
    
    def save(self) -> None:
        """Save the archive to disk"""
        if not self.filename:
            raise ValueError("No filename specified")
            
        with open(self.filename, 'wb') as f:
            f.write(ArchiveCommon.MAGIC_HEADER)
            f.write(ArchiveCommon.serialize_archive(self.files))
    
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
