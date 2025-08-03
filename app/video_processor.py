import subprocess
import os
import tempfile
from flask import current_app
import logging
import qrcode
from PIL import Image
import io

logger = logging.getLogger(__name__)

class VideoProcessor:
    """Handle video processing operations like watermarking"""
    
    @staticmethod
    def add_watermark(input_path, output_path, watermark_text="PromptToVideo.com", qr_url=None):
        """
        Add watermark to video using FFmpeg
        
        Args:
            input_path: Path to input video file
            output_path: Path to output video file
            watermark_text: Text to use as watermark (deprecated - only QR codes supported)
            qr_url: URL to encode in QR code (required)
        """
        try:
            if qr_url:
                # Create QR code watermark
                logger.info(f"🎯 Using QR code watermark with URL: {qr_url}")
                return VideoProcessor._add_qr_watermark(input_path, output_path, qr_url)
            else:
                # No watermark - just copy the video
                logger.info(f"⚠️ No QR URL provided, skipping watermark")
                import shutil
                shutil.copy2(input_path, output_path)
                return True
                
        except Exception as e:
            logger.error(f"Error adding watermark: {str(e)}")
            raise
    
    @staticmethod
    def _add_qr_watermark(input_path, output_path, qr_url):
        """Add QR code watermark to video"""
        logger.info(f"🎯 Starting QR watermark process...")
        logger.info(f"📁 Input path: {input_path}")
        logger.info(f"📁 Output path: {output_path}")
        logger.info(f"🔗 QR URL: {qr_url}")
        
        try:
            # Get FFmpeg path
            ffmpeg_path = VideoProcessor._get_ffmpeg_path()
            
            # Generate QR code image
            logger.info(f"🔧 Generating QR code image...")
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_url)
            qr.make(fit=True)
            
            # Create QR code image
            qr_img = qr.make_image(fill_color="black", back_color="white")
            logger.info(f"✅ QR code image created, size: {qr_img.size}")
            
            # Resize QR code to medium size (120x120 pixels)
            qr_img = qr_img.resize((120, 120), Image.Resampling.LANCZOS)
            logger.info(f"✅ QR code resized to 120x120")
            
            # Add white background with transparency
            background = Image.new('RGBA', (140, 140), (255, 255, 255, 200))
            background.paste(qr_img, (10, 10))
            logger.info(f"✅ Background added with transparency")
            
            # Save QR code to temporary file
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_qr:
                background.save(temp_qr.name, 'PNG')
                qr_path = temp_qr.name
            
            logger.info(f"📁 QR code saved to: {qr_path}")
            logger.info(f"📊 QR file size: {os.path.getsize(qr_path)} bytes")
            
            try:
                # Add QR code to video using FFmpeg
                filter_complex = f"overlay=x=W-w-20:y=20:format=auto"
                
                cmd = [
                    ffmpeg_path,
                    '-i', input_path,
                    '-i', qr_path,
                    '-filter_complex', filter_complex,
                    '-c:a', 'copy',  # Copy audio without re-encoding
                    '-y',  # Overwrite output file
                    output_path
                ]
                
                logger.info(f"🎬 Running FFmpeg QR watermark command...")
                logger.info(f"🔧 FFmpeg path: {ffmpeg_path}")
                logger.info(f"🔧 Command: {' '.join(cmd)}")
                
                # Run FFmpeg command
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                
                logger.info(f"🎬 FFmpeg return code: {result.returncode}")
                if result.stdout:
                    logger.info(f"🎬 FFmpeg stdout: {result.stdout[:200]}...")
                if result.stderr:
                    logger.info(f"🎬 FFmpeg stderr: {result.stderr[:200]}...")
                
                if result.returncode != 0:
                    logger.error(f"❌ FFmpeg QR watermark failed: {result.stderr}")
                    raise Exception(f"FFmpeg QR watermark processing failed: {result.stderr}")
                
                # Check if output file was created
                if os.path.exists(output_path):
                    output_size = os.path.getsize(output_path)
                    logger.info(f"✅ QR code watermark added successfully to {output_path}")
                    logger.info(f"📊 Output file size: {output_size} bytes")
                    return True
                else:
                    logger.error(f"❌ Output file was not created: {output_path}")
                    return False
                
            finally:
                # Clean up temporary QR code file
                if os.path.exists(qr_path):
                    os.unlink(qr_path)
                    logger.info(f"🧹 Cleaned up temporary QR file")
                    
        except Exception as e:
            logger.error(f"❌ Error adding QR watermark: {str(e)}")
            logger.error(f"❌ Error type: {type(e).__name__}")
            import traceback
            logger.error(f"❌ Full traceback: {traceback.format_exc()}")
            raise
    
    @staticmethod
    def _add_text_watermark(input_path, output_path, watermark_text):
        """Add text watermark to video (fallback method)"""
        try:
            # Simple watermark using colored rectangles instead of text
            # This avoids font configuration issues on Windows
            filter_complex = (
                # Corner badge (top-right)
                "drawbox=x=iw-80:y=10:w=70:h=25:color=black@0.7:t=fill,"
                # Bottom attribution (bottom-left)
                "drawbox=x=10:y=ih-35:w=150:h=25:color=black@0.5:t=fill"
            )
            
            cmd = [
                ffmpeg_path,
                '-i', input_path,
                '-vf', filter_complex,
                '-c:a', 'copy',  # Copy audio without re-encoding
                '-y',  # Overwrite output file
                output_path
            ]
            
            logger.info(f"Running FFmpeg text watermark command: {' '.join(cmd)}")
            
            # Run FFmpeg command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                logger.error(f"FFmpeg text watermark failed: {result.stderr}")
                raise Exception(f"FFmpeg text watermark processing failed: {result.stderr}")
            
            logger.info(f"Text watermark added successfully to {output_path}")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg text watermark processing timed out")
            raise Exception("Video processing timed out")
        except Exception as e:
            logger.error(f"Error adding text watermark: {str(e)}")
            raise
    
    @staticmethod
    def _get_ffmpeg_path():
        """Get the path to FFmpeg executable"""
        import os
        
        # Common FFmpeg installation paths on Windows
        possible_paths = [
            'ffmpeg',  # Try PATH first
            os.path.expanduser('~/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-7.1.1-full_build/bin/ffmpeg.exe'),
            'C:/Program Files/ffmpeg/bin/ffmpeg.exe',
            'C:/ffmpeg/bin/ffmpeg.exe',
        ]
        
        for path in possible_paths:
            try:
                result = subprocess.run(
                    [path, '-version'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    logger.info(f"Found FFmpeg at: {path}")
                    return path
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        raise Exception("FFmpeg not found in any of the expected locations")
    
    @staticmethod
    def check_ffmpeg_available():
        """Check if FFmpeg is available on the system"""
        try:
            VideoProcessor._get_ffmpeg_path()
            return True
        except Exception:
            return False
    
    @staticmethod
    def get_video_info(video_path):
        """Get video information using FFprobe"""
        try:
            # Get FFmpeg path and construct ffprobe path
            ffmpeg_path = VideoProcessor._get_ffmpeg_path()
            ffprobe_path = ffmpeg_path.replace('ffmpeg.exe', 'ffprobe.exe')
            
            cmd = [
                ffprobe_path,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                video_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"FFprobe failed: {result.stderr}")
                return None
            
            import json
            return json.loads(result.stdout)
            
        except Exception as e:
            logger.error(f"Error getting video info: {str(e)}")
            return None
    
    @staticmethod
    def generate_thumbnail(video_path, output_path, time_offset="00:00:05"):
        """
        Generate thumbnail from video
        
        Args:
            video_path: Path to input video
            output_path: Path to output thumbnail
            time_offset: Time offset for thumbnail (default: 5 seconds)
        """
        try:
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-ss', time_offset,
                '-vframes', '1',
                '-q:v', '2',
                '-y',
                output_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"Thumbnail generation failed: {result.stderr}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error generating thumbnail: {str(e)}")
            return False 