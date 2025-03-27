from gui import YouTubeDownloaderGUI
from downloader import YouTubeDownloader

if __name__ == "__main__":
    downloader = YouTubeDownloader()
    app = YouTubeDownloaderGUI(downloader)
    app.run()
