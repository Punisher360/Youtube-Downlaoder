# YouTube Downloader

A powerful desktop application for downloading YouTube videos, gathering video information, and organizing content by upload date. Built with Python using yt-dlp and DearPyGUI.

![YouTube Downloader Screenshot](screenshot.png)

## Features

### 📥 Download Videos
- Download individual YouTube videos in various formats (1080p, 720p, 480p, 360p, audio only)
- Smart format selection with estimated file size display
- Progress tracking with download speed and ETA display
- Custom filename templates support

### 📚 Batch Downloads
- Process multiple URLs at once
- Upload URLs from text file or paste from clipboard
- Concurrent downloads with individual progress tracking
- Detailed status reporting for each URL

### 📊 Video Info Gatherer
- Collect information about multiple YouTube videos without downloading
- Organize videos by upload month
- Generate separate files for each month or summary files
- Choose between URLs-only or detailed information output
- Perfect for creating video collections or playlists

### 📂 Download History
- Track all downloaded videos
- View download status, date, and format
- Quick access to downloaded files

### ⚙️ Customization
- Light/Dark theme support
- Custom download folder configuration
- Customizable filename templates

## Installation

### Prerequisites
- Python 3.7 or higher
- pip (Python package manager)

### Setup

1. Clone this repository:
```bash
git clone https://github.com/yourusername/youtube-downloader.git
cd youtube-downloader
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python main.py
```

## Usage

### Single Video Download
1. Go to the "Downloader" tab
2. Paste a YouTube URL and click "Get Info"
3. Select your desired format
4. Click "Download"

### Batch Download
1. Go to the "Batch Download" tab
2. Enter multiple YouTube URLs (one per line)
3. Select format and output location
4. Click "Download All"

### Video Info Gathering
1. Go to the "Video Info Gatherer" tab
2. Enter multiple YouTube URLs
3. Select output options:
   - Create separate monthly files
   - Create summary file
   - Choose between URLs only or detailed info
4. Click "Gather Info"

### Settings
- Go to the "Settings" tab to customize:
  - Application theme
  - Default download folder
  - Filename templates

## Dependencies

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - YouTube video downloader
- [DearPyGUI](https://github.com/hoffstadt/DearPyGui) - GUI framework
- pyperclip - Clipboard access
- requests - HTTP requests

## License

MIT License - Feel free to use, modify and distribute this software.

## Disclaimer

This tool is meant for downloading videos for personal use only. Please respect copyright laws and YouTube's Terms of Service.
