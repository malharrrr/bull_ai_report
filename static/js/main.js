const dropZone    = document.getElementById('dropZone');
const fileInput   = document.getElementById('fileInput');
const dropContent = document.getElementById('dropContent');
const form        = document.getElementById('uploadForm');
const submitBtn   = document.getElementById('submitBtn');
const progressWrap = document.getElementById('progressWrap');
const progressFill = document.getElementById('progressFill');
const statusText   = document.getElementById('statusText');
const resultBox    = document.getElementById('resultBox');
const errorBox     = document.getElementById('errorBox');

dropZone.addEventListener('click', e => {
  if (e.target.tagName !== 'U') fileInput.click();
});
dropZone.addEventListener('dragover', e => {
  e.preventDefault();
  dropZone.classList.add('drag-over');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  fileInput.files = e.dataTransfer.files;
  updateDrop();
});
fileInput.addEventListener('change', updateDrop);

function updateDrop() {
  if (!fileInput.files.length) return;
  const f = fileInput.files[0];
  const size = f.size < 1048576
    ? (f.size / 1024).toFixed(1) + ' KB'
    : (f.size / 1048576).toFixed(2) + ' MB';
  dropContent.textContent = '';
  const selectedEl = document.createElement('div');
  selectedEl.className = 'drop-selected';
  selectedEl.textContent = '✓ File selected';

  const nameEl = document.createElement('div');
  nameEl.className = 'drop-selected-name';
  nameEl.appendChild(document.createTextNode(f.name));
  nameEl.appendChild(document.createTextNode(' \u00A0·\u00A0 '));
  nameEl.appendChild(document.createTextNode(size));

  dropContent.appendChild(selectedEl);
  dropContent.appendChild(nameEl);
}	

function setStep(n, pct, msg) {
  progressFill.style.width = pct + '%';
  statusText.textContent = msg;
  [1, 2, 3].forEach(i => {
    const el = document.getElementById('step' + i);
    el.className = 'step' + (i < n ? ' done' : i === n ? ' active' : '');
  });
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();

  const file    = fileInput.files[0];
  const company = document.getElementById('companyName').value.trim();

  if (!file)    { alert('Please select a document.'); return; }
  if (!company) { alert('Please enter a company name.'); return; }

  resultBox.style.display  = 'none';
  errorBox.style.display   = 'none';
  progressWrap.style.display = 'block';
  submitBtn.disabled = true;
  setStep(1, 15, 'extracting financial data from document…');

  const fd = new FormData();
  fd.append('file', file);
  fd.append('company_name', company);

  try {
    const t1 = setTimeout(() => setStep(2, 50, 'analyst agent synthesising estimates & ratings…'), 3500);
    const t2 = setTimeout(() => setStep(3, 80, 'rendering pdf report…'), 9000);

    const resp = await fetch('/generate', { method: 'POST', body: fd });
    clearTimeout(t1);
    clearTimeout(t2);

    const json = await resp.json();
    if (!resp.ok || json.error) throw new Error(json.error || 'Unknown server error');

    setStep(3, 100, 'done.');
    setTimeout(() => {
      progressWrap.style.display = 'none';
      document.getElementById('resultMeta').textContent =
        `${json.company_name}  ·  Rating: ${json.rating || '—'}  ·  Target: Rs. ${json.target_price || '—'}`;
      document.getElementById('downloadLink').href = json.download_url;
      resultBox.style.display = 'block';
    }, 600);

  } catch (err) {
    progressWrap.style.display = 'none';
    document.getElementById('errorText').textContent = err.message;
    errorBox.style.display = 'block';
  } finally {
    submitBtn.disabled = false;
  }
});