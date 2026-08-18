import subprocess
import os
import re

def get_video_duration(input_path, ffprobe_path):
    try:
        command = [
            ffprobe_path,
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            input_path
        ]
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return float(result.stdout.strip())
    except Exception as e:
        print(f"Could not get video duration: {e}")
        return 0.0

def convert_to_sbs(input_path, output_path, progress_callback=None):
    """
    Converts a standard 2D video to a duplicated Side-By-Side (SBS) format using FFmpeg.
    If progress_callback is provided, it will be called with an integer percentage (0-100).
    """
    ffmpeg_path = r"C:\Users\JeyK\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin\ffmpeg.exe"
    ffprobe_path = ffmpeg_path.replace('ffmpeg.exe', 'ffprobe.exe')
    
    if not os.path.exists(ffmpeg_path):
        ffmpeg_path = 'ffmpeg'
        ffprobe_path = 'ffprobe'

    # Get total duration for progress calculation
    total_duration = get_video_duration(input_path, ffprobe_path)

    command = [
        ffmpeg_path,
        '-i', input_path,
        '-filter_complex', '[0:v][0:v]hstack=inputs=2[v]',
        '-map', '[v]',
        '-map', '0:a?', 
        '-c:v', 'h264_amf', 
        '-quality', 'quality', 
        '-b:v', '15M', 
        '-metadata:s:v:0', 'stereo_mode=1',
        '-c:a', 'aac', 
        '-y', 
        output_path
    ]
    
    try:
        print(f"Starting conversion: {input_path} -> {output_path}")
        
        process = subprocess.Popen(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            universal_newlines=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        # Regex to find time=HH:MM:SS.ms in ffmpeg output
        time_regex = re.compile(r"time=(\d{2}):(\d{2}):(\d{2}\.\d{2})")
        
        for line in process.stdout:
            if progress_callback and total_duration > 0:
                match = time_regex.search(line)
                if match:
                    hours, minutes, seconds = match.groups()
                    current_time = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
                    percentage = int((current_time / total_duration) * 100)
                    progress_callback(min(percentage, 100))

        process.wait()
        
        if process.returncode == 0:
            print("Conversion completed successfully.")
            if progress_callback:
                progress_callback(100)
            return True
        else:
            print(f"FFmpeg error occurred with return code {process.returncode}")
            return False
            
    except Exception as e:
        print(f"Error during FFmpeg execution: {e}")
        return False
