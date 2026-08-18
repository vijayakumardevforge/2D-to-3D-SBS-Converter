import subprocess
import os
import cv2
import numpy as np
import torch
from transformers import pipeline
from transformers.utils import logging
logging.disable_progress_bar()
from PIL import Image

def convert_to_sbs_ai(input_path, output_path, progress_callback=None, cancel_event=None):
    """
    Converts a standard 2D video to true 3D SBS format using AI depth estimation.
    """
    ffmpeg_path = r"C:\Users\JeyK\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin\ffmpeg.exe"
    if not os.path.exists(ffmpeg_path):
        ffmpeg_path = 'ffmpeg'

    try:
        if progress_callback:
            progress_callback(0.01)
            
        print("Loading AI Depth Model...")
        # Use GPU if available, else CPU
        device = 0 if torch.cuda.is_available() else -1
        # Using a fast, lightweight depth model
        pipe = pipeline("depth-estimation", model="Intel/dpt-swinv2-tiny-256", device=device)
        
        # Windows Media Foundation frequently deadlocks in background threads when decoding WebM (VP9).
        # We use a lightning-fast hardware pre-conversion (h264_amf) to make it an MP4 (H.264) first.
        temp_input_path = None
        if input_path.lower().endswith(('.webm', '.ts', '.flv')):
            print("Running 9-second hardware pre-conversion for WebM...")
            temp_input_path = input_path + "_temp.mp4"
            convert_cmd = [
                ffmpeg_path, '-y', '-nostdin', '-i', input_path, 
                '-c:v', 'h264_amf', '-b:v', '30M', 
                '-c:a', 'copy', temp_input_path
            ]
            subprocess.run(convert_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
            if os.path.exists(temp_input_path):
                input_path = temp_input_path
        
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            print("Error opening video")
            return False
            
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Hardware encoders usually have a 4096 width limit for H.264.
        # SBS doubles the width, so max input width is 2048.
        width = original_width
        height = original_height
        
        if width > 2048:
            scale = 2048 / width
            width = 2048
            height = int(height * scale)
            # Ensure even dimensions
            if height % 2 != 0: height -= 1
            
        out_width = width * 2
        
        # Start ffmpeg process to receive raw frames and mux audio
        command = [
            ffmpeg_path,
            '-y',
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-s', f"{out_width}x{height}",
            '-pix_fmt', 'bgr24',
            '-r', str(fps),
            '-i', '-',  # Input from stdin (raw frames)
            '-i', input_path,  # Input for audio
            '-map', '0:v',
            '-map', '1:a?',
            '-c:v', 'h264_amf',
            '-quality', 'quality',
            '-b:v', '25M',
            '-metadata:s:v:0', 'stereo_mode=1',
            '-c:a', 'aac',
            output_path
        ]
        
        process = subprocess.Popen(command, stdin=subprocess.PIPE)
        
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            if cancel_event and cancel_event.is_set():
                print("Cancellation requested by user.")
                break
                
            frame_idx += 1
            if progress_callback and total_frames > 0:
                # Update progress based on frames processed
                percentage = (frame_idx / total_frames) * 100
                progress_callback(round(min(percentage, 99.99), 2)) # Reserve 100% for final muxing
                
            # Resize frame if we exceeded hardware limits
            if frame.shape[1] != width or frame.shape[0] != height:
                frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
                
            # Convert BGR to RGB for the AI model
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb_frame)
            
            # Predict depth map
            result = pipe(pil_img)
            depth_img = result["depth"]
            
            # Convert depth PIL Image to numpy array (0-255)
            depth_map = np.array(depth_img, dtype=np.float32)
            
            # Resize depth map to match original frame size
            depth_map_resized = cv2.resize(depth_map, (width, height), interpolation=cv2.INTER_LINEAR)
            
            # Smooth the depth map slightly to reduce jagged edges on objects
            depth_map_resized = cv2.GaussianBlur(depth_map_resized, (15, 15), 0)
            
            # Normalize to 0.0 - 1.0
            depth_map_normalized = depth_map_resized / 255.0
            
            # 3D Divergence factor (controls how much objects pop out)
            # Increased to 4.5% for a stronger, more noticeable 3D effect
            divergence = int(width * 0.045) 
            
            y, x = np.mgrid[0:height, 0:width]
            
            # Shift objects based on depth (closer objects shift more)
            shift = (depth_map_normalized * divergence).astype(np.int32)
            
            # Left eye: shift pixels to the right to simulate left-eye perspective
            x_src_left = np.clip(x - shift // 2, 0, width - 1)
            left_eye = frame[y, x_src_left]
            
            # Right eye: shift pixels to the left to simulate right-eye perspective
            x_src_right = np.clip(x + shift // 2, 0, width - 1)
            right_eye = frame[y, x_src_right]
            
            # Combine left and right horizontally
            sbs_frame = np.hstack((left_eye, right_eye))
            
            # Write processed frame to FFmpeg pipe
            process.stdin.write(sbs_frame.tobytes())
            
        cap.release()
        process.stdin.close()
        
        if temp_input_path and os.path.exists(temp_input_path):
            try:
                os.remove(temp_input_path)
            except:
                pass
        
        if cancel_event and cancel_event.is_set():
            process.terminate()
            process.wait()
            try:
                if os.path.exists(output_path):
                    os.remove(output_path)
            except:
                pass
            return False
            
        process.wait()
        
        if process.returncode == 0:
            if progress_callback:
                progress_callback(100)
            return True
        else:
            print(f"FFmpeg error with return code {process.returncode}")
            return False
            
    except Exception as e:
        import traceback
        with open('ai_error.log', 'w') as f:
            f.write(traceback.format_exc())
        print(f"AI Conversion Error: {e}")
        return False
