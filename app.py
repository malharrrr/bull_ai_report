import os
import uuid
import traceback
from pathlib import Path

from flask import (
    Flask, request, send_file, jsonify
)
from dotenv import load_dotenv

from extractor import extract_financials
from report_generator import generate_report
from analyst_agent import synthesize_report

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024 

UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".csv"}

def allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bull AI — Research Report Generator</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', Arial, sans-serif; background: #f0f4f8; color: #1a2a3a; min-height: 100vh; display: flex; flex-direction: column; align-items: center; }

  header { width: 100%; background: #003366; color: white; padding: 18px 40px; display: flex; align-items: center; gap: 14px; }
  header h1 { font-size: 22px; font-weight: 700; letter-spacing: 0.5px; }
  header span { font-size: 12px; opacity: 0.7; }

  .card { background: white; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); padding: 40px; width: 100%; max-width: 680px; margin: 48px auto; }
  .card h2 { font-size: 18px; color: #003366; margin-bottom: 6px; }
  .card .subtitle { font-size: 13px; color: #666; margin-bottom: 28px; }

  label { display: block; font-size: 13px; font-weight: 600; color: #334; margin-bottom: 6px; }
  input[type="text"], input[type="file"], select {
    width: 100%; padding: 10px 14px; border: 1.5px solid #cdd; border-radius: 8px;
    font-size: 14px; margin-bottom: 20px; outline: none; transition: border 0.2s;
  }
  input:focus, select:focus { border-color: #003366; }

  .drop-zone {
    border: 2px dashed #aac; border-radius: 10px; padding: 30px; text-align: center;
    cursor: pointer; transition: background 0.2s; margin-bottom: 20px; color: #667;
    font-size: 13px;
  }
  .drop-zone:hover { background: #f0f4ff; border-color: #003366; }
  .drop-zone input { display: none; }

  .btn {
    width: 100%; padding: 13px; background: #003366; color: white; font-size: 15px;
    font-weight: 600; border: none; border-radius: 8px; cursor: pointer; transition: background 0.2s;
    letter-spacing: 0.3px;
  }
  .btn:hover { background: #154690; }
  .btn:disabled { background: #99aacc; cursor: not-allowed; }

  .progress-wrap { display: none; margin-top: 24px; }
  .progress-bar { height: 6px; background: #e0e0e0; border-radius: 3px; overflow: hidden; margin-bottom: 10px; }
  .progress-fill { height: 100%; width: 0%; background: #003366; transition: width 0.4s; border-radius: 3px; }
  .status { font-size: 13px; color: #555; text-align: center; }

  .result-box { display: none; margin-top: 24px; padding: 20px; background: #e8f5e9; border-radius: 10px; text-align: center; }
  .result-box h3 { color: #1e5c2a; font-size: 16px; margin-bottom: 10px; }
  .download-btn {
    display: inline-block; padding: 10px 28px; background: #1e8449; color: white;
    border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 14px;
    margin-top: 8px; transition: background 0.2s;
  }
  .download-btn:hover { background: #155d32; }

  .error-box { display: none; margin-top: 24px; padding: 20px; background: #fff0f0; border-radius: 10px; }
  .error-box h3 { color: #c0392b; font-size: 14px; margin-bottom: 6px; }
  .error-box pre { font-size: 11px; color: #555; white-space: pre-wrap; word-break: break-all; }
  footer { font-size: 12px; color: #999; padding: 24px; }
</style>
</head>
<body>
<header>
  <div>
    <h1> Bull AI — Research Report Generator</h1>
    <span>Upload a financial document → Get an Equity Research PDF</span>
  </div>
</header>

<div class="card">
  <h2>Generate Equity Research Report</h2>
  <p class="subtitle">Supports PDF, TXT, and CSV financial documents. Powered by Gemini AI.</p>

  <form id="uploadForm">
    <label for="companyName">Company Name</label>
    <input type="text" id="companyName" name="company_name" placeholder="e.g. JSW Energy Limited" required>

    <label>Upload Financial Document</label>
    <div class="drop-zone" id="dropZone">
      <input type="file" id="fileInput" name="file" accept=".pdf,.txt,.csv">
      <div id="dropText">📄 Drag &amp; drop your file here, or <u>click to browse</u><br><small>PDF, TXT, CSV — max 32 MB</small></div>
    </div>

    <button type="submit" class="btn" id="submitBtn">Generate Report</button>
  </form>

  <div class="progress-wrap" id="progressWrap">
    <div class="progress-bar"><div class="progress-fill" id="progressFill"></div></div>
    <div class="status" id="statusText">Uploading document…</div>
  </div>

  <div class="result-box" id="resultBox">
    <h3>✅ Report Generated Successfully!</h3>
    <p id="resultCompany" style="font-size:13px;color:#333;margin-bottom:8px;"></p>
    <a href="#" id="downloadLink" class="download-btn">⬇ Download PDF Report</a>
  </div>

  <div class="error-box" id="errorBox">
    <h3>❌ Error generating report</h3>
    <pre id="errorText"></pre>
  </div>
</div>

<footer>Bull AI © 2026 — For demonstration purposes only. Not financial advice.</footer>

<script>
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const dropText  = document.getElementById('dropText');
const form      = document.getElementById('uploadForm');
const submitBtn = document.getElementById('submitBtn');
const progressWrap = document.getElementById('progressWrap');
const progressFill = document.getElementById('progressFill');
const statusText   = document.getElementById('statusText');
const resultBox    = document.getElementById('resultBox');
const errorBox     = document.getElementById('errorBox');

dropZone.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.style.background = '#f0f4ff'; });
dropZone.addEventListener('dragleave', () => { dropZone.style.background = ''; });
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.style.background = '';
  fileInput.files = e.dataTransfer.files;
  updateDropText();
});
fileInput.addEventListener('change', updateDropText);

function updateDropText() {
  if (fileInput.files.length) {
    dropText.innerHTML = `✅ <b>${fileInput.files[0].name}</b> (${(fileInput.files[0].size/1024/1024).toFixed(2)} MB)`;
  }
}

function setProgress(pct, msg) {
  progressFill.style.width = pct + '%';
  statusText.textContent = msg;
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const file = fileInput.files[0];
  const companyName = document.getElementById('companyName').value.trim();

  if (!file) { alert('Please select a file.'); return; }
  if (!companyName) { alert('Please enter a company name.'); return; }

  resultBox.style.display = 'none';
  errorBox.style.display  = 'none';
  progressWrap.style.display = 'block';
  submitBtn.disabled = true;
  setProgress(20, 'Uploading & Extracting Base PDF Data...');

  const fd = new FormData();
  fd.append('file', file);
  fd.append('company_name', companyName);

  try {
    const resp = await fetch('/generate', { method: 'POST', body: fd });
    setProgress(70, 'Agent Synthesizing Estimates & Ratings...');

    const json = await resp.json();
    if (!resp.ok || json.error) throw new Error(json.error || 'Unknown server error');

    setProgress(95, 'Formatting PDF...');
    setTimeout(() => {
        setProgress(100, 'Done!');
        setTimeout(() => { progressWrap.style.display = 'none'; }, 800);
        document.getElementById('resultCompany').textContent = `Company: ${json.company_name}  |  Rating: ${json.rating || '—'}`;
        document.getElementById('downloadLink').href = json.download_url;
        resultBox.style.display = 'block';
    }, 500);

  } catch (err) {
    progressWrap.style.display = 'none';
    document.getElementById('errorText').textContent = err.message;
    errorBox.style.display = 'block';
  } finally {
    submitBtn.disabled = false;
  }
});
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return HTML

@app.route("/generate", methods=["POST"])
def generate():
    if "file" not in request.files: return jsonify({"error": "No file uploaded."}), 400
    uploaded = request.files["file"]
    company_name_override = request.form.get("company_name", "").strip()

    if not uploaded.filename: return jsonify({"error": "Empty filename."}), 400
    if not allowed_file(uploaded.filename): return jsonify({"error": f"Unsupported file type."}), 400

    uid = uuid.uuid4().hex
    suffix = Path(uploaded.filename).suffix.lower()
    upload_path = UPLOAD_DIR / f"{uid}{suffix}"
    uploaded.save(str(upload_path))

    try:
        raw_data = extract_financials(str(upload_path))
        data = synthesize_report(raw_data)

        if company_name_override:
            data["company_name"] = company_name_override
        if not data.get("company_name"):
            data["company_name"] = "Company Report"

        safe_name = "".join(c for c in data["company_name"] if c.isalnum() or c in " _-")
        pdf_name = f"{safe_name.strip().replace(' ','_')}_{uid[:8]}.pdf"
        output_path = OUTPUT_DIR / pdf_name
        
        generate_report(data, str(output_path))

        return jsonify({
            "company_name": data.get("company_name"),
            "rating":       data.get("rating"),
            "target_price": data.get("target_price"),
            "download_url": f"/download/{pdf_name}",
        })

    except Exception as exc:
        traceback.print_exc()
        return jsonify({"error": str(exc)}), 500
    finally:
        try: upload_path.unlink()
        except Exception: pass

@app.route("/download/<filename>")
def download(filename):
    safe = Path(filename).name
    path = OUTPUT_DIR / safe
    if not path.exists(): return "File not found.", 404
    return send_file(str(path), as_attachment=True, download_name=safe, mimetype="application/pdf")

if __name__ == "__main__":
    print("=" * 50)
    print("  Bull AI Report Generator")
    print("  http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, port=5000)