# 2D to 3D Side-by-Side (SBS) Converter

A lightweight, local-first web application that uses AI depth estimation to convert standard 2D flat videos into immersive stereoscopic 3D Side-by-Side (SBS) videos. The resulting videos are perfect for viewing on VR headsets, 3D TVs, or standard devices using cross-eyed/parallel viewing techniques.

## Features
- **AI Depth Estimation**: Uses the lightweight `Intel/dpt-swinv2-tiny-256` model to intelligently estimate depth from flat 2D frames.
- **CPU Optimized**: Carefully designed to fall back to CPU processing, making it perfectly viable to run on standard laptops (like AMD Ryzen or Intel Core processors) without needing a heavy dedicated NVIDIA GPU.
- **Hardware-Accelerated Fallbacks**: Uses `h264_amf` (AMD Advanced Media Framework) or equivalent hardware encoders via FFmpeg to speed up rendering where possible.
- **Clean UI**: Simple web interface with drag-and-drop support, real-time conversion progress, and instant download capabilities.
- **Local Privacy**: Runs 100% on your own hardware. Your personal videos are never sent to external cloud servers.

## Prerequisites
1. **Python 3.8+**
2. **FFmpeg**: Must be installed and accessible via your system PATH.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/vijayakumardevforge/2D-to-3D-SBS-Converter.git
   cd 2D-to-3D-SBS-Converter
   ```

2. Set up the Python environment (optional but recommended):
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. Install the required Python packages:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

## Usage

### 1. Start the Backend
The AI conversion engine runs as a Flask server.
```bash
cd backend
python app.py
```
*The backend will start on `http://127.0.0.1:5000`.*

### 2. Start the Frontend
In a new terminal window, serve the frontend HTML files.
```bash
cd frontend
python -m http.server 8000
```
*Alternatively, you can just open `frontend/index.html` directly in your web browser, or use VS Code Live Server.*

### 3. Convert Videos
- Navigate to `http://127.0.0.1:8000` in your web browser.
- Upload any standard 2D video file (MP4, MKV, WebM, etc.).
- Wait for the conversion to complete and download your new 3D SBS video!

## How it Works
1. The backend receives a video and begins reading it frame-by-frame using OpenCV.
2. The AI depth model generates a greyscale depth map for every single frame.
3. Pixels in the original frame are mathematically shifted horizontally based on the depth map intensity (closer objects shift more than background objects).
4. The script synthesizes distinct Left-Eye and Right-Eye perspectives.
5. The frames are stitched together horizontally (Side-by-Side) and piped directly into FFmpeg to mux the original audio back into a high-quality H.264 output video.

## License
[MIT License](LICENSE)
