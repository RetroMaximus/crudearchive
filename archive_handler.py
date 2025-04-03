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
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        ext = os.path.splitext(file_path)[1][1:].lower()
        with open(file_path, 'rb') as f:
            data = f.read()
        
        if ext in {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tga'}:
            self.add_image(name, data)
        elif ext in {'mp3', 'wav', 'ogg'}:
            self.add_audio(name, data)
        elif ext in {'mp4', 'avi', 'mov'}:
            self.add_video(name, data)
        else:
            raise ValueError(f"Unsupported media type: {ext}")
    
    def add_audio(self, name: str, audio_data: bytes) -> None:
        """Specialized audio file adder"""
        ext = name.split('.')[-1].lower()
        if not self.validate_media_file(audio_data, ext):
            raise ValueError(f"Invalid {ext.upper()} audio file")
        
        metadata = self._extract_audio_metadata(audio_data, ext)
        self.add_file(name, audio_data, ext, metadata=metadata)

    def add_video(self, name: str, video_data: bytes) -> None:
        """Specialized video file adder"""
        ext = name.split('.')[-1].lower()
        if not self.validate_media_file(video_data, ext):
            raise ValueError(f"Invalid {ext.upper()} video file")
        
        metadata = self._extract_video_metadata(video_data, ext)
        self.add_file(name, video_data, ext, metadata=metadata)


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
    # Internal Media Processors
    # ======================
    
    def _extract_image_metadata(self, data: bytes, ext: str) -> dict:
        """Extract basic image metadata"""
        metadata = {'type': 'image', 'format': ext}
        
        try:
            if ext == 'png':
                metadata.update(self._parse_png_chunks(data))
            elif ext in ('jpg', 'jpeg'):
                metadata.update(self._parse_jpeg_segments(data))
            elif ext == 'gif':
                width, height = struct.unpack('<HH', data[6:10])
                metadata.update({'width': width, 'height': height})
        except:
            pass  # Return basic info if parsing fails
        
        return metadata
    
    def _get_image_info(self, data: bytes, ext: str) -> dict:
        """Get detailed image information"""
        info = self._extract_image_metadata(data, ext)
        info['size'] = len(data)
        return info
    
    def _parse_png_chunks(self, data: bytes) -> dict:
        """Extract PNG IHDR chunk data"""
        if len(data) > 24 and data[12:16] == b'IHDR':
            return {
                'width': struct.unpack('>I', data[16:20])[0],
                'height': struct.unpack('>I', data[20:24])[0],
                'bit_depth': data[24],
                'color_type': data[25]
            }
        return {}
    
    def _parse_jpeg_segments(self, data: bytes) -> dict:
        """Extract JPEG SOF segment data"""
        pos = 2  # Skip SOI marker
        while pos < len(data) - 1:
            marker = data[pos:pos+2]
            if marker[0] != 0xFF:
                break
                
            if marker[1] in (0xC0, 0xC2):  # SOF0/SOF2
                return {
                    'width': struct.unpack('>H', data[pos+7:pos+9])[0],
                    'height': struct.unpack('>H', data[pos+5:pos+7])[0],
                    'components': data[pos+9]
                }
            pos += 2 + struct.unpack('>H', data[pos+2:pos+4])[0]
        return {}

    
    def _extract_audio_metadata(self, data: bytes, ext: str) -> dict:
        """Extract audio metadata based on format"""
        metadata = {'type': 'audio', 'format': ext}
        
        try:
            if ext == 'mp3':
                metadata.update(self._parse_mp3_header(data))
            elif ext == 'wav':
                metadata.update(self._parse_wav_header(data))
            elif ext == 'ogg':
                metadata.update(self._parse_ogg_header(data))
        except:
            pass  # Return basic info if parsing fails
        
        return metadata
    
    def _parse_mp3_header(self, data: bytes) -> dict:
        """Extract MP3 (ID3) metadata"""
        metadata = {}
        # Check for ID3v2 header
        if len(data) > 10 and data[:3] == b'ID3':
            metadata['id3_version'] = f"{data[3]}.{data[4]}"
            metadata['size'] = (data[6] << 21 | data[7] << 14 | 
                              data[8] << 7 | data[9]) + 10
            
        # Parse MPEG frame header (first valid frame after ID3)
        pos = metadata.get('size', 0)
        while pos < len(data) - 4:
            if data[pos] == 0xFF and (data[pos+1] & 0xE0) == 0xE0:
                frame = data[pos:pos+4]
                version = (frame[1] >> 3) & 0x03
                layer = (frame[1] >> 1) & 0x03
                bitrate_idx = (frame[2] >> 4) & 0x0F
                sample_rate_idx = (frame[2] >> 2) & 0x03
                
                metadata.update({
                    'mpeg_version': ['2.5', None, '2', '1'][version],
                    'layer': {1: 'III', 2: 'II', 3: 'I'}.get(layer),
                    'bitrate': self._get_mp3_bitrate(version, layer, bitrate_idx),
                    'sample_rate': self._get_mp3_sample_rate(version, sample_rate_idx),
                    'channel_mode': ['stereo', 'joint stereo', 
                                    'dual channel', 'mono'][(frame[3] >> 6) & 0x03]
                })
                break
            pos += 1
        
        return metadata
    
    def _parse_wav_header(self, data: bytes) -> dict:
        """Extract WAV file metadata"""
        if len(data) < 44 or data[:4] != b'RIFF' or data[8:12] != b'WAVE':
            return {}
        
        return {
            'audio_format': struct.unpack('<H', data[20:22])[0],
            'channels': struct.unpack('<H', data[22:24])[0],
            'sample_rate': struct.unpack('<I', data[24:28])[0],
            'bit_depth': struct.unpack('<H', data[34:36])[0],
            'duration': (struct.unpack('<I', data[40:44])[0] / 
                        (struct.unpack('<I', data[24:28])[0] /
                        struct.unpack('<H', data[22:24])[0] /
                        (struct.unpack('<H', data[34:36])[0] / 8)))
        }
    
    def _parse_ogg_header(self, data: bytes) -> dict:
        """Extract Ogg Vorbis metadata"""
        if len(data) < 28 or data[:4] != b'OggS':
            return {}
        
        return {
            'version': data[4],
            'channels': data[11],
            'sample_rate': struct.unpack('<I', data[12:16])[0],
            'bitrate_max': struct.unpack('<I', data[16:20])[0],
            'bitrate_nom': struct.unpack('<I', data[20:24])[0],
            'bitrate_min': struct.unpack('<I', data[24:28])[0]
        }
    
    # Video Parsers
    def _extract_video_metadata(self, data: bytes, ext: str) -> dict:
        """Extract video metadata based on format"""
        metadata = {'type': 'video', 'format': ext}
        
        try:
            if ext == 'mp4':
                metadata.update(self._parse_mp4_atoms(data))
            elif ext == 'avi':
                metadata.update(self._parse_avi_header(data))
            elif ext == 'mov':
                metadata.update(self._parse_mov_header(data))
        except:
            pass
        
        return metadata
    
    def _parse_mp4_atoms(self, data: bytes) -> dict:
        """Parse MP4 container atoms"""
        metadata = {}
        pos = 0
        
        while pos < len(data) - 8:
            atom_size = struct.unpack('>I', data[pos:pos+4])[0]
            atom_type = data[pos+4:pos+8].decode('ascii', errors='ignore')
            
            if atom_type == 'moov':
                metadata['duration'] = self._parse_moov_atom(data[pos+8:pos+atom_size])
            elif atom_type == 'ftyp':
                metadata['codec'] = data[pos+8:pos+12].decode('ascii', errors='ignore')
            elif atom_type == 'tkhd' and pos + 80 < len(data):
                # Track header contains width/height (fixed-point 16.16)
                metadata['width'] = struct.unpack('>I', data[pos+76:pos+80])[0] / 65536
                metadata['height'] = struct.unpack('>I', data[pos+80:pos+84])[0] / 65536
            
            pos += atom_size
        
        return metadata
    
    def _parse_avi_header(self, data: bytes) -> dict:
        """Extract AVI file metadata"""
        if len(data) < 144 or data[:4] != b'RIFF' or data[8:12] != b'AVI ':
            return {}
        
        return {
            'frames': struct.unpack('<I', data[48:52])[0],
            'width': struct.unpack('<I', data[64:68])[0],
            'height': struct.unpack('<I', data[68:72])[0],
            'codec': data[112:116].decode('ascii', errors='ignore').strip(),
            'fps': struct.unpack('<I', data[80:84])[0] / 
                   struct.unpack('<I', data[84:88])[0]
        }
    
    # Helper methods for MP3
    def _get_mp3_bitrate(self, version: int, layer: int, idx: int) -> int:
        """MP3 bitrate lookup tables"""
        # [version][layer][bitrate_index]
        bitrates = [
            [  # MPEG 1
                [0, 32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448],  # Layer I
                [0, 32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384],     # Layer II
                [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320]       # Layer III
            ],
            [  # MPEG 2/2.5
                [0, 32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256],     # Layer I
                [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],          # Layer II/III
                [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160]           # Layer II/III
            ]
        ]
        version_idx = 0 if version == 1 else 1
        layer_idx = min(layer-1, 2)  # Convert to 0-based index
        return bitrates[version_idx][layer_idx][idx] * 1000 if idx < 15 else 0
    
    def _get_mp3_sample_rate(self, version: int, idx: int) -> int:
        """MP3 sample rate lookup"""
        rates = [
            [44100, 48000, 32000],  # MPEG 1
            [22050, 24000, 16000],   # MPEG 2
            [11025, 12000, 8000]     # MPEG 2.5
        ]
        return rates[version][idx % 3]
   
    def _get_audio_info(self, data: bytes, ext: str) -> dict:
        """Get comprehensive audio metadata"""
        info = self._extract_audio_metadata(data, ext)
        info.update({
            'size': len(data),
            'duration': self._calculate_audio_duration(data, ext),
            'bitrate': self._calculate_audio_bitrate(data, ext),
            'codec': self._get_audio_codec(ext)
        })
        return info
    
    def _get_video_info(self, data: bytes, ext: str) -> dict:
        """Get comprehensive video metadata"""
        info = self._extract_video_metadata(data, ext)
        info.update({
            'size': len(data),
            'duration': self._calculate_video_duration(data, ext),
            'bitrate': self._calculate_video_bitrate(data, ext),
            'aspect_ratio': self._calculate_aspect_ratio(info),
            'streams' :self._get_video_streams(data, ext),
            'codec_info':{}
        })
        
        # Add codec-specific enhancements
        if 'codec' not in info:
            info['codec'] = self._detect_video_codec(data, ext)
        
        return info
    
    # ======================
    # Audio Helper Methods
    # ======================
    
    def _calculate_audio_duration(self, data: bytes, ext: str) -> float:
        """Calculate duration in seconds"""
        try:
            if ext == 'mp3':
                return self._get_mp3_duration(data)
            elif ext == 'wav':
                return struct.unpack('<I', data[40:44])[0] / (
                       struct.unpack('<I', data[24:28])[0] *
                       struct.unpack('<H', data[22:24])[0] *
                       (struct.unpack('<H', data[34:36])[0] / 8))
            elif ext == 'ogg':
                return len(data) / (self._get_ogg_bitrate(data) / 8)
        except:
            return 0.0
    
    def _calculate_audio_bitrate(self, data: bytes, ext: str) -> int:
        """Calculate bitrate in kbps"""
        if ext == 'mp3':
            return self._parse_mp3_header(data).get('bitrate', 0)
        return int((len(data) * 8) / (self._calculate_audio_duration(data, ext) * 1000))

    def get_audio_cover(self, filename: str, renderer: str = None) -> Optional[Any]:
        """Extract embedded cover art and prepare for specified renderer."""
        if filename not in self.files:
            raise FileNotFoundError(f"File {filename} not in archive")
        
        # Extract raw cover art bytes
        raw_data = None
        data = self.get_file(filename)
        ext = self.files[filename]['type'].lower()
        
        if ext == 'mp3':
            raw_data = self._extract_mp3_cover(data)
        elif ext == 'flac':
            raw_data = self._extract_flac_cover(data)
        
        # Return raw data if no renderer requested
        if not raw_data or renderer is None:
            return raw_data
        
        # Validate renderer name first
        valid_renderers = {'OPENGL', 'tkinter', 'pygame', 'PyQt', 'pyopengl'}
        if renderer not in valid_renderers:
            raise ValueError(
                f"Unsupported renderer: {renderer}. "
                f"Must be one of: {', '.join(sorted(valid_renderers))}"
            )
        
        # Prepare for specific renderer (now raises ImportError if packages missing)
        if renderer == 'tkinter':
            
            try:
                from PIL import Image, ImageTk
                import io
                img = Image.open(io.BytesIO(raw_data))

            except ImportError as e:
                print(f"Dependencies required for this feature: pip install pillow")

            return ImageTk.PhotoImage(img)
            
        elif renderer == 'pygame':
            try:
                import pygame
                import io
                return pygame.image.load(io.BytesIO(raw_data))
            except ImportError as e:
                print(f"Dependencies required for this feature: pip install pygame")
            
        elif renderer in ('OPENGL', 'pyopengl'):
            try:
                from PIL import Image
                import numpy as np
                img = Image.open(io.BytesIO(raw_data))
                return np.array(img)
            except ImportError as e:
                print(f"Dependencies required for this feature: pip install pyopengl")
            
        elif renderer == 'PyQt':
            try:
                from PyQt5.QtGui import QImage, QPixmap
                img = QImage()
                img.loadFromData(raw_data)
                return QPixmap.fromImage(img)
            except ImportError as e:
                print(f"Dependencies required for this feature: pip install pyqt")

    def _extract_mp3_cover(self, data: bytes) -> Optional[bytes]:
        """Extract cover from ID3v2 tags"""
        if len(data) > 10 and data[:3] == b'ID3':
            tag_size = (data[6] << 21 | data[7] << 14 | 
                      data[8] << 7 | data[9]) + 10
            pos = 10
            
            while pos < tag_size - 10:
                frame_id = data[pos:pos+4]
                frame_size = struct.unpack('>I', data[pos+4:pos+8])[0]
                
                if frame_id == b'APIC':
                    # Skip header to get to image data
                    return data[pos+10:pos+frame_size]
                pos += 10 + frame_size
        return None
    
    def _extract_flac_cover(self, data: bytes) -> Optional[bytes]:
        """Extract cover from FLAC metadata"""
        if len(data) > 4 and data[:4] == b'fLaC':
            pos = 4
            while pos < len(data) - 4:
                header = data[pos:pos+4]
                block_type = header[0] & 0x7F
                block_size = struct.unpack('>I', b'\x00' + header[1:4])[0]
                
                if block_type == 6:  # PICTURE block
                    # Parse FLAC picture structure
                    pic_type = struct.unpack('>I', data[pos+4:pos+8])[0]
                    if pic_type == 3:  # Front cover
                        offset = pos + 32
                        return data[offset:offset+block_size-28]
                pos += 4 + block_size
        return None
    
    # ======================
    # Video Helper Methods
    # ======================
    
    def _get_video_streams(self, data: bytes, ext: str) -> List[Dict]:
        """Identify all media streams in video container"""
        streams = []
        
        if ext == 'mp4':
            # Parse MP4 track headers
            pos = 0
            while pos < len(data) - 8:
                size = struct.unpack('>I', data[pos:pos+4])[0]
                atom_type = data[pos+4:pos+8]
                
                if atom_type == b'trak':
                    stream_type = b'vide'
                    codec = b'unknown'
                    # Look for media handler type and codec
                    sub_pos = pos + 8
                    while sub_pos < pos + size:
                        sub_size = struct.unpack('>I', data[sub_pos:sub_pos+4])[0]
                        sub_type = data[sub_pos+4:sub_pos+8]
                        
                        if sub_type == b'hdlr':
                            stream_type = data[sub_pos+16:sub_pos+20]
                        elif sub_type == b'stsd':
                            codec = data[sub_pos+12:sub_pos+16]
                        sub_pos += sub_size
                    
                    streams.append({
                        'type': stream_type.decode('ascii', errors='ignore'),
                        'codec': codec.decode('ascii', errors='ignore')
                    })
                pos += size
        
        elif ext == 'avi':
            # Parse AVI stream headers
            if len(data) > 116 and data[112:116] == b'vids':
                streams.append({
                    'type': 'video',
                    'codec': data[112:116].decode('ascii')
                })
            if len(data) > 160 and data[156:160] == b'auds':
                streams.append({
                    'type': 'audio',
                    'codec': data[156:160].decode('ascii')
                })
        
        return streams

    def _calculate_video_duration(self, data: bytes, ext: str) -> float:
        """Get duration in seconds"""
        try:
            if ext == 'mp4':
                return self._parse_mp4_atoms(data).get('duration', 0)
            elif ext == 'avi':
                return (struct.unpack('<I', data[48:52])[0] / 
                       struct.unpack('<I', data[32:36])[0])
        except:
            return 0.0
    
    def _calculate_video_bitrate(self, data: bytes, ext: str) -> float:
        """Calculate average bitrate in Mbps"""
        duration = self._calculate_video_duration(data, ext)
        if duration > 0:
            return (len(data) * 8) / (duration * 1000000)
        return 0.0
    
    def _calculate_aspect_ratio(self, metadata: dict) -> str:
        """Calculate display aspect ratio"""
        if 'width' not in metadata or 'height' not in metadata:
            return 'unknown'
        
        width = metadata['width']
        height = metadata['height']
        
        # Common aspect ratios with tolerance
        ratios = {
            (16, 9): '16:9',
            (4, 3): '4:3',
            (1, 1): '1:1'
        }
        
        for (w, h), ratio in ratios.items():
            if abs(width/height - w/h) < 0.05:
                return ratio
        
        # Return calculated ratio if no match
        gcd = self._gcd(round(width), round(height))
        return f"{round(width/gcd)}:{round(height/gcd)}"
    
    @staticmethod
    def _gcd(a: int, b: int) -> int:
        """Greatest common divisor helper"""
        while b:
            a, b = b, a % b
        return a


    # ======================
    # Internal Processors
    # ======================
    
    def _get_h264_info(self, data: bytes) -> Dict:
        """Parse H.264-specific parameters from MP4/AVC"""
        info = {}
        pos = 0
        
        while pos < len(data) - 8:
            size = struct.unpack('>I', data[pos:pos+4])[0]
            atom_type = data[pos+4:pos+8]
            
            if atom_type == b'avcC':
                # AVC Configuration Atom
                info['profile'] = data[pos+12]
                info['level'] = data[pos+13]
                info['nalu_size'] = (data[pos+14] & 0x03) + 1
                break
                
            pos += size
        
        return info
    
    def _get_video_codec_info(self, data: bytes, codec: str) -> Dict:
        """Get codec-specific parameters"""
        if codec.lower() in ('avc1', 'h264'):
            return self._get_h264_info(data)
        elif codec.lower() == 'hev1':
            return self._get_hevc_info(data)
        return {}
    
    # Example HEVC parser
    def _get_hevc_info(self, data: bytes) -> Dict:
        """Parse HEVC/H.265 parameters"""
        info = {}
        pos = 0
        
        while pos < len(data) - 8:
            size = struct.unpack('>I', data[pos:pos+4])[0]
            atom_type = data[pos+4:pos+8]
            
            if atom_type == b'hvcC':
                info['profile'] = data[pos+12]
                info['tier'] = (data[pos+13] & 0xC0) >> 6
                info['level'] = data[pos+13] & 0x3F
                break
                
            pos += size
        
        return info

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
        """Validate media files by magic numbers and structure"""
        file_type = file_type.lower()
        signatures = {
            'png': b'\x89PNG',
            'jpg': b'\xFF\xD8',
            'gif': b'GIF',
            'bmp': b'BM',
            'mp3': (b'ID3', lambda d: d[1:4] == b'MP3'),
            'wav': (b'RIFF', lambda d: d[8:12] == b'WAVE'),
            'mp4': (b'\x00\x00\x00\x18ftyp', lambda d: d[4:8] == b'ftyp')
        }
        
        if file_type not in signatures:
            return True  # Skip validation for types without known signatures
            
        check = signatures[file_type]
        if isinstance(check, bytes):
            return data.startswith(check)
        elif callable(check):
            return check(data)
        elif isinstance(check, tuple):
            return any(data.startswith(s) if isinstance(s, bytes) else s(data) 
                   for s in check)
        return False
   
    def get_media_info(self, filename: str) -> dict:
        """Get metadata for media files"""
        if filename not in self.files:
            raise FileNotFoundError(f"File {filename} not in archive")
        
        file_info = self.files[filename]
        ext = file_info['type'].lower()
        
        if ext in {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tga'}:
            return self._get_image_info(file_info['content'], ext)
        elif ext in {'mp3', 'wav', 'ogg'}:
            return self._get_audio_info(file_info['content'], ext)
        elif ext in {'mp4', 'avi', 'mov'}:
            return self._get_video_info(file_info['content'], ext)
        else:
            return {'error': 'Unsupported media type'}

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
    
    def insert_text_at_index(self, filename: str, text: str, index: int) -> None:
        """Insert text at specific position in a text file"""
        if filename not in self.files:
            raise FileNotFoundError(f"File {filename} not in archive")
        
        current_content = self.get_file_as_text(filename)
        if current_content is None:
            raise ValueError("File is not a text file")
        
        new_content = current_content[:index] + text + current_content[index:]
        self.add_text_data(filename, new_content)
    def copy_text_block(self, filename: str, start_row: int, start_col: int, 
                       end_row: int, end_col: int) -> str:
        """Extract rectangular text region between coordinates"""
        lines = self.get_text_lines(filename)
        if not (0 <= start_row < len(lines) and 0 <= end_row < len(lines)):
            raise IndexError("Row index out of range")
        
        block = []
        for i in range(start_row, end_row + 1):
            line = lines[i]
            if start_col < len(line) and end_col <= len(line):
                block.append(line[start_col:end_col])
        return '\n'.join(block)
    
    def move_text_block(self, filename: str, start_row: int, start_col: int,
                       end_row: int, end_col: int, dest_row: int, dest_col: int) -> None:
        """Cut text from source region and paste at destination"""
        content = self.copy_text_block(filename, start_row, start_col, end_row, end_col)
        self.remove_text_row_at_index(filename, start_row, start_col, end_col)
        self.insert_text_at_position(filename, content, dest_row, dest_col)
        def truncate_text_row(self, filename: str, start: int, end: int) -> None:
            """Remove text between indices and shift remaining content left"""
            if filename not in self.files:
                raise FileNotFoundError(f"File {filename} not in archive")
            
            current_content = self.get_file_as_text(filename)
            if current_content is None:
                raise ValueError("File is not a text file")
            
            # Shift remaining content left
            new_content = current_content[:start] + current_content[end:]
            self.add_text_data(filename, new_content)
    
    def remove_text_row_at_index(self, filename: str, row: int, col_start: int, col_end: int) -> None:
        """Remove text from specific row/columns without shifting remaining lines"""
        if filename not in self.files:
            raise FileNotFoundError(f"File {filename} not in archive")
        
        lines = self.get_text_lines(filename)
        if row >= len(lines):
            raise IndexError(f"Row {row} out of range")
        
        # Replace specified columns with empty space while preserving line structure
        line = lines[row]
        new_line = line[:col_start] + ' '*(col_end-col_start) + line[col_end:]
        lines[row] = new_line
        
        self.add_text_data(filename, '\n'.join(lines))
    
    def remove_text_column(self, filename: str, col_start: int, col_end: int) -> None:
        """Remove vertical column range from all lines"""
        if filename not in self.files:
            raise FileNotFoundError(f"File {filename} not in archive")
        
        lines = self.get_text_lines(filename)
        modified_lines = []
        
        for line in lines:
            if len(line) > col_start:
                # Preserve line length with spaces if removing middle columns
                new_line = line[:col_start] + (' ' if col_end > col_start else '') + line[col_end:]
            else:
                new_line = line
            modified_lines.append(new_line)
        
        self.add_text_data(filename, '\n'.join(modified_lines))
    
    def insert_text_at_position(self, filename: str, text: str, row: int, col: int) -> None:
        """Insert text at specific row/column position"""
        if filename not in self.files:
            raise FileNotFoundError(f"File {filename} not in archive")
        
        lines = self.get_text_lines(filename)
        
        # Handle row overflow
        while row >= len(lines):
            lines.append('')
        
        # Handle column overflow
        line = lines[row]
        if col > len(line):
            line += ' ' * (col - len(line))
        
        lines[row] = line[:col] + text + line[col:]
        self.add_text_data(filename, '\n'.join(lines))
    
    # Additional quality-of-life functions
    def append_text(self, filename: str, text: str) -> None:
        """Append text to an existing file"""
        if filename not in self.files:
            raise FileNotFoundError(f"File {filename} not in archive")
        
        current_content = self.get_file_as_text(filename) or ""
        self.add_text_data(filename, current_content + text)
    
    def prepend_text(self, filename: str, text: str) -> None:
        """Prepend text to an existing file"""
        if filename not in self.files:
            raise FileNotFoundError(f"File {filename} not in archive")
        
        current_content = self.get_file_as_text(filename) or ""
        self.add_text_data(filename, text + current_content)
    
    def replace_text(self, filename: str, old: str, new: str) -> None:
        """Replace all occurrences of text in a file"""
        if filename not in self.files:
            raise FileNotFoundError(f"File {filename} not in archive")
        
        current_content = self.get_file_as_text(filename)
        if current_content is None:
            raise ValueError("File is not a text file")
        
        self.add_text_data(filename, current_content.replace(old, new))
    
    def get_text_lines(self, filename: str) -> List[str]:
        """Get text file content as lines"""
        content = self.get_file_as_text(filename)
        if content is None:
            raise ValueError("File is not a text file")
        return content.splitlines()
    
    def update_json_value(self, filename: str, key: str, value: Any) -> None:
        """Update a value in a JSON file"""
        if filename not in self.files:
            raise FileNotFoundError(f"File {filename} not in archive")
        
        try:
            data = json.loads(self.get_file_as_text(filename))
            data[key] = value
            self.add_dict_as_json(filename, data)
        except json.JSONDecodeError:
            raise ValueError("File is not valid JSON")

    def add_binary_data(self, filename: str, binary_data: bytes, file_type: str = None) -> None:
        """Add binary data directly to the archive"""
        if file_type is None:
            file_type = filename.split('.')[-1] if '.' in filename else 'bin'
        self.add_file(filename, binary_data, file_type)
    
    def get_binary_data(self, filename: str) -> dict:
        """Get raw binary data and file info"""
        if filename not in self.files:
            raise FileNotFoundError(f"File {filename} not in archive")
        return {
            'data': self.get_file(filename),
            'type': self.files[filename]['type'],
            'size': len(self.files[filename]['content'])
        }

    def add_font(self, name: str, font_data: bytes) -> None:
        """Add font file with validation"""
        ext = name.split('.')[-1].lower()
        if ext not in {'ttf', 'otf', 'woff', 'woff2'}:
            raise ValueError(f"Unsupported font format: {ext}")
        
        if not self._validate_font_file(font_data, ext):
            raise ValueError(f"Invalid {ext.upper()} font file")
        
        metadata = self._extract_font_metadata(font_data, ext)
        self.add_file(name, font_data, ext, metadata=metadata)
    
    def add_image(self, name: str, image_data: bytes) -> None:
        """Add image with format validation and metadata extraction"""
        ext = name.split('.')[-1].lower()
        if ext not in {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tga'}:
            raise ValueError(f"Unsupported image format: {ext}")
        
        if not self.validate_media_file(image_data, ext):
            raise ValueError(f"Invalid {ext.upper()} file structure")
        
        metadata = self._extract_image_metadata(image_data, ext)
        self.add_file(name, image_data, ext, metadata=metadata)
    
    def get_image_data(self, name: str) -> dict:
        """Get raw image bytes and metadata"""
        if name not in self.files:
            raise FileNotFoundError(f"File {name} not in archive")
        ext = self.files[name]['type'].lower()
        return {
            'data': self.get_file(name),
            'metadata': self._get_image_info(self.files[name]['content'], ext)
        }
    
    def get_audio_data(self, name: str) -> dict:
        """Get raw audio bytes and metadata"""
        if name not in self.files:
            raise FileNotFoundError(f"File {name} not in archive")
        ext = self.files[name]['type'].lower()
        return {
            'data': self.get_file(name),
            'metadata': self._get_audio_info(self.files[name]['content'], ext)
        }
    
    def get_video_data(self, name: str) -> dict:
        """Get raw video bytes and metadata"""
        if name not in self.files:
            raise FileNotFoundError(f"File {name} not in archive")
        ext = self.files[name]['type'].lower()
        return {
            'data': self.get_file(name),
            'metadata': self._get_video_info(self.files[name]['content'], ext)
        }
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

    def get_font(self, identifier: str) -> Optional[bytes]:
        """
        Get font by filename or path
        Returns raw font data or None if not found
        """
        # Try direct filename match first
        if identifier in self.files:
            return self.get_file(identifier)
        
        # Try path-based lookup (case insensitive)
        identifier_lower = identifier.lower()
        for name in self.files:
            if name.lower() == identifier_lower or name.lower().endswith(identifier_lower):
                return self.get_file(name)
        
        return None
    
    def get_all_fonts(self) -> Dict[str, dict]:
        """Return all fonts in archive with both file data and metadata
        
        Returns:
            Dictionary with:
            - Key: Font filename
            - Value: Dictionary containing:
                * 'data': Raw font bytes (from get_file())
                * 'type': File extension
                * 'metadata': Extracted font metadata
        """
        fonts = {}
        for name, info in self.files.items():
            if info['type'].lower() in {'ttf', 'otf', 'woff', 'woff2'}:
                fonts[name] = {
                    'data': self.get_file(name),  # Using get_file() instead of direct access
                    'type': info['type'],
                    'metadata': info.get('metadata', {})
                }
        return fonts
    
    def get_font_details(self, identifier: str) -> Dict[str, Any]:
        """Get detailed metadata for specific font"""
        font_data = self.get_font(identifier)
        if not font_data:
            raise FileNotFoundError(f"Font {identifier} not found in archive")
        
        ext = identifier.split('.')[-1].lower()
        return self._extract_font_metadata(font_data, ext)
    
    # ======================
    # Internal Font Handlers
    # ======================
    
    def _validate_font_file(self, data: bytes, ext: str) -> bool:
        """Validate font file signatures"""
        signatures = {
            'ttf': b'\x00\x01\x00\x00',
            'otf': b'OTTO',
            'woff': b'wOFF',
            'woff2': b'wOF2'
        }
        return data.startswith(signatures.get(ext, b''))
    
    def _extract_font_metadata(self, data: bytes, ext: str) -> Dict[str, Any]:
        """Extract basic font metadata"""
        metadata = {'type': 'font', 'format': ext}
        
        try:
            if ext in ('ttf', 'otf'):
                # Parse SFNT tables (common to TTF/OTF)
                num_tables = struct.unpack('>H', data[4:6])[0]
                metadata['tables'] = num_tables
                
                # Look for name table (contains font names)
                for i in range(num_tables):
                    offset = 12 + i*16
                    tag = data[offset:offset+4].decode('ascii', errors='ignore')
                    if tag == 'name':
                        name_offset = struct.unpack('>I', data[offset+8:offset+12])[0]
                        break
                
                # Basic name extraction (simplified)
                if 'name_offset' in locals():
                    name_count = struct.unpack('>H', data[name_offset+2:name_offset+4])[0]
                    metadata['names'] = name_count
            
            elif ext == 'woff':
                metadata['flavor'] = data[8:12].decode('ascii', errors='ignore')
            
            # Add file size
            metadata['size'] = len(data)
            
        except:
            pass  # Return basic info if parsing fails
        
        return metadata
