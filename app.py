from importlib.resources import path
import os
import uuid
import traceback
from pathlib import Path

from flask import (
    Flask, request, send_file, send_from_directory, jsonify, render_template
)
from dotenv import load_dotenv

from extractor import extract_financials
from report_generator import generate_report
from analyst_agent import synthesize_report

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

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    if "file" not in request.files: 
        return jsonify({"error": "No file uploaded."}), 400
    
    uploaded = request.files["file"]
    company_name_override = request.form.get("company_name", "").strip()

    if not uploaded.filename: 
        return jsonify({"error": "Empty filename."}), 400
        
    if not allowed_file(uploaded.filename): 
        return jsonify({"error": "Unsupported file type."}), 400

    uid = uuid.uuid4().hex
    upload_path = UPLOAD_DIR / f"{uid}.bin"
    uploaded.save(str(upload_path))

    try:
        raw_data = extract_financials(str(upload_path))
        data = synthesize_report(raw_data)

        if company_name_override:
            data["company_name"] = company_name_override
        if not data.get("company_name"):
            data["company_name"] = "Company Report"

        safe_name = "".join(c for c in data["company_name"] if c.isalnum() or c in " _-").strip().replace(" ", "_")
        download_name = f"{safe_name}_{uid[:8]}.pdf" if safe_name else f"Company_Report_{uid[:8]}.pdf"
        stored_pdf_name = f"{uid}.pdf"
        output_path = OUTPUT_DIR / stored_pdf_name
        
        generate_report(data, str(output_path))

        return jsonify({
            "company_name": data.get("company_name"),
            "rating":       data.get("rating"),
            "target_price": data.get("target_price"),
            "download_url": f"/download/{uid}?download_name={download_name}",
        })

    except Exception as exc:
        traceback.print_exc()
        return jsonify({"error": str(exc)}), 500
    finally:
        try: 
            upload_path.unlink()
        except Exception: 
            pass


@app.route("/download/<file_id>")
def download(file_id):
    if len(file_id) != 32 or any(c not in "0123456789abcdef" for c in file_id):
        return "Invalid file id.", 400

    safe_stored_name = f"{file_id}.pdf"
    path = (OUTPUT_DIR / safe_stored_name).resolve(strict=False)
    try:
        path.relative_to(OUTPUT_DIR)
    except ValueError:
        return "Invalid file path.", 400

    if not path.exists() or not path.is_file():
        return "File not found.", 404

    requested_name = request.args.get("download_name", safe_stored_name)
    safe_download_name = Path(requested_name).name
    if not safe_download_name.lower().endswith(".pdf"):
        safe_download_name = f"{safe_download_name}.pdf"

    return send_from_directory(
        directory=str(OUTPUT_DIR),
        path=safe_stored_name,
        as_attachment=True,
        download_name=safe_download_name,
        mimetype="application/pdf",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)