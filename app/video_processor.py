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
            # Temporarily disable QR code watermark due to performance issues
            # Just copy the video without watermark for now
            logger.info(f"⚠️ QR code watermark temporarily disabled for performance")
            logger.info(f"📋 Copying video without watermark: {input_path} -> {output_path}")
            import shutil
            shutil.copy2(input_path, output_path)
            logger.info(f"✅ Video copied successfully without watermark")
            return True
                
        except Exception as e:
            logger.error(f"Error copying video: {str(e)}")
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
            
            # Generate QR code image with optimized settings
            logger.info(f"🔧 Generating optimized QR code image...")
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=8,  # Reduced box size for faster generation
                border=2,    # Reduced border for smaller file
            )
            qr.add_data(qr_url)
            qr.make(fit=True)
            
            # Create QR code image
            qr_img = qr.make_image(fill_color="black", back_color="white")
            logger.info(f"✅ QR code image created, size: {qr_img.size}")
            
            # Resize QR code to smaller size (100x100 pixels) for faster processing
            qr_img = qr_img.resize((100, 100), Image.Resampling.NEAREST)  # Use NEAREST for speed
            logger.info(f"✅ QR code resized to 100x100")
            
            # Add white background with transparency (smaller size)
            background = Image.new('RGBA', (120, 120), (255, 255, 255, 180))  # Reduced transparency
            background.paste(qr_img, (10, 10))
            logger.info(f"✅ Background added with transparency")
            
            # Save QR code to temporary file
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_qr:
                background.save(temp_qr.name, 'PNG')
                qr_path = temp_qr.name
            
            logger.info(f"📁 QR code saved to: {qr_path}")
            logger.info(f"📊 QR file size: {os.path.getsize(qr_path)} bytes")
            
            try:
                # Add QR code to video using FFmpeg with optimized settings
                # Use a simpler overlay filter and optimize for speed
                filter_complex = f"overlay=x=W-w-20:y=20"
                
                cmd = [
                    ffmpeg_path,
                    '-i', input_path,
                    '-i', qr_path,
                    '-filter_complex', filter_complex,
                    '-c:v', 'libx264',  # Use H.264 codec for better compatibility
                    '-preset', 'ultrafast',  # Use fastest encoding preset
                    '-crf', '23',  # Good quality with reasonable file size
                    '-c:a', 'copy',  # Copy audio without re-encoding
                    '-y',  # Overwrite output file
                    output_path
                ]
                
                logger.info(f"🎬 Running optimized FFmpeg QR watermark command...")
                logger.info(f"🔧 FFmpeg path: {ffmpeg_path}")
                logger.info(f"🔧 Command: {' '.join(cmd)}")
                
                # Run FFmpeg command with shorter timeout
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=180  # 3 minute timeout (reduced from 5)
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
            
            # Fallback: try to copy the video without watermark
            logger.info(f"🔄 Attempting fallback: copying video without watermark...")
            try:
                import shutil
                shutil.copy2(input_path, output_path)
                logger.info(f"✅ Fallback successful: video copied without watermark")
                return True
            except Exception as fallback_error:
                logger.error(f"❌ Fallback also failed: {fallback_error}")
                raise e  # Re-raise the original error
    
    @staticmethod
    def _add_text_watermark(input_path, output_path, watermark_text):
        """Add text watermark to video (fallback method)"""
        try:
            # Get FFmpeg path
            ffmpeg_path = VideoProcessor._get_ffmpeg_path()
            
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
        
        # Common FFmpeg installation paths (Windows, Linux, Cloud Run)
        possible_paths = [
            'ffmpeg',  # Try PATH first
            '/usr/bin/ffmpeg',  # Linux/Cloud Run
            '/usr/local/bin/ffmpeg',  # Linux/Cloud Run
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
                logger.debug(f"FFmpeg not found at: {path}")
                continue
        
        # If we get here, try to find ffmpeg in PATH using which/where
        try:
            if os.name == 'nt':  # Windows
                result = subprocess.run(['where', 'ffmpeg'], capture_output=True, text=True, timeout=10)
            else:  # Linux/Mac
                result = subprocess.run(['which', 'ffmpeg'], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                ffmpeg_path = result.stdout.strip().split('\n')[0]
                logger.info(f"Found FFmpeg in PATH at: {ffmpeg_path}")
                return ffmpeg_path
        except Exception as e:
            logger.debug(f"Could not find ffmpeg in PATH: {e}")
        
        raise Exception("FFmpeg not found in any of the expected locations. Please ensure FFmpeg is installed and available in PATH.")
    
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
            # Get FFmpeg path
            ffmpeg_path = VideoProcessor._get_ffmpeg_path()
            
            # Optimized command for faster thumbnail generation
            cmd = [
                ffmpeg_path,
                '-i', video_path,
                '-ss', time_offset,
                '-vframes', '1',
                '-vf', 'scale=320:180:force_original_aspect_ratio=decrease,pad=320:180:(ow-iw)/2:(oh-ih)/2',
                '-q:v', '3',  # Slightly lower quality for faster processing
                '-y',
                output_path
            ]
            
            logger.info(f"🎬 Running optimized thumbnail generation command...")
            logger.info(f"📁 Input: {video_path}")
            logger.info(f"📁 Output: {output_path}")
            logger.info(f"⏰ Time offset: {time_offset}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # Increased timeout to 2 minutes
            )
            
            if result.returncode != 0:
                logger.error(f"Thumbnail generation failed: {result.stderr}")
                return False
            
            # Verify the output file was created and has content
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"✅ Thumbnail generated successfully: {output_path}")
                logger.info(f"📊 Thumbnail size: {os.path.getsize(output_path)} bytes")
                return True
            else:
                logger.error(f"Thumbnail file not created or empty: {output_path}")
                return False
            
        except subprocess.TimeoutExpired:
            logger.error(f"Thumbnail generation timed out after 120 seconds")
            return False
        except Exception as e:
            logger.error(f"Error generating thumbnail: {str(e)}")
            return False 