# Bull AI: Automated Equity Research Report Generator

Bull AI is an automated pipeline that ingests raw corporate earnings documents (PDFs, TXT, CSV) and generates professional, broker-grade Equity Research Reports. By combining Large Language Models (LLMs) with live financial market data and programmatic PDF generation, it acts as an autonomous Junior Analyst.

> **Note:** This project was built as a Proof of Concept (POC). While fully functional, there is significant room for improvement, specifically by upgrading to a more powerful reasoning model and decoupling the embedded HTML UI into a dedicated React/Next.js frontend.

## How It Works

1. **Extraction (`extractor.py`)**: Uses Google's Gemini AI to parse unstructured corporate documents and extract a strict JSON schema of financial metrics (Revenue, EBITDA, PAT, Shareholding, etc.).
2. **Analysis & Synthesis (`analyst_agent.py`)**: 
   - Fetches real-time market data (CMP, Market Cap, Beta) using `yfinance`.
   - Prompts the LLM to act as a Lead Equity Research Analyst to synthesize the data.
   - Automatically calculates an investment rating (BUY, HOLD, SELL), projects missing forward estimates (FY26E/FY27E), estimates a Target Price, and writes a professional outlook paragraph.
3. **Report Generation (`report_generator.py`)**: Uses `reportlab` and `matplotlib` to dynamically render the synthesized data into a polished A4 PDF, complete with custom charts for Revenue, EBITDA margins, and PAT trends.
4. **Web Interface (`app.py`)**: A Flask-based web application that provides a drag-and-drop UI to upload documents and instantly download the generated PDF report.

## Setup & Installation

### Prerequisites
* Python 3.12+
* A Google Gemini API Key

### Installation

1. **Clone the repository and navigate to the directory:**
   ```bash
   cd bull_ai_report
   ```

2. **Install the dependencies:**
   It is recommended to use a virtual environment.
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   Create a `.env` file in the root directory and add your Gemini API key:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

4. **Run the Application:**
   ```bash
   python app.py
   ```

5. **Access the Web UI:**
   Open your browser and navigate to `http://localhost:5000`.

## Roadmap & Future Improvements

Because this was developed as a rapid POC, here are the immediate areas for future development:

1. **Model Upgrades:** Currently utilizing `gemini-3.1-flash-lite` for speed and cost-efficiency. Upgrading to a heavier reasoning model (like Gemini Pro or Claude 4.6 Sonnet) would vastly improve the accuracy of forward-looking estimates and nuanced valuation commentary.
2. **Decoupled Frontend:** The UI is currently a monolithic HTML string embedded directly inside `app.py`. Moving this to a modern, decoupled frontend architecture (like React, Next.js, or Vue) would allow for better state management, richer loading animations, and an interactive dashboard before PDF generation.
3. **RAG Integration:** Implement Retrieval-Augmented Generation (RAG) over historical company reports to ensure the AI's outlook paragraph has deeper historical context.