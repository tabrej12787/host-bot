from flask import Flask, send_file, request, jsonify
import yt_dlp
import uuid
import os
import re

app = Flask(__name__)
DOWNLOAD_DIR = "/tmp/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.route('/')
def home():
    return jsonify({
        "name": "Universal Video Downloader API",
        "version": "1.0",
        "endpoints": {
            "/info?url=...": "Get video information",
            "/download?url=...": "Download video (best quality)",
            "/download/mp3?url=...": "Download audio only",
            "/health": "Check API status"
        },
        "supported_sites": "1000+ (YouTube, Instagram, TikTok, Facebook, Twitter, etc.)"
    })

@app.route('/info')
def info():
    """Get video information without downloading"""
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "URL parameter required"}), 400
    
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            data = ydl.extract_info(url, download=False)
            
            # Get available qualities
            qualities = []
            if data.get('formats'):
                for f in data['formats']:
                    if f.get('height'):
                        qualities.append(f"{f['height']}p")
            qualities = sorted(set(qualities), key=lambda x: int(x.replace('p', '')), reverse=True)
            
            # Format duration
            duration = data.get('duration', 0)
            if duration:
                minutes = duration // 60
                seconds = duration % 60
                duration_str = f"{minutes}:{seconds:02d}"
            else:
                duration_str = "Unknown"
            
            return jsonify({
                "success": True,
                "title": data.get('title', 'Unknown'),
                "platform": data.get('extractor', 'unknown'),
                "duration": duration_str,
                "thumbnail": data.get('thumbnail', ''),
                "uploader": data.get('uploader', 'Unknown'),
                "view_count": data.get('view_count', 0),
                "like_count": data.get('like_count', 0),
                "comment_count": data.get('comment_count', 0),
                "available_qualities": qualities,
                "filesize_approx": data.get('filesize_approx', 0)
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download')
def download():
    """Download video in best available quality"""
    url = request.args.get('url')
    quality = request.args.get('quality', 'best')
    
    if not url:
        return jsonify({"error": "URL parameter required"}), 400
    
    try:
        filename = f"{uuid.uuid4()}.mp4"
        filepath = os.path.join(DOWNLOAD_DIR, filename)
        
        # Handle quality parameter
        if quality != 'best':
            # Extract number from quality (e.g., "720p" -> 720)
            match = re.search(r'(\d+)', quality)
            if match:
                height = match.group(1)
                format_spec = f'best[height<={height}]'
            else:
                format_spec = 'best'
        else:
            format_spec = 'bestvideo+bestaudio/best'
        
        ydl_opts = {
            'format': format_spec,
            'outtmpl': filepath,
            'quiet': True,
            'no_warnings': True,
            'merge_output_format': 'mp4',
            'concurrent_fragments': 5,
            'retries': 10
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'video')
            # Clean filename
            title = re.sub(r'[^\w\s-]', '', title).strip()[:50]
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=f"{title}.mp4",
            mimetype='video/mp4'
        )
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download/mp3')
def download_mp3():
    """Download audio only as MP3"""
    url = request.args.get('url')
    
    if not url:
        return jsonify({"error": "URL parameter required"}), 400
    
    try:
        filename = f"{uuid.uuid4()}.mp3"
        filepath = os.path.join(DOWNLOAD_DIR, filename)
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': filepath.replace('.mp3', ''),
            'quiet': True,
            'no_warnings': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'retries': 10,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'audio')
            title = re.sub(r'[^\w\s-]', '', title).strip()[:50]
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=f"{title}.mp3",
            mimetype='audio/mpeg'
        )
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health')
def health():
    """Check if API is running"""
    return jsonify({
        "status": "healthy",
        "server_id": os.environ.get('SERVER_ID', '1'),
        "timestamp": str(datetime.now())
    })

if __name__ == '__main__':
    import datetime
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, threaded=True)
