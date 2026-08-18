import os
import uuid
import threading
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from ai_converter import convert_to_sbs_ai

app = Flask(__name__)
# Enable CORS so the frontend can communicate with the backend
CORS(app)

# Configure directories
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__name__)), 'uploads')
DOWNLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__name__)), 'downloads')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Allowed extensions
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'mkv', 'avi', 'webm', 'wmv', 'flv', 'm4v', 'ts'}

# Store progress for background jobs
conversion_jobs = {}
conversion_events = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_video_background(job_id, input_path, output_path, output_filename, host_url, cancel_event):
    def progress_callback(percentage):
        conversion_jobs[job_id]['progress'] = percentage
        
    try:
        success = convert_to_sbs_ai(input_path, output_path, progress_callback, cancel_event)
        
        try:
            os.remove(input_path)
        except Exception as e:
            print(f"Failed to remove input file: {e}")
            
        if success:
            download_url = f"{host_url}download/{output_filename}"
            conversion_jobs[job_id]['status'] = 'completed'
            conversion_jobs[job_id]['download_url'] = download_url
            conversion_jobs[job_id]['progress'] = 100
        else:
            conversion_jobs[job_id]['status'] = 'failed'
            conversion_jobs[job_id]['message'] = 'Video conversion failed during processing'
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        with open('backend_error.log', 'w') as f:
            f.write(error_msg)
        print("EXCEPTION IN process_video_background:")
        print(error_msg)
        conversion_jobs[job_id]['status'] = 'failed'
        conversion_jobs[job_id]['message'] = str(e)


@app.route('/convert', methods=['POST'])
def convert_video():
    if 'video' not in request.files:
        print("DEBUG 400: 'video' not in request.files")
        print("DEBUG request.files:", request.files)
        print("DEBUG request.form:", request.form)
        return jsonify({'success': False, 'message': 'No video part in the request'}), 400
    
    file = request.files['video']
    
    if file.filename == '':
        print("DEBUG 400: file.filename is empty")
        return jsonify({'success': False, 'message': 'No selected file'}), 400
        
    if file and allowed_file(file.filename):
        original_filename = secure_filename(file.filename)
        filename_base = os.path.splitext(original_filename)[0]
        ext = os.path.splitext(original_filename)[1]
        
        unique_id = str(uuid.uuid4())[:8]
        job_id = str(uuid.uuid4())
        
        input_filename = f"{filename_base}_{unique_id}{ext}"
        output_filename = f"{filename_base}_SBS_{unique_id}.mp4" 
        
        input_path = os.path.join(UPLOAD_FOLDER, input_filename)
        output_path = os.path.join(DOWNLOAD_FOLDER, output_filename)
        
        file.save(input_path)
        
        conversion_jobs[job_id] = {
            'status': 'processing',
            'progress': 0,
            'download_url': None,
            'message': None
        }
        
        # Create cancel event
        cancel_event = threading.Event()
        conversion_events[job_id] = cancel_event
        
        # Start conversion in background thread
        thread = threading.Thread(
            target=process_video_background, 
            args=(job_id, input_path, output_path, output_filename, request.host_url, cancel_event)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True, 
            'message': 'Video conversion started',
            'job_id': job_id
        })
            
    print(f"DEBUG 400: Invalid file type for filename '{file.filename}'")
    return jsonify({'success': False, 'message': f'Invalid file type: {file.filename}'}), 400

@app.route('/progress/<job_id>', methods=['GET'])
def get_progress(job_id):
    if job_id not in conversion_jobs:
        return jsonify({'success': False, 'message': 'Job not found'}), 404
        
    return jsonify({
        'success': True,
        'job': conversion_jobs[job_id]
    })

@app.route('/cancel/<job_id>', methods=['POST'])
def cancel_job(job_id):
    if job_id in conversion_events:
        conversion_events[job_id].set()
        if job_id in conversion_jobs:
            conversion_jobs[job_id]['status'] = 'cancelled'
            conversion_jobs[job_id]['message'] = 'Conversion stopped by user'
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Job not found'})

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
