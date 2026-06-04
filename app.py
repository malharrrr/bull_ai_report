import os
import uuid
import traceback
import time
from pathlib import Path

from flask import (
    Flask, request, send_file, send_from_directory, jsonify, render_template
)
from werkzeug.exceptions import NotFound
from dotenv import load_dotenv

from extractor import extract_financials
from report_generator import generate_report
from analyst_agent import synthesize_report
from logging_config import UserActionLogger, track_request_duration, logger

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024 

UPLOAD_DIR = Path("uploads").resolve()
OUTPUT_DIR = Path("outputs").resolve()
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".csv"}

def allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

def get_client_ip():
    """Extract client IP from request."""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

@app.route("/")
def index():
    UserActionLogger.log_api_request("GET", "/", get_client_ip())
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
@track_request_duration
def generate():
    start_time = time.time()
    file_id = uuid.uuid4().hex
    client_ip = get_client_ip()
    
    UserActionLogger.log_api_request("POST", "/generate", client_ip)
    
    if "file" not in request.files: 
        UserActionLogger.log_error("validation", file_id, "No file uploaded", "MissingFileError")
        return jsonify({"error": "No file uploaded."}), 400
    
    uploaded = request.files["file"]
    company_name_override = request.form.get("company_name", "").strip()

    if not uploaded.filename: 
        UserActionLogger.log_error("validation", file_id, "Empty filename", "EmptyFilenameError")
        return jsonify({"error": "Empty filename."}), 400
        
    if not allowed_file(uploaded.filename): 
        UserActionLogger.log_error(
            "validation", file_id, 
            f"Unsupported file type: {uploaded.filename}", 
            "UnsupportedFileTypeError"
        )
        return jsonify({"error": "Unsupported file type."}), 400

    file_size = len(uploaded.read())
    uploaded.seek(0) 
    UserActionLogger.log_file_upload(uploaded.filename, file_size, company_name_override)

    suffix = Path(uploaded.filename).suffix.lower()
    upload_path = UPLOAD_DIR / f"{file_id}{suffix}"
    uploaded.save(str(upload_path))

    try:
        UserActionLogger.log_extraction_start(file_id, uploaded.filename)
        raw_data = extract_financials(str(upload_path))
        metrics_count = len(raw_data.get("annual_estimates", []))
        UserActionLogger.log_extraction_complete(file_id, metrics_count)

        UserActionLogger.log_analysis_start(file_id, company_name_override or "Unknown")
        data = synthesize_report(raw_data)
        UserActionLogger.log_analysis_complete(
            file_id, 
            data.get("rating", "N/A"), 
            data.get("target_price", 0)
        )

        if company_name_override:
            data["company_name"] = company_name_override
        if not data.get("company_name"):
            data["company_name"] = "Company Report"

        safe_name = "".join(c for c in data["company_name"] if c.isalnum() or c in " _-").strip().replace(" ", "_")
        download_name = f"{safe_name}_{file_id[:8]}.pdf" if safe_name else f"Company_Report_{file_id[:8]}.pdf"
        stored_pdf_name = f"{file_id}.pdf"
        output_path = OUTPUT_DIR / stored_pdf_name
        
        UserActionLogger.log_pdf_generation_start(file_id)
        generate_report(data, str(output_path))
        
        pdf_size = output_path.stat().st_size
        UserActionLogger.log_pdf_generation_complete(file_id, pdf_size)
        
        duration_ms = (time.time() - start_time) * 1000
        UserActionLogger.log_api_response("/generate", 200, duration_ms)

        return jsonify({
            "company_name": data.get("company_name"),
            "rating":       data.get("rating"),
            "target_price": data.get("target_price"),
            "download_url": f"/download/{file_id}?download_name={download_name}",
        })

    except Exception as exc:
        error_type = type(exc).__name__
        error_msg = str(exc)
        
        traceback.print_exc()
        UserActionLogger.log_error(
            "generation",
            file_id,
            error_msg,
            error_type
        )
        
        duration_ms = (time.time() - start_time) * 1000
        UserActionLogger.log_api_response("/generate", 500, duration_ms)
        
        return jsonify({"error": error_msg}), 500
    
    finally:
        try: 
            upload_path.unlink()
            UserActionLogger.log_file_cleanup(file_id, str(upload_path), True)
        except Exception as e: 
            UserActionLogger.log_file_cleanup(file_id, str(upload_path), False)


@app.route("/download/<file_id>")
def download(file_id):
    client_ip = get_client_ip()
    UserActionLogger.log_api_request("GET", f"/download/{file_id}", client_ip)
    
    if len(file_id) != 32 or any(c not in "0123456789abcdef" for c in file_id):
        UserActionLogger.log_error("validation", file_id, "Invalid file ID format", "InvalidFileIdError")
        return "Invalid file id.", 400

    safe_stored_name = f"{file_id}.pdf"

    requested_name = request.args.get("download_name", safe_stored_name)
    safe_download_name = Path(requested_name).name
    if not safe_download_name.lower().endswith(".pdf"):
        safe_download_name = f"{safe_download_name}.pdf"

    try:
        UserActionLogger.log_pdf_download(file_id, safe_download_name)
        return send_from_directory(
            directory=str(OUTPUT_DIR),
            path=safe_stored_name,
            as_attachment=True,
            download_name=safe_download_name,
            mimetype="application/pdf",
        )
    except NotFound:
        UserActionLogger.log_error("download", file_id, "PDF file not found", "FileNotFoundError")
        return "File not found.", 404


@app.before_request
def before_request():
    """Attach request start time for duration tracking."""
    request.start_time = time.time()

@app.after_request
def after_request(response):
    """Log all responses with status code."""
    if hasattr(request, 'start_time'):
        duration_ms = (time.time() - request.start_time) * 1000
        UserActionLogger.log_api_response(request.path, response.status_code, duration_ms)
    return response

@app.errorhandler(404)
def not_found(e):
    UserActionLogger.log_error("routing", "N/A", "Route not found", "NotFoundError")
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    UserActionLogger.log_error("server", "N/A", str(e), "InternalServerError")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    logger.info("Starting Bull AI application")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)