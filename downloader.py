import os
import yt_dlp
import random
import tempfile
import requests
import time
from pathlib import Path
import logging

class YouTubeDownloader:
    def __init__(self):
        # Configure yt-dlp logger to suppress specific warnings
        self._configure_logger()
        
        self.formats = []
        self.progress_callback = None
        self.should_cancel = False
        # Common user agents to simulate real browsers
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/121.0.0.0 Safari/537.36',
        ]
        # Create temp directory for cookies
        self.temp_dir = tempfile.mkdtemp()
        self.cookies_file = os.path.join(self.temp_dir, 'cookies.txt')
        # Create empty cookies file
        Path(self.cookies_file).touch()
        # Get YouTube home page to obtain cookies
        self._get_youtube_cookies()
    
    def _configure_logger(self):
        """Configure yt-dlp logger to suppress specific warnings"""
        # Create custom filter to ignore specific warnings
        class WarningFilter(logging.Filter):
            def filter(self, record):
                # Filter out the specific warning messages we want to hide
                message = record.getMessage()
                if any(warning in message for warning in [
                    "Skipping unsupported client",
                    "android client https formats require a GVS PO Token",
                    "You have asked for UNPLAYABLE formats",
                ]):
                    return False
                return True
        
        # Apply the filter to the yt-dlp logger
        ytdlp_logger = logging.getLogger("yt_dlp")
        ytdlp_logger.addFilter(WarningFilter())
        
        # Set up handler if none exists
        if not ytdlp_logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
            ytdlp_logger.addHandler(handler)
    
    def _get_youtube_cookies(self):
        """Get YouTube cookies to use with requests"""
        try:
            user_agent = self.get_random_user_agent()
            headers = {
                'User-Agent': user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
            }
            
            session = requests.Session()
            session.headers.update(headers)
            
            # Visit YouTube homepage to get cookies
            response = session.get('https://www.youtube.com/')
            
            # Write cookies to file in Netscape format
            with open(self.cookies_file, 'w') as f:
                f.write("# Netscape HTTP Cookie File\n")
                for cookie in session.cookies:
                    f.write(f".youtube.com\tTRUE\t/\tFALSE\t{int(time.time()) + 3600*24*30}\t{cookie.name}\t{cookie.value}\n")
            
            return True
        except Exception as e:
            print(f"Error getting YouTube cookies: {e}")
            return False
    
    def get_random_user_agent(self):
        """Get a random user agent to avoid detection"""
        return random.choice(self.user_agents)
    
    def set_progress_callback(self, callback):
        """Set callback function for progress updates"""
        self.progress_callback = callback
    
    def cancel_download(self):
        """Cancel ongoing download"""
        self.should_cancel = True
    
    def reset_cancel_flag(self):
        """Reset download cancellation flag"""
        self.should_cancel = False
    
    def get_video_info(self, url):
        """Get video information without downloading"""
        self.formats = []
        
        # Enhanced options for 2025.03.26 version
        ydl_opts = {
            'quiet': False,  # Changed to allow logging
            'no_warnings': True,  # Suppress warnings via the logger
            'ignoreerrors': True,
            'cookiefile': self.cookies_file,
            'no_color': True,
            'geo_bypass': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web', 'mobile'],
                    'player_skip': [],  # Don't skip any player extraction
                    'formats': 'missing_pot'  # Allow formats even if PO token is missing
                }
            },
            'socket_timeout': 30,
            'user_agent': self.get_random_user_agent(),
            'http_headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Origin': 'https://www.youtube.com',
                'Referer': 'https://www.youtube.com/'
            },
            'logger': logging.getLogger("yt_dlp")  # Use our configured logger
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    return False, "Could not retrieve video information. The video may be unavailable or restricted.", []
                
                # Get available formats
                format_items = ["best", "1080p", "720p", "480p", "360p", "audio only"]
                
                if 'formats' in info:
                    for f in info['formats']:
                        format_id = f.get('format_id', '')
                        extension = f.get('ext', '')
                        resolution = f.get('resolution', 'N/A')
                        note = f.get('format_note', '')
                        
                        if note or resolution != 'N/A':
                            format_str = f"{format_id} - {extension} - {resolution} - {note}"
                            self.formats.append({
                                'id': format_id, 
                                'ext': extension,
                                'resolution': resolution,
                                'note': note,
                                'str': format_str
                            })
                            format_items.append(format_str)
                
                return True, info, format_items
        except yt_dlp.utils.DownloadError as e:
            error_message = str(e)
            if "HTTP Error 429" in error_message:
                return False, "YouTube rate limit exceeded. Please try again later.", []
            elif "HTTP Error 403" in error_message:
                return False, "Access forbidden. YouTube may be blocking this request.", []
            elif "Precondition check failed" in error_message:
                return False, "YouTube API error. Try updating yt-dlp or try a different video.", []
            elif "This video is unavailable" in error_message:
                return False, "This video is unavailable or may be private.", []
            else:
                return False, f"Error: {error_message}", []
        except Exception as e:
            return False, f"Error: {str(e)}", []
    
    def download_video(self, url, output_path, format_choice, filename_template="%(title)s"):
        """Download YouTube video using yt-dlp with custom filename template"""
        # Determine format based on selection
        if format_choice == "audio only":
            format_option = "bestaudio[ext=m4a]/bestaudio/best"
        elif format_choice in ["best", "1080p", "720p", "480p", "360p"]:
            if format_choice == "best":
                format_option = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
            else:
                height = format_choice[:-1]
                format_option = f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}][ext=mp4]/best"
        else:
            # User selected specific format from the list
            for fmt in self.formats:
                if fmt['str'] == format_choice:
                    format_option = fmt['id']
                    break
            else:
                format_option = "best"
        
        # Set output template
        outtmpl = os.path.join(output_path, f"{filename_template}.%(ext)s")
        
        # Enhanced options for version 2025.03.26
        options = {
            'format': format_option,
            'outtmpl': outtmpl,
            'cookiefile': self.cookies_file,
            'progress_hooks': [self.progress_hook],
            'quiet': True,
            'no_warnings': False,
            'ignoreerrors': True,
            'no_color': True,
            'geo_bypass': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web', 'mobile'],
                    'player_skip': [],
                    'formats': 'missing_pot'  # Allow formats even if PO token is missing
                }
            },
            'socket_timeout': 30,
            'user_agent': self.get_random_user_agent(),
            'http_chunk_size': 1048576,  # 1MB chunks
            'youtube_include_dash_manifest': False,
            'http_headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Origin': 'https://www.youtube.com',
                'Referer': 'https://www.youtube.com/'
            },
            'retry_sleep_functions': {
                'http': lambda x: 10 if x > 5 else 5,
            },
            'retries': 15,
            'fragment_retries': 15,
            'concurrent_fragment_downloads': 1,
            'merge_output_format': 'mp4',
            'allow_unplayable_formats': True  # New in recent yt-dlp versions
        }
        
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                self.reset_cancel_flag()
                ydl.download([url])
                if not self.should_cancel:
                    return True, "Download completed successfully."
                else:
                    return False, "Download was canceled."
        except yt_dlp.utils.DownloadError as e:
            error_message = str(e)
            if "HTTP Error 429" in error_message:
                return False, "YouTube rate limit exceeded. Please try again later."
            elif "HTTP Error 403" in error_message:
                # Try with different format after 403 error
                return self._try_alternative_download(url, output_path, filename_template)
            elif "fragment" in error_message and "not found" in error_message:
                # Try with different HTTP chunk size
                return self._try_alternative_download(url, output_path, filename_template, smaller_chunks=True)
            elif "Precondition check failed" in error_message:
                return False, "YouTube API error. This may be temporary, please try again later."
            else:
                return False, f"Download error: {error_message}"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def _try_alternative_download(self, url, output_path, filename_template="%(title)s", smaller_chunks=False):
        """Try alternative download approach after a failure"""
        # Set output template
        outtmpl = os.path.join(output_path, f"{filename_template}.%(ext)s")
        
        # Different options for a second attempt - optimized for 2025.03.26
        options = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': outtmpl,
            'cookiefile': self.cookies_file,
            'progress_hooks': [self.progress_hook],
            'quiet': True,
            'ignoreerrors': True,
            'geo_bypass': True,
            'user_agent': self.get_random_user_agent(),
            'http_chunk_size': 262144 if smaller_chunks else 524288,  # Smaller chunks
            'retries': 20,
            'fragment_retries': 20,
            'hls_prefer_native': True,
            'concurrent_fragment_downloads': 1,
            'allow_unplayable_formats': True,
            'extractor_retries': 10,
            'file_access_retries': 10
        }
        
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                self.reset_cancel_flag()
                ydl.download([url])
                if not self.should_cancel:
                    return True, "Download completed successfully (using alternative method)."
                else:
                    return False, "Download was canceled."
        except Exception as e:
            return False, f"Alternative download method failed: {str(e)}"
    
    def download_playlist(self, url, output_path, format_choice, filename_template="%(title)s"):
        """Download YouTube playlist"""
        # First, get playlist information
        try:
            # Set options for playlist detection
            info_options = {
                'quiet': True,
                'no_warnings': False,
                'extract_flat': True,
                'playlist_items': '1-999',  # Limit to reasonable number
                'cookiefile': self.cookies_file,
                'user_agent': self.get_random_user_agent(),
            }
            
            with yt_dlp.YoutubeDL(info_options) as ydl:
                info_result = ydl.extract_info(url, download=False)
                
                if not info_result:
                    return False, "Unable to retrieve playlist information."
                
                # Check if it's a playlist
                if 'entries' not in info_result:
                    return False, "The URL doesn't seem to be a playlist."
                
                playlist_title = info_result.get('title', 'Playlist')
                
                # Create folder for playlist
                playlist_folder = os.path.join(output_path, self._sanitize_filename(playlist_title))
                if not os.path.exists(playlist_folder):
                    os.makedirs(playlist_folder)
                
                # Include playlist info in the template
                download_template = f"{filename_template}"
                
                # Add index number to avoid filename conflicts
                outtmpl = os.path.join(playlist_folder, f"%(playlist_index)s-{download_template}.%(ext)s")
                
                # Setup options for downloading
                download_options = {
                    'format': self._get_format_option(format_choice),
                    'outtmpl': outtmpl,
                    'cookiefile': self.cookies_file,
                    'progress_hooks': [self.progress_hook],
                    'quiet': True,
                    'no_warnings': False,
                    'ignoreerrors': True,
                    'no_color': True,
                    'geo_bypass': True,
                    'socket_timeout': 30,
                    'user_agent': self.get_random_user_agent(),
                    'http_chunk_size': 1048576,
                    'retries': 15,
                    'fragment_retries': 15,
                    'allow_unplayable_formats': True,
                    'extractor_args': {
                        'youtube': {
                            'player_client': ['android', 'web', 'mobile'],
                            'player_skip': [],
                            'formats': 'missing_pot'  # Allow formats even if PO token is missing
                        }
                    }
                }
                
                self.reset_cancel_flag()
                
                # Download playlist
                with yt_dlp.YoutubeDL(download_options) as ydl:
                    ydl.download([url])
                    
                    if self.should_cancel:
                        return False, "Playlist download was canceled."
                    else:
                        return True, f"Playlist '{playlist_title}' downloaded successfully."
                        
        except yt_dlp.utils.DownloadError as e:
            return False, f"Playlist download error: {str(e)}"
        except Exception as e:
            return False, f"Error downloading playlist: {str(e)}"
    
    def _sanitize_filename(self, name):
        """Remove invalid characters from filename"""
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in invalid_chars:
            name = name.replace(char, '_')
        return name
    
    def _get_format_option(self, format_choice):
        """Get format option string based on user selection"""
        if format_choice == "audio only":
            return "bestaudio[ext=m4a]/bestaudio/best"
        elif format_choice == "best":
            return "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        elif format_choice in ["1080p", "720p", "480p", "360p"]:
            height = format_choice[:-1]
            return f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}][ext=mp4]/best"
        else:
            # User selected specific format from the list
            for fmt in self.formats:
                if fmt['str'] == format_choice:
                    return fmt['id']
            return "best"
    
    def progress_hook(self, d):
        """Handle progress updates from yt-dlp"""
        if self.should_cancel:
            raise Exception("Download canceled by user")
        
        if self.progress_callback:
            self.progress_callback(d)
    
    def download_video_with_callback(self, url, output_path, format_choice, filename_template="%(title)s", progress_callback=None):
        """Download YouTube video using yt-dlp with custom filename template and specific callback"""
        # Store current callback
        original_callback = self.progress_callback
        
        # Set temporary callback
        if progress_callback:
            self.progress_callback = progress_callback
        
        try:
            # Use the normal download method
            result = self.download_video(url, output_path, format_choice, filename_template)
            
            # Restore original callback
            self.progress_callback = original_callback
            
            return result
        except Exception as e:
            # Restore original callback in case of error
            self.progress_callback = original_callback
            return False, f"Error: {str(e)}"
