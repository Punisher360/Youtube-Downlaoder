import os
import threading
import time
import dearpygui.dearpygui as dpg
from datetime import datetime
import webbrowser
import shutil

class YouTubeDownloaderGUI:
    def __init__(self, downloader):
        # Store downloader instance
        self.downloader = downloader
        
        # Set progress callback
        self.downloader.set_progress_callback(self.progress_hook)
        
        # Initialize DearPyGUI
        dpg.create_context()
        
        # Application variables
        self.download_path = os.path.expanduser("~/Downloads")
        self.is_downloading = False
        self.download_history = []
        self.download_speed = "0 KB/s"
        self.estimated_time = "Unknown"
        self.last_downloaded_bytes = 0
        self.last_time = time.time()
        self.info_output_path = self.download_path  # New variable for info output path
        self.is_gathering_info = False  # New state variable for info gathering
        self.settings = {
            "theme": "dark",
            "autoplay_preview": False,
            "filename_template": "%(title)s",
            "downloads_folder": self.download_path
        }
        
        # Load settings if available
        self.load_settings()
        
        # Create GUI
        self.create_gui()
    
    def save_settings(self):
        """Save user settings to file"""
        settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.txt")
        try:
            with open(settings_file, "w") as f:
                for key, value in self.settings.items():
                    f.write(f"{key}={value}\n")
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def load_settings(self):
        """Load user settings from file"""
        settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.txt")
        try:
            if os.path.exists(settings_file):
                with open(settings_file, "r") as f:
                    for line in f:
                        if "=" in line:
                            key, value = line.strip().split("=", 1)
                            if key in self.settings:
                                # Handle boolean values
                                if value.lower() == "true":
                                    value = True
                                elif value.lower() == "false":
                                    value = False
                                self.settings[key] = value
                
                # Update download path from settings
                if "downloads_folder" in self.settings:
                    folder = self.settings["downloads_folder"]
                    if os.path.exists(folder):
                        self.download_path = folder
        except Exception as e:
            print(f"Error loading settings: {e}")
    
    def create_gui(self):
        # Create viewport
        dpg.create_viewport(title="YouTube Downloader", width=900, height=700)
        
        # Set theme based on settings
        self.set_theme(self.settings["theme"])
        
        # Main window
        with dpg.window(tag="Primary Window"):
            # Create tabs for different sections
            with dpg.tab_bar(tag="main_tabs"):
                # Downloader Tab
                with dpg.tab(label="Downloader", tag="downloader_tab"):
                    self.create_downloader_tab()
                
                # Batch Download Tab
                with dpg.tab(label="Batch Download", tag="batch_tab"):
                    self.create_batch_tab()
                
                # Video Info Gatherer Tab - Adding a specific tag and default_open=True to make it visible
                with dpg.tab(label="Video Info Gatherer", tag="info_gatherer_tab"):
                    self.create_info_gatherer_tab()
                
                # History Tab
                with dpg.tab(label="Download History", tag="history_tab"):
                    self.create_history_tab()
                
                # Settings Tab
                with dpg.tab(label="Settings", tag="settings_tab"):
                    self.create_settings_tab()
                
                # About Tab
                with dpg.tab(label="About", tag="about_tab"):
                    self.create_about_tab()
            
        # Create context menu for download history
        with dpg.handler_registry():
            dpg.add_key_press_handler(dpg.mvKey_Delete, callback=self.delete_selected_history)

    def create_downloader_tab(self):
        """Create the main downloader interface"""
        with dpg.group():
            # Header
            with dpg.group(horizontal=True):
                dpg.add_text("YouTube Downloader", color=[255, 0, 0])
                dpg.add_spacer(width=10)
                dpg.add_button(label="Clear", callback=self.clear_form, width=80)
            
            # URL input row
            with dpg.group(horizontal=True):
                dpg.add_input_text(label="YouTube URL", tag="url_input", width=550)
                dpg.add_button(label="Get Info", callback=self.on_info_click, width=100)
                dpg.add_button(label="Paste", callback=self.paste_url, width=80)
            
            # Video info section
            with dpg.group():
                # Video details
                with dpg.group():
                    dpg.add_text("Title: ", tag="video_title", wrap=550)
                    dpg.add_text("Duration: ", tag="video_duration")
                    dpg.add_text("Channel: ", tag="video_channel")
                    dpg.add_text("Upload Date: ", tag="video_upload_date")
                    
                    # Format selection
                    with dpg.group(horizontal=True):
                        dpg.add_text("Format:")
                        dpg.add_combo(
                            items=["best", "1080p", "720p", "480p", "360p", "audio only"],
                            default_value="best",
                            tag="format_combo",
                            width=300
                        )
                
                # Estimated download size
                dpg.add_text("Estimated Size: Unknown", tag="estimated_size")
            
            # Download location
            with dpg.group(horizontal=True):
                dpg.add_button(label="Select Download Folder", callback=self.select_directory, width=200)
                dpg.add_text("Download folder: " + self.download_path, tag="directory", wrap=650)
            
            # Download controls
            with dpg.group(horizontal=True):
                dpg.add_button(label="Download", callback=self.on_download_click, width=150, height=30, tag="download_button")
                dpg.add_button(label="Cancel", callback=self.on_cancel_click, width=150, height=30, tag="cancel_button", enabled=False)
                dpg.add_button(label="Open Download Folder", callback=self.open_download_folder, width=180, height=30)
            dpg.add_separator()
            
            # Status and progress section
            with dpg.group():
                dpg.add_text("Status: Ready", tag="status")
                dpg.add_text("", tag="error_message", color=[255, 100, 100], wrap=850)
                
                with dpg.group(horizontal=True):
                    dpg.add_text("Progress: ", tag="progress_text")
                    dpg.add_text("Speed: 0 KB/s", tag="download_speed")
                    dpg.add_text("ETA: --:--", tag="download_eta")
                dpg.add_progress_bar(default_value=0, tag="progress", width=850)
            
            # Playlist options (Initially hidden)
            with dpg.collapsing_header(label="Playlist Options", tag="playlist_options", show=False):
                dpg.add_checkbox(label="Download entire playlist", tag="download_playlist")
                with dpg.group(horizontal=True):
                    dpg.add_text("Videos found: 0", tag="playlist_count")
                    dpg.add_button(label="Select Items", callback=self.show_playlist_items, tag="select_playlist_items", show=False)

    def create_batch_tab(self):
        """Create batch download interface"""
        with dpg.group():
            # Header
            with dpg.group(horizontal=True):
                dpg.add_text("Batch YouTube Downloader", color=[255, 0, 0])
                dpg.add_spacer(width=10)
                dpg.add_button(label="Clear All", callback=self.clear_batch_form, width=80)
            
            # Instructions
            dpg.add_text("Enter one YouTube URL per line or upload a text file:")
            
            # URLs text area and file upload
            with dpg.group(horizontal=True):
                dpg.add_input_text(multiline=True, height=150, width=750, tag="batch_urls")
                with dpg.group():
                    dpg.add_button(label="Upload URLs", callback=self.open_url_file, width=95)
                    dpg.add_spacer(height=5)
                    dpg.add_button(label="Paste", callback=self.paste_batch_urls, width=95)
            
            # Format selection
            with dpg.group(horizontal=True):
                dpg.add_text("Format for all videos:")
                dpg.add_combo(
                    items=["best", "1080p", "720p", "480p", "360p", "audio only"],
                    default_value="best",
                    tag="batch_format_combo",
                    width=200
                )
                dpg.add_spacer(width=20)
                
                # Download location
                dpg.add_button(label="Select Download Folder", callback=self.select_batch_directory, width=200)
            
            # Display selected folder
            dpg.add_text(f"Download folder: {self.download_path}", tag="batch_directory", wrap=850)
            
            # Download controls
            with dpg.group(horizontal=True):
                dpg.add_button(label="Download All", callback=self.on_batch_download_click, width=150, height=30, tag="batch_download_button")
                dpg.add_button(label="Cancel All", callback=self.on_batch_cancel_click, width=150, height=30, tag="batch_cancel_button", enabled=False)
            dpg.add_separator()
            
            # Progress information
            dpg.add_text("Status: Ready", tag="batch_status")
            dpg.add_text("", tag="batch_error_message", color=[255, 100, 100], wrap=850)
            
            # Overall progress
            with dpg.group():
                dpg.add_text("Overall Progress: 0/0", tag="batch_overall_progress")
                dpg.add_progress_bar(default_value=0, tag="batch_progress", width=850)
            
            # Batch results table
            dpg.add_text("Results:")
            with dpg.table(tag="batch_results_table", header_row=True, 
                           policy=dpg.mvTable_SizingStretchProp,
                           borders_innerH=True, borders_outerH=True, 
                           borders_innerV=True, borders_outerV=True, 
                           resizable=True, width=850, height=200):
                dpg.add_table_column(label="URL")
                dpg.add_table_column(label="Status")
                dpg.add_table_column(label="Progress")

    def open_url_file(self):
        """Open file dialog to select a text file with URLs"""
        dpg.add_file_dialog(
            directory_selector=False,
            callback=self.load_url_file,
            tag="url_file_dialog",
            width=700,
            height=400,
            default_path=self.download_path,
            extensions=".txt"
        )
        dpg.show_item("url_file_dialog")

    def load_url_file(self, sender, app_data):
        """Load URLs from a text file"""
        file_path = app_data['file_path_name']
        try:
            with open(file_path, 'r') as f:
                urls = f.read()
            
            # Get current content
            current_content = dpg.get_value("batch_urls")
            
            # Add new URLs, ensuring there's a separator if needed
            if current_content and not current_content.endswith('\n'):
                urls = '\n' + urls
            
            # Set value to combined content
            dpg.set_value("batch_urls", current_content + urls)
            dpg.set_value("batch_status", f"Loaded URLs from {os.path.basename(file_path)}")
        except Exception as e:
            dpg.set_value("batch_error_message", f"Error loading file: {str(e)}")

    def paste_batch_urls(self):
        """Paste URLs from clipboard into the batch text area"""
        try:
            import pyperclip
            clipboard_text = pyperclip.paste()
            if clipboard_text:
                # Get current content
                current_content = dpg.get_value("batch_urls")
                
                # Add new URLs, ensuring there's a separator if needed
                if current_content and not current_content.endswith('\n'):
                    clipboard_text = '\n' + clipboard_text
                
                # Set value to combined content
                dpg.set_value("batch_urls", current_content + clipboard_text)
        except Exception as e:
            print(f"Error pasting URLs: {e}")
            dpg.set_value("batch_error_message", "Failed to paste from clipboard")

    def create_history_tab(self):
        """Create download history interface"""
        with dpg.group():
            dpg.add_text("Download History")
            
            with dpg.group(horizontal=True):
                dpg.add_button(label="Clear History", callback=self.clear_history, width=120)
                dpg.add_button(label="Refresh", callback=self.refresh_history, width=100)
            
            # History table
            with dpg.table(tag="history_table", header_row=True, policy=dpg.mvTable_SizingStretchProp,
                          borders_innerH=True, borders_outerH=True, borders_innerV=True,
                          borders_outerV=True, resizable=True, sortable=True, width=850, height=400):
                dpg.add_table_column(label="Date/Time")
                dpg.add_table_column(label="Title")
                dpg.add_table_column(label="Format")
                dpg.add_table_column(label="Status")
                dpg.add_table_column(label="File")
                dpg.add_table_column(label="Action")

    def create_settings_tab(self):
        """Create settings interface"""
        with dpg.group():
            dpg.add_text("Application Settings")
            
            with dpg.group():
                # Theme settings
                with dpg.group(horizontal=True):
                    dpg.add_text("Theme:")
                    dpg.add_radio_button(("Dark", "Light"), callback=self.change_theme, 
                                      default_value="Dark" if self.settings["theme"] == "dark" else "Light",
                                      horizontal=True, tag="theme_setting")
                
                # Downloads folder
                with dpg.group(horizontal=True):
                    dpg.add_button(label="Default Downloads Folder", callback=self.select_default_directory, width=200)
                    dpg.add_text(self.settings["downloads_folder"], tag="default_directory", wrap=600)
                
                # Filename template
                with dpg.group(horizontal=True):
                    dpg.add_text("Filename Template:")
                    dpg.add_input_text(default_value=self.settings["filename_template"], tag="filename_template", width=400)
                    dpg.add_text(" ?", tag="filename_help")
                    
                    # Add tooltip for the filename template help
                    with dpg.tooltip("filename_help"):    
                        dpg.add_text("Available variables:\n%(title)s - Video title\n%(id)s - Video ID\n%(uploader)s - Uploader\n%(upload_date)s - Upload date")
                
                # Save settings button
                dpg.add_button(label="Save Settings", callback=self.save_user_settings, width=120)

    def create_about_tab(self):
        """Create about page"""
        with dpg.group():
            dpg.add_text("YouTube Downloader", color=[255, 50, 50])
            dpg.add_text("A simple YouTube video downloader using yt-dlp and DearPyGUI")
            dpg.add_separator()
            
            dpg.add_text("Features:")
            dpg.add_text("• Download YouTube videos in various formats")
            dpg.add_text("• Extract audio from videos")
            dpg.add_text("• Download whole playlists")
            dpg.add_text("• Track download history")
            dpg.add_text("• Customize download settings")
            dpg.add_separator()
            
            dpg.add_text("Instructions:")
            dpg.add_text("1. Enter a YouTube URL")
            dpg.add_text("2. Click 'Get Info' to see available formats")
            dpg.add_text("3. Select format and click 'Download'")
            dpg.add_separator()
            
            dpg.add_text("Troubleshooting:")
            dpg.add_text("• If you see errors, try a different video")
            dpg.add_text("• YouTube regularly changes their API which may cause issues")
            dpg.add_text("• Try again later if you encounter rate limiting")
            dpg.add_separator()
            
            # Links
            with dpg.group(horizontal=True):
                dpg.add_button(label="GitHub", callback=lambda: webbrowser.open("https://github.com/yt-dlp/yt-dlp"))
                dpg.add_button(label="yt-dlp Documentation", callback=lambda: webbrowser.open("https://github.com/yt-dlp/yt-dlp#readme"))
                dpg.add_button(label="DearPyGUI", callback=lambda: webbrowser.open("https://github.com/hoffstadt/DearPyGui"))

    def set_theme(self, theme_name):
        """Set application theme"""
        with dpg.theme() as global_theme:
            with dpg.theme_component(dpg.mvAll):
                if theme_name == "dark":
                    dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (25, 25, 25))
                    dpg.add_theme_color(dpg.mvThemeCol_TitleBg, (40, 40, 40))
                    dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, (50, 50, 50))
                    dpg.add_theme_color(dpg.mvThemeCol_Button, (70, 70, 70))
                    dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (80, 80, 80))
                    dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (90, 90, 90))
                    dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (60, 60, 60))
                    dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255))
                    dpg.add_theme_color(dpg.mvThemeCol_TabActive, (80, 80, 80))
                    dpg.add_theme_color(dpg.mvThemeCol_TabHovered, (70, 70, 70))
                    dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, (70, 70, 70))
                    dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, (80, 80, 80))
                else:
                    dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (240, 240, 240))
                    dpg.add_theme_color(dpg.mvThemeCol_TitleBg, (220, 220, 220))
                    dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, (200, 200, 200))
                    dpg.add_theme_color(dpg.mvThemeCol_Button, (180, 180, 180))
                    dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (190, 190, 190))
                    dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (200, 200, 200))
                    dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (230, 230, 230))
                    dpg.add_theme_color(dpg.mvThemeCol_Text, (20, 20, 20))
                    dpg.add_theme_color(dpg.mvThemeCol_TabActive, (200, 200, 200))
                    dpg.add_theme_color(dpg.mvThemeCol_TabHovered, (210, 210, 210))
                    dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, (210, 210, 210))
                    dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, (200, 200, 200))
        dpg.bind_theme(global_theme)
    
    def change_theme(self, sender, app_data):
        """Change theme when user selects a new one"""
        theme = "dark" if app_data == "Dark" else "light"
        self.settings["theme"] = theme
        self.set_theme(theme)
    
    def on_info_click(self):
        """Handle get info button click"""
        url = dpg.get_value("url_input")
        if not url:
            dpg.set_value("status", "Please enter a URL")
            return
        
        dpg.set_value("status", "Getting video info...")
        dpg.set_value("video_title", "Title: Loading...")
        dpg.set_value("video_duration", "Duration: Loading...")
        dpg.set_value("video_channel", "Channel: Loading...")
        dpg.set_value("video_upload_date", "Upload Date: Loading...")
        dpg.set_value("error_message", "")
        dpg.set_value("progress", 0)
        
        # Get video info in a separate thread
        def get_info_thread():
            success, result, formats = self.downloader.get_video_info(url)
            
            if success:
                # Set video information
                title = result.get('title', 'Unknown')
                uploader = result.get('uploader', 'Unknown')
                upload_date = result.get('upload_date', '')
                duration = result.get('duration', 0)
                
                # Format duration
                duration_str = "Unknown"
                if duration:
                    mins, secs = divmod(int(duration), 60)
                    hours, mins = divmod(mins, 60)
                    if hours > 0:
                        duration_str = f"{hours}h {mins}m {secs}s"
                    else:
                        duration_str = f"{mins}m {secs}s"
                
                # Format upload date
                if upload_date and len(upload_date) == 8:
                    try:
                        date_obj = datetime.strptime(upload_date, '%Y%m%d')
                        upload_date = date_obj.strftime('%b %d, %Y')
                    except:
                        pass
                
                # Show playlist information if available
                is_playlist = 'entries' in result or result.get('_type') == 'playlist'
                if is_playlist:
                    entries = result.get('entries', [])
                    playlist_count = len(list(entries)) if entries else 0
                    dpg.configure_item("playlist_options", show=True)
                    dpg.set_value("playlist_count", f"Videos found: {playlist_count}")
                    dpg.configure_item("select_playlist_items", show=playlist_count > 0)
                else:
                    dpg.configure_item("playlist_options", show=False)
                
                # Update UI with video details
                dpg.set_value("video_title", f"Title: {title}")
                dpg.set_value("video_duration", f"Duration: {duration_str}")
                dpg.set_value("video_channel", f"Channel: {uploader}")
                dpg.set_value("video_upload_date", f"Upload Date: {upload_date}")
                
                # Get and set estimated file size
                if 'formats' in result:
                    format_choice = dpg.get_value("format_combo")
                    size = self._get_estimated_size(result, format_choice)
                    dpg.set_value("estimated_size", f"Estimated Size: {size}")
                
                # Update format dropdown
                dpg.configure_item("format_combo", items=formats)
                dpg.set_value("status", "Ready to download")
            else:
                dpg.set_value("status", "Error retrieving video information")
                dpg.set_value("error_message", str(result))
        threading.Thread(target=get_info_thread).start()
    
    def _get_estimated_size(self, info, format_choice):
        """Estimate download size based on selected format"""
        try:
            # Handle format selection
            if format_choice == "audio only":
                for fmt in info.get('formats', []):
                    if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                        if 'filesize' in fmt and fmt['filesize']:
                            return self._format_size(fmt['filesize'])
            elif format_choice in ["best", "1080p", "720p", "480p", "360p"]:
                # For specific resolutions
                if format_choice != "best":
                    height = int(format_choice[:-1])
                    # Find closest matching format
                    for fmt in info.get('formats', []):
                        if fmt.get('height') == height:
                            if 'filesize' in fmt and fmt['filesize']:
                                return self._format_size(fmt['filesize'])
                # If specific format not found or 'best' is selected
                if 'filesize' in info and info['filesize']:
                    return self._format_size(info['filesize'])
                elif 'filesize_approx' in info and info['filesize_approx']:
                    return self._format_size(info['filesize_approx']) + " (approx)"
            # If we couldn't determine size
            return "Unknown"
        except:
            return "Unknown"
    
    def _format_size(self, size_bytes):
        """Format file size in human-readable format"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    
    def on_download_click(self):
        """Handle download button click"""
        url = dpg.get_value("url_input")
        if not url:
            dpg.set_value("status", "Please enter a URL")
            return
        
        format_choice = dpg.get_value("format_combo")
        
        # Reset progress
        dpg.set_value("progress", 0)
        dpg.set_value("error_message", "")
        dpg.set_value("download_speed", "0 KB/s")
        dpg.set_value("download_eta", "--:--")
        
        # Disable download button and enable cancel button
        if dpg.does_item_exist("download_button"):
            dpg.configure_item("download_button", enabled=False)
        if dpg.does_item_exist("cancel_button"):
            dpg.configure_item("cancel_button", enabled=True)
        
        self.is_downloading = True
        self.last_downloaded_bytes = 0
        self.last_time = time.time()
        
        # Check if downloading playlist
        download_playlist = False
        if dpg.does_item_exist("download_playlist"):
            download_playlist = dpg.get_value("download_playlist")
        
        # Get filename template
        filename_template = self.settings.get("filename_template", "%(title)s")
        
        # Start download in a separate thread to avoid freezing GUI
        def download_thread():
            dpg.set_value("status", "Starting download...")
            
            # Add timestamp to history before download starts
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            title = dpg.get_value("video_title")[7:]  # Remove "Title: " prefix
            history_entry = {
                "timestamp": timestamp,
                "title": title,
                "format": format_choice,
                "status": "Downloading",
                "filepath": self.download_path
            }
            
            # Add to history and update UI
            self.download_history.append(history_entry)
            self.update_history_table()
            
            if download_playlist:
                success, message = self.downloader.download_playlist(url, self.download_path, format_choice, filename_template)
            else:
                success, message = self.downloader.download_video(url, self.download_path, format_choice, filename_template)
            
            # Update history with final status
            history_entry["status"] = "Complete" if success else "Failed"
            self.update_history_table()
            
            # Update UI when download completes
            if success:
                dpg.set_value("status", message)
                self._show_notification("Download Complete", title)
            else:
                dpg.set_value("status", "Download failed")
                dpg.set_value("error_message", message)
                self._show_notification("Download Failed", f"{title} - {message}")
            
            dpg.set_value("progress_text", "Progress: 100%")
            dpg.configure_item("download_button", enabled=True)
            dpg.configure_item("cancel_button", enabled=False)
            self.is_downloading = False
        
        download_thread = threading.Thread(target=download_thread)
        download_thread.daemon = True
        download_thread.start()

        # Monitor the download thread and check for cancelation
        def monitor_thread():
            while download_thread.is_alive() and self.is_downloading:
                time.sleep(0.1)
        
        monitor = threading.Thread(target=monitor_thread)
        monitor.daemon = True
        monitor.start()
    
    def _show_notification(self, title, message):
        """Show a system notification if available"""
        # This is a placeholder - platform-specific notification code would go here
        # For now, we just print to console
        print(f"NOTIFICATION: {title} - {message}")
    
    def on_cancel_click(self):
        """Handle cancel button click"""
        if self.is_downloading:
            self.downloader.cancel_download()
            dpg.set_value("status", "Canceling download...")
            if dpg.does_item_exist("download_button"):
                dpg.configure_item("download_button", enabled=True)
            if dpg.does_item_exist("cancel_button"):
                dpg.configure_item("cancel_button", enabled=False)
            
            # Update history with canceled status
            if self.download_history:
                self.download_history[-1]["status"] = "Canceled"
                self.update_history_table()
    
    def select_directory(self):
        """Open directory selection dialog"""
        dpg.add_file_dialog(
            directory_selector=True,
            callback=self.directory_selected,
            tag="directory_dialog",
            default_path=self.download_path,
            width=700,
            height=400
        )
        dpg.show_item("directory_dialog")
    
    def select_default_directory(self):
        """Open directory selection dialog for default download location"""
        dpg.add_file_dialog(
            directory_selector=True,
            callback=self.default_directory_selected,
            tag="default_directory_dialog",
            default_path=self.settings["downloads_folder"],
            width=700,
            height=400
        )
        dpg.show_item("default_directory_dialog")
    
    def directory_selected(self, sender, app_data):
        """Handle directory selection"""
        self.download_path = app_data['file_path_name']
        dpg.set_value("directory", f"Download folder: {self.download_path}")
    
    def default_directory_selected(self, sender, app_data):
        """Handle default directory selection"""
        self.settings["downloads_folder"] = app_data['file_path_name']
        dpg.set_value("default_directory", self.settings["downloads_folder"])
    
    def progress_hook(self, d):
        """Update progress bar based on download progress"""
        if d['status'] == 'downloading':
            try:
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
                
                # Calculate download speed
                current_time = time.time()
                time_diff = current_time - self.last_time
                
                if time_diff >= 1:  # Update every second
                    byte_diff = downloaded - self.last_downloaded_bytes
                    speed = byte_diff / time_diff
                    
                    # Calculate ETA
                    if speed > 0 and total > 0:
                        remaining_bytes = total - downloaded
                        eta_seconds = remaining_bytes / speed
                        m, s = divmod(int(eta_seconds), 60)
                        h, m = divmod(m, 60)
                        if h > 0:
                            eta = f"{h}h {m}m {s}s"
                        elif m > 0:
                            eta = f"{m}m {s}s"
                        else:
                            eta = f"{s}s"
                        dpg.set_value("download_eta", f"ETA: {eta}")
                    
                    # Format speed for display
                    if speed < 1024:
                        speed_str = f"{speed:.1f} B/s"
                    elif speed < 1024 * 1024:
                        speed_str = f"{speed / 1024:.1f} KB/s"
                    else:
                        speed_str = f"{speed / (1024 * 1024):.1f} MB/s"
                    
                    dpg.set_value("download_speed", f"Speed: {speed_str}")
                    self.last_downloaded_bytes = downloaded
                    self.last_time = current_time
                
                if total > 0:
                    progress = downloaded / total
                    dpg.set_value("progress", progress)
                    progress_percent = f"{progress:.1%}"
                    dpg.set_value("progress_text", f"Progress: {progress_percent}")
                    
                    # Format size display (MB)
                    downloaded_mb = downloaded / (1024 * 1024)
                    total_mb = total / (1024 * 1024)
                    dpg.set_value("status", f"Downloading: {progress:.1%} ({downloaded_mb:.1f}MB of {total_mb:.1f}MB)")
                else:
                    downloaded_mb = downloaded / (1024 * 1024)
                    dpg.set_value("status", f"Downloading... ({downloaded_mb:.1f}MB)")
                    dpg.set_value("progress_text", f"Progress: --")
            except Exception as e:
                print(f"Progress error: {e}")
                
        elif d['status'] == 'finished':
            dpg.set_value("status", "Download finished. Processing...")

    def paste_url(self):
        """Paste URL from clipboard"""
        try:
            # This is simplified - actual clipboard access would depend on platform
            import pyperclip
            clipboard_text = pyperclip.paste()
            if clipboard_text:
                dpg.set_value("url_input", clipboard_text)
        except:
            pass
    
    def open_download_folder(self):
        """Open the download folder in file explorer"""
        try:
            if os.path.exists(self.download_path):
                if os.name == 'nt':  # Windows
                    os.startfile(self.download_path)
                elif os.name == 'posix':  # macOS and Linux
                    if 'darwin' in os.sys.platform:  # macOS
                        os.system(f'open "{self.download_path}"')
                    else:  # Linux
                        os.system(f'xdg-open "{self.download_path}"')
        except Exception as e:
            print(f"Error opening folder: {e}")
    
    def show_playlist_items(self):
        """Show dialog to select playlist items"""
        # This is a placeholder - would need to implement playlist item selection
        pass
    
    def update_history_table(self):
        """Update the download history table"""
        # Clear existing rows
        if dpg.does_item_exist("history_table"):
            children = dpg.get_item_children("history_table")
            if children:
                row_ids = children[1]  # Index 1 contains row IDs
                for row_id in row_ids:
                    dpg.delete_item(row_id)
            
            # Add history entries to table
            for idx, entry in enumerate(self.download_history):
                with dpg.table_row(parent="history_table", tag=f"history_row_{idx}"):
                    dpg.add_text(entry.get("timestamp", ""))
                    dpg.add_text(entry.get("title", "")[:50])
                    dpg.add_text(entry.get("format", ""))
                    
                    # Status with color
                    status = entry.get("status", "")
                    if status == "Complete":
                        dpg.add_text(status, color=[50, 200, 50])
                    elif status == "Failed":
                        dpg.add_text(status, color=[200, 50, 50])
                    elif status == "Canceled":
                        dpg.add_text(status, color=[200, 200, 50])
                    else:
                        dpg.add_text(status)
                    
                    filepath = entry.get("filepath", "")
                    dpg.add_text(os.path.basename(filepath) if filepath else "")
                    
                    # Open file button
                    if status == "Complete" and filepath:
                        dpg.add_button(label="Open", callback=lambda s, a, u=filepath: self.open_file(u), width=60)
                    else:
                        dpg.add_text("")

    def open_file(self, filepath):
        """Open a downloaded file"""
        try:
            if os.path.exists(filepath):
                if os.name == 'nt':  # Windows
                    os.startfile(filepath)
                elif os.name == 'posix':  # macOS and Linux
                    if 'darwin' in os.sys.platform:  # macOS
                        os.system(f'open "{filepath}"')
                    else:  # Linux
                        os.system(f'xdg-open "{filepath}"')
        except Exception as e:
            print(f"Error opening file: {e}")
    
    def refresh_history(self):
        """Refresh the history table"""
        self.update_history_table()
    
    def clear_history(self):
        """Clear download history"""
        self.download_history = []
        self.update_history_table()
    
    def delete_selected_history(self):
        """Delete selected history entry"""
        # This is a placeholder - would need table selection to work properly
        pass
    
    def clear_form(self):
        """Clear the form fields"""
        dpg.set_value("url_input", "")
        dpg.set_value("video_title", "Title: ")
        dpg.set_value("video_duration", "Duration: ")
        dpg.set_value("video_channel", "Channel: ")
        dpg.set_value("video_upload_date", "Upload Date: ")
        dpg.set_value("error_message", "")
        dpg.set_value("progress", 0)
        dpg.set_value("status", "Ready")
        dpg.set_value("estimated_size", "Estimated Size: Unknown")
        dpg.configure_item("playlist_options", show=False)
    
    def save_user_settings(self):
        """Save user settings"""
        # Get values from UI
        self.settings["theme"] = "dark" if dpg.get_value("theme_setting") == "Dark" else "light"
        self.settings["filename_template"] = dpg.get_value("filename_template")
        
        # Save settings to file
        self.save_settings()
        
        # Show confirmation
        dpg.set_value("status", "Settings saved")
    
    def run(self):
        """Run the application"""
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window("Primary Window", True)
        dpg.start_dearpygui()
        dpg.destroy_context()
    
    def select_batch_directory(self):
        """Open directory selection dialog for batch downloads"""
        dpg.add_file_dialog(
            directory_selector=True,
            callback=self.batch_directory_selected,
            tag="batch_directory_dialog",
            default_path=self.download_path,
            width=700,
            height=400
        )
        dpg.show_item("batch_directory_dialog")

    def batch_directory_selected(self, sender, app_data):
        """Handle batch directory selection"""
        self.download_path = app_data['file_path_name']
        dpg.set_value("batch_directory", f"Download folder: {self.download_path}")

    def clear_batch_form(self):
        """Clear batch form fields"""
        dpg.set_value("batch_urls", "")
        dpg.set_value("batch_status", "Status: Ready")
        dpg.set_value("batch_error_message", "")
        dpg.set_value("batch_progress", 0)
        dpg.set_value("batch_overall_progress", "Overall Progress: 0/0")
        
        # Clear results table
        if dpg.does_item_exist("batch_results_table"):
            children = dpg.get_item_children("batch_results_table")
            if children and len(children) > 1:
                row_ids = children[1]  # Index 1 contains row IDs
                for row_id in row_ids:
                    dpg.delete_item(row_id)

    def on_batch_download_click(self):
        """Handle batch download button click"""
        # Get URLs (one per line)
        batch_text = dpg.get_value("batch_urls")
        urls = [url.strip() for url in batch_text.split('\n') if url.strip()]
        
        if not urls:
            dpg.set_value("batch_status", "Please enter at least one URL")
            return
        
        format_choice = dpg.get_value("batch_format_combo")
        
        # Reset batch progress
        dpg.set_value("batch_progress", 0)
        dpg.set_value("batch_error_message", "")
        dpg.set_value("batch_overall_progress", f"Overall Progress: 0/{len(urls)}")
        
        # Disable download button and enable cancel button
        if dpg.does_item_exist("batch_download_button"):
            dpg.configure_item("batch_download_button", enabled=False)
        if dpg.does_item_exist("batch_cancel_button"):
            dpg.configure_item("batch_cancel_button", enabled=True)
        
        self.is_downloading = True
        
        # Clear results table
        self.clear_batch_results_table()
        
        # Create initial entries in results table
        for i, url in enumerate(urls):
            with dpg.table_row(parent="batch_results_table", tag=f"batch_row_{i}"):
                shortened_url = url[:50] + "..." if len(url) > 50 else url
                dpg.add_text(shortened_url, tag=f"batch_url_{i}")
                dpg.add_text("Pending...", tag=f"batch_status_{i}")
                dpg.add_progress_bar(default_value=0, width=-1, tag=f"batch_item_progress_{i}")
        
        # Get filename template
        filename_template = self.settings.get("filename_template", "%(title)s")
        
        # Start batch download in a separate thread
        def batch_download_thread():
            dpg.set_value("batch_status", "Starting batch download...")
            total_urls = len(urls)
            completed_count = 0
            
            # Use ThreadPoolExecutor to parallelize downloads
            from concurrent.futures import ThreadPoolExecutor
            
            # Limit concurrent downloads to 2 to avoid hitting API limits
            with ThreadPoolExecutor(max_workers=2) as executor:
                # Track futures for cancellation
                self.batch_futures = []
                
                def download_single(idx, url):
                    try:
                        # Update status
                        dpg.set_value(f"batch_status_{idx}", "Getting info...")
                        
                        # Add to history before download starts
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        history_entry = {
                            "timestamp": timestamp,
                            "title": url,
                            "format": format_choice,
                            "status": "Downloading",
                            "filepath": self.download_path
                        }
                        
                        # Try to get video info first
                        success, info, _ = self.downloader.get_video_info(url)
                        
                        if success:
                            title = info.get('title', 'Unknown')
                            # Update URL display with title
                            dpg.set_value(f"batch_url_{idx}", f"{title[:50]}...")
                            history_entry["title"] = title
                            
                            # Add to history
                            self.download_history.append(history_entry)
                            self.update_history_table()
                            
                            # Update status
                            dpg.set_value(f"batch_status_{idx}", "Downloading...")
                            
                            # Download the video
                            current_item_callback = lambda d: self.batch_item_progress_hook(d, idx)
                            success, message = self.downloader.download_video_with_callback(
                                url, self.download_path, format_choice, filename_template, current_item_callback
                            )
                            
                            # Update status and history
                            status = "Complete" if success else "Failed"
                            dpg.set_value(f"batch_status_{idx}", status)
                            history_entry["status"] = status
                            
                            if not success:
                                dpg.set_value(f"batch_status_{idx}", f"Failed: {message}")
                            self.update_history_table()
                            
                            # Show notification for completed downloads
                            if success:
                                self._show_notification("Download Complete", title)
                        else:
                            dpg.set_value(f"batch_status_{idx}", f"Failed: {info}")
                            history_entry["status"] = "Failed"
                            self.download_history.append(history_entry)
                            self.update_history_table()
                        return success
                    except Exception as e:
                        dpg.set_value(f"batch_status_{idx}", f"Error: {str(e)}")
                        return False
                
                # Submit all download tasks
                for i, url in enumerate(urls):
                    if url.strip():
                        future = executor.submit(download_single, i, url)
                        self.batch_futures.append(future)
                    else:
                        dpg.set_value(f"batch_status_{i}", "Invalid URL")
                        completed_count += 1
                        dpg.set_value("batch_overall_progress", f"Overall Progress: {completed_count}/{total_urls}")
                        dpg.set_value("batch_progress", completed_count / total_urls)
                
                # Wait for all downloads to complete
                for i, future in enumerate(self.batch_futures):
                    try:
                        success = future.result()
                        completed_count += 1
                        dpg.set_value("batch_overall_progress", f"Overall Progress: {completed_count}/{total_urls}")
                        dpg.set_value("batch_progress", completed_count / total_urls)
                    except Exception as e:
                        print(f"Error in batch download: {e}")
            
            # Update UI when all downloads complete
            self.is_downloading = False
            dpg.configure_item("batch_download_button", enabled=True)
            dpg.configure_item("batch_cancel_button", enabled=False)
            dpg.set_value("batch_status", "Batch download completed")
        
        batch_thread = threading.Thread(target=batch_download_thread)
        batch_thread.daemon = True
        batch_thread.start()

    def batch_item_progress_hook(self, d, idx):
        """Handle progress updates for batch items"""
        if d['status'] == 'downloading':
            try:
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
                
                if total > 0:
                    progress = downloaded / total
                    dpg.set_value(f"batch_item_progress_{idx}", progress)
                    
                    # Don't update too frequently to avoid GUI overload
                    if progress % 0.05 < 0.01:  # Update roughly every 5%
                        progress_percent = f"{progress:.1%}"
                        dpg.set_value(f"batch_status_{idx}", f"Downloading: {progress_percent}")
            except Exception as e:
                print(f"Batch progress error: {e}")
                    
        elif d['status'] == 'finished':
            dpg.set_value(f"batch_status_{idx}", "Processing...")

    def on_batch_cancel_click(self):
        """Handle batch cancel button click"""
        if self.is_downloading:
            # Cancel downloads
            self.downloader.cancel_download()
            
            # Cancel all pending futures if available
            if hasattr(self, 'batch_futures'):
                for future in self.batch_futures:
                    future.cancel()
            
            dpg.set_value("batch_status", "Canceling batch downloads...")
            if dpg.does_item_exist("batch_download_button"):
                dpg.configure_item("batch_download_button", enabled=True)
            if dpg.does_item_exist("batch_cancel_button"):
                dpg.configure_item("batch_cancel_button", enabled=False)
            
            # Update history with canceled status
            for entry in self.download_history:
                if entry["status"] == "Downloading":
                    entry["status"] = "Canceled"
            self.update_history_table()
    
    def clear_batch_results_table(self):
        """Clear batch results table"""
        if dpg.does_item_exist("batch_results_table"):
            children = dpg.get_item_children("batch_results_table")
            if children and len(children) > 1:
                row_ids = children[1]  # Index 1 contains row IDs
                for row_id in row_ids:
                    dpg.delete_item(row_id)

    def create_info_gatherer_tab(self):
        """Create video info gatherer interface"""
        with dpg.group():
            # Header
            with dpg.group(horizontal=True):
                dpg.add_text("Video Info Gatherer", color=[50, 150, 255])
                dpg.add_spacer(width=10)
                dpg.add_button(label="Clear", callback=self.clear_info_form, width=80)
            
            # Instructions
            dpg.add_text("Enter YouTube URLs (one per line) to gather information:")
            
            # URLs text area and file upload
            with dpg.group(horizontal=True):
                dpg.add_input_text(multiline=True, height=150, width=750, tag="info_urls")
                with dpg.group():
                    dpg.add_button(label="Upload URLs", callback=self.open_info_url_file, width=95)
                    dpg.add_spacer(height=5)
                    dpg.add_button(label="Paste", callback=self.paste_info_urls, width=95)
            
            # Output file selection
            with dpg.group(horizontal=True):
                dpg.add_button(label="Select Output Folder", callback=self.select_info_output_folder, width=180)
                dpg.add_input_text(default_value="video_info.txt", label="Base filename", tag="info_output_file", width=300)
            
            # Display selected folder
            dpg.add_text(f"Output folder: {self.download_path}", tag="info_output_folder", wrap=850)
            
            # Output options - First row
            with dpg.group(horizontal=True):
                dpg.add_checkbox(label="Create separate files for each month", tag="separate_month_files", default_value=True)
                dpg.add_checkbox(label="Create summary file with all videos", tag="create_summary_file", default_value=True)
            
            # Output options - Second row (new)
            with dpg.group(horizontal=True):
                dpg.add_text("File Content Type:")
                dpg.add_radio_button(
                    items=("URLs only", "URLs and detailed info"), 
                    tag="info_content_type",
                    default_value="URLs and detailed info",
                    horizontal=True
                )
            
            # Process controls
            with dpg.group(horizontal=True):
                dpg.add_button(label="Gather Info", callback=self.on_gather_info_click, width=150, height=30, tag="gather_info_button")
                dpg.add_button(label="Cancel", callback=self.on_cancel_info_gathering, width=150, height=30, tag="cancel_info_button", enabled=False)
            
            dpg.add_separator()
            
            # Status section
            dpg.add_text("Status: Ready", tag="info_status")
            dpg.add_text("", tag="info_error_message", color=[255, 100, 100], wrap=850)
            
            # Progress bar
            with dpg.group():
                dpg.add_text("Progress: 0/0", tag="info_progress_text")
                dpg.add_progress_bar(default_value=0, tag="info_progress", width=850)
            
            # Results preview 
            dpg.add_text("Results Preview:")
            dpg.add_input_text(multiline=True, readonly=True, height=150, width=850, tag="info_results_preview")

    def open_info_url_file(self):
        """Open file dialog to select a text file with URLs for info gathering"""
        dpg.add_file_dialog(
            directory_selector=False,
            callback=self.load_info_url_file,
            tag="info_url_file_dialog",
            width=700,
            height=400,
            default_path=self.download_path,
            extensions=".txt"
        )
        dpg.show_item("info_url_file_dialog")

    def load_info_url_file(self, sender, app_data):
        """Load URLs from a text file for info gathering"""
        file_path = app_data['file_path_name']
        try:
            with open(file_path, 'r') as f:
                urls = f.read()
            
            # Get current content
            current_content = dpg.get_value("info_urls")
            
            # Add new URLs, ensuring there's a separator if needed
            if current_content and not current_content.endswith('\n'):
                urls = '\n' + urls
            
            # Set value to combined content
            dpg.set_value("info_urls", current_content + urls)
            dpg.set_value("info_status", f"Loaded URLs from {os.path.basename(file_path)}")
        except Exception as e:
            dpg.set_value("info_error_message", f"Error loading file: {str(e)}")

    def paste_info_urls(self):
        """Paste URLs from clipboard into the info gatherer text area"""
        try:
            import pyperclip
            clipboard_text = pyperclip.paste()
            if clipboard_text:
                # Get current content
                current_content = dpg.get_value("info_urls")
                
                # Add new URLs, ensuring there's a separator if needed
                if current_content and not current_content.endswith('\n'):
                    clipboard_text = '\n' + clipboard_text
                
                # Set value to combined content
                dpg.set_value("info_urls", current_content + clipboard_text)
        except Exception as e:
            print(f"Error pasting URLs: {e}")
            dpg.set_value("info_error_message", "Failed to paste from clipboard")

    def select_info_output_folder(self):
        """Open directory selection dialog for info output folder"""
        dpg.add_file_dialog(
            directory_selector=True,
            callback=self.info_output_folder_selected,
            tag="info_output_folder_dialog",
            default_path=self.download_path,
            width=700,
            height=400
        )
        dpg.show_item("info_output_folder_dialog")

    def info_output_folder_selected(self, sender, app_data):
        """Handle info output folder selection"""
        self.info_output_path = app_data['file_path_name']
        dpg.set_value("info_output_folder", f"Output folder: {self.info_output_path}")

    def clear_info_form(self):
        """Clear info gatherer form fields"""
        dpg.set_value("info_urls", "")
        dpg.set_value("info_status", "Status: Ready")
        dpg.set_value("info_error_message", "")
        dpg.set_value("info_progress", 0)
        dpg.set_value("info_progress_text", "Progress: 0/0")
        dpg.set_value("info_results_preview", "")

    def on_gather_info_click(self):
        """Handle gather info button click"""
        # Get URLs (one per line)
        info_text = dpg.get_value("info_urls")
        urls = [url.strip() for url in info_text.split('\n') if url.strip()]
        
        if not urls:
            dpg.set_value("info_status", "Please enter at least one URL")
            return
        
        # Set output path
        output_folder = getattr(self, 'info_output_path', self.download_path)
        output_filename = dpg.get_value("info_output_file")
        base_output_path = os.path.join(output_folder, output_filename)
        
        # Get output options
        create_separate_files = dpg.get_value("separate_month_files")
        create_summary_file = dpg.get_value("create_summary_file")
        content_type = dpg.get_value("info_content_type")
        urls_only = (content_type == "URLs only")
        
        # Reset progress
        dpg.set_value("info_progress", 0)
        dpg.set_value("info_error_message", "")
        dpg.set_value("info_progress_text", f"Progress: 0/{len(urls)}")
        dpg.set_value("info_results_preview", "")
        
        # Disable gather button and enable cancel button
        dpg.configure_item("gather_info_button", enabled=False)
        dpg.configure_item("cancel_info_button", enabled=True)
        
        self.is_gathering_info = True
        
        # Start info gathering in a separate thread
        def gather_info_thread():
            dpg.set_value("info_status", "Starting to gather video information...")
            total_urls = len(urls)
            processed_count = 0
            
            # Initialize month categories
            month_categories = {}
            preview_text = ""
            file_paths = []
            
            try:
                # Process each URL
                for i, url in enumerate(urls):
                    if not self.is_gathering_info:  # Check for cancellation
                        break
                    
                    dpg.set_value("info_status", f"Processing URL {i+1} of {total_urls}...")
                    
                    # Get video info
                    success, info, _ = self.downloader.get_video_info(url)
                    
                    if success:
                        title = info.get('title', 'Unknown')
                        uploader = info.get('uploader', 'Unknown')
                        upload_date = info.get('upload_date', '')
                        duration = info.get('duration', 0)
                        
                        # Format duration
                        duration_str = "Unknown"
                        if duration:
                            mins, secs = divmod(int(duration), 60)
                            hours, mins = divmod(mins, 60)
                            if hours > 0:
                                duration_str = f"{hours}h {mins}m {secs}s"
                            else:
                                duration_str = f"{mins}m {secs}s"
                        
                        # Get year and month from upload date
                        if upload_date and len(upload_date) == 8:
                            try:
                                year = upload_date[:4]
                                month = upload_date[4:6]
                                day = upload_date[6:8]
                                date_obj = datetime.strptime(upload_date, '%Y%m%d')
                                month_name = date_obj.strftime('%B')  # Full month name
                                month_key = f"{year}-{month} ({month_name})"
                                
                                # Create month category if it doesn't exist
                                if month_key not in month_categories:
                                    month_categories[month_key] = []
                                
                                # Add video info to the corresponding month
                                video_info = {
                                    'title': title,
                                    'uploader': uploader,
                                    'duration': duration_str,
                                    'url': url,
                                    'date': f"{year}-{month}-{day}"
                                }
                                month_categories[month_key].append(video_info)
                                
                                # Update preview
                                preview_text += f"Added: {title} ({month_name} {year}) - {uploader}\n"
                            except Exception as e:
                                preview_text += f"Error processing date for {title}: {str(e)}\n"
                        else:
                            # Add to "Unknown Date" category
                            if "Unknown Date" not in month_categories:
                                month_categories["Unknown Date"] = []
                            
                            video_info = {
                                'title': title,
                                'uploader': uploader,
                                'duration': duration_str,
                                'url': url,
                                'date': 'Unknown'
                            }
                            month_categories["Unknown Date"].append(video_info)
                            preview_text += f"Added: {title} (Unknown Date) - {uploader}\n"
                    else:
                        error_message = info
                        preview_text += f"Error processing URL {url}: {error_message}\n"
                    
                    # Update progress
                    processed_count += 1
                    dpg.set_value("info_progress", processed_count / total_urls)
                    dpg.set_value("info_progress_text", f"Progress: {processed_count}/{total_urls}")
                    dpg.set_value("info_results_preview", preview_text)
                
                # Generate output files
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                
                # Sort months in descending order (newest first)
                sorted_months = sorted(month_categories.keys(), reverse=True)
                
                # Create separate files for each month
                if create_separate_files and month_categories:
                    for month in sorted_months:
                        videos = month_categories[month]
                        
                        # Create a valid filename from the month
                        month_filename = month.replace(" ", "_").replace("(", "").replace(")", "")
                        month_file_path = os.path.join(output_folder, f"{month_filename}_videos.txt")
                        file_paths.append(month_file_path)
                        
                        with open(month_file_path, 'w', encoding='utf-8') as f:
                            f.write(f"YouTube Videos - {month}\n")
                            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                            f.write(f"Total videos: {len(videos)}\n\n")
                            
                            # Sort videos by date (if available) - newest first
                            videos.sort(key=lambda x: x['date'] if x['date'] != 'Unknown' else '0000-00-00', reverse=True)
                            
                            # Write URLs first (or only URLs if that option is selected)
                            f.write("=== URLs ===\n")
                            for video in videos:
                                f.write(f"{video['url']}\n")
                            
                            # Write detailed info only if requested
                            if not urls_only:
                                f.write("\n\n=== DETAILED INFO ===\n\n")
                                for video in videos:
                                    f.write(f"Title: {video['title']}\n")
                                    f.write(f"Uploader: {video['uploader']}\n")
                                    f.write(f"Duration: {video['duration']}\n")
                                    f.write(f"Date: {video['date']}\n")
                                    f.write(f"URL: {video['url']}\n\n")
                
                # Create summary file with all videos 
                if create_summary_file and month_categories:
                    # Add timestamp to avoid overwriting files
                    base_name = os.path.splitext(base_output_path)[0]
                    ext = os.path.splitext(base_output_path)[1] or ".txt"
                    summary_file_path = f"{base_name}_summary{ext}"
                    file_paths.append(summary_file_path)
                    
                    with open(summary_file_path, 'w', encoding='utf-8') as f:
                        f.write(f"YouTube Video Information - Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"Total videos processed: {processed_count}\n\n")
                        
                        # If URLs only, create a section with all URLs regardless of month
                        if urls_only:
                            f.write("=== ALL URLS ===\n")
                            for month in sorted_months:
                                videos = month_categories[month]
                                videos.sort(key=lambda x: x['date'] if x['date'] != 'Unknown' else '0000-00-00', reverse=True)
                                for video in videos:
                                    f.write(f"{video['url']}\n")
                            f.write("\n\n")
                        
                        # Then create month sections with URLs or detailed info
                        for month in sorted_months:
                            videos = month_categories[month]
                            f.write(f"=== {month} === ({len(videos)} videos)\n\n")
                            
                            # Sort videos by date (if available)
                            videos.sort(key=lambda x: x['date'] if x['date'] != 'Unknown' else '0000-00-00', reverse=True)
                            
                            # Write only URLs if that option is selected
                            if urls_only:
                                for video in videos:
                                    f.write(f"{video['url']}\n")
                                f.write("\n")
                            else:
                                # Write detailed info
                                for video in videos:
                                    f.write(f"Title: {video['title']}\n")
                                    f.write(f"Uploader: {video['uploader']}\n")
                                    f.write(f"Duration: {video['duration']}\n")
                                    f.write(f"Date: {video['date']}\n")
                                    f.write(f"URL: {video['url']}\n\n")
                                
                                f.write("\n")
                
                # Show file paths in the preview
                if file_paths:
                    files_str = "\n".join(file_paths)
                    preview_text += f"\nFiles created:\n{files_str}\n"
                    dpg.set_value("info_results_preview", preview_text)
                    dpg.set_value("info_status", f"Information saved to {len(file_paths)} file(s)")
                else:
                    dpg.set_value("info_status", "No valid video information was found")
            
            except Exception as e:
                dpg.set_value("info_error_message", f"Error gathering information: {str(e)}")
                dpg.set_value("info_status", "Error occurred during processing")
            
            # Update UI
            dpg.configure_item("gather_info_button", enabled=True)
            dpg.configure_item("cancel_info_button", enabled=False)
            self.is_gathering_info = False
        
        info_thread = threading.Thread(target=gather_info_thread)
        info_thread.daemon = True
        info_thread.start()

    def on_cancel_info_gathering(self):
        """Cancel the info gathering process"""
        if self.is_gathering_info:
            self.is_gathering_info = False
            dpg.set_value("info_status", "Canceling info gathering...")
            dpg.configure_item("gather_info_button", enabled=True)
            dpg.configure_item("cancel_info_button", enabled=False)
            
    def clear_batch_results_table(self):
        """Clear batch results table"""
        if dpg.does_item_exist("batch_results_table"):
            children = dpg.get_item_children("batch_results_table")
            if children and len(children) > 1:
                row_ids = children[1]  # Index 1 contains row IDs
                for row_id in row_ids:
                    dpg.delete_item(row_id)