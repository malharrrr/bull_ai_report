import logging
import logging.handlers
import os
import json
from datetime import datetime
from functools import wraps

# Configure logging for Render
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

def setup_logging():
    """Initialize logging with Render-compatible handlers."""
    
    logger = logging.getLogger("bull_ai")
    logger.setLevel(getattr(logging, LOG_LEVEL))
    
    logger.handlers = []
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, LOG_LEVEL))
    
    # Structured format for Render dashboard parsing
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    log_dir = os.getenv("LOG_DIR", "/tmp")
    if os.access(log_dir, os.W_OK):
        try:
            file_handler = logging.handlers.RotatingFileHandler(
                filename=os.path.join(log_dir, "bull_ai.log"),
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=3,
                encoding='utf-8'
            )
            file_handler.setLevel(getattr(logging, LOG_LEVEL))
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"Could not setup file logging: {e}")
    
    return logger

logger = setup_logging()

class UserActionLogger:
    """ API for logging user actions with structured data."""
    
    @staticmethod
    def log_file_upload(filename: str, file_size: int, company_name: str):
        """Log file upload event."""
        logger.info(
            f"FILE_UPLOAD | filename={filename} | size_bytes={file_size} | company={company_name}"
        )
    
    @staticmethod
    def log_extraction_start(file_id: str, filename: str):
        """Log extraction phase start."""
        logger.info(f"EXTRACTION_START | file_id={file_id} | filename={filename}")
    
    @staticmethod
    def log_extraction_complete(file_id: str, metrics_count: int):
        """Log successful extraction."""
        logger.info(f"EXTRACTION_COMPLETE | file_id={file_id} | metrics_extracted={metrics_count}")
    
    @staticmethod
    def log_market_data_fetch(ticker: str, success: bool, error_msg: str = None):
        """Log market data fetch attempt."""
        if success:
            logger.info(f"MARKET_DATA_SUCCESS | ticker={ticker}")
        else:
            logger.warning(f"MARKET_DATA_FAILED | ticker={ticker} | error={error_msg}")
    
    @staticmethod
    def log_analysis_start(file_id: str, company_name: str):
        """Log analysis phase start."""
        logger.info(f"ANALYSIS_START | file_id={file_id} | company={company_name}")
    
    @staticmethod
    def log_analysis_complete(file_id: str, rating: str, target_price: float):
        """Log analysis completion with results."""
        logger.info(
            f"ANALYSIS_COMPLETE | file_id={file_id} | rating={rating} | target_price={target_price}"
        )
    
    @staticmethod
    def log_pdf_generation_start(file_id: str):
        """Log PDF generation start."""
        logger.info(f"PDF_GENERATION_START | file_id={file_id}")
    
    @staticmethod
    def log_pdf_generation_complete(file_id: str, pdf_size: int):
        """Log PDF generation completion."""
        logger.info(f"PDF_GENERATION_COMPLETE | file_id={file_id} | pdf_size_bytes={pdf_size}")
    
    @staticmethod
    def log_pdf_download(file_id: str, download_name: str):
        """Log PDF download."""
        logger.info(f"PDF_DOWNLOAD | file_id={file_id} | download_name={download_name}")
    
    @staticmethod
    def log_error(phase: str, file_id: str, error_msg: str, error_type: str = None):
        """Log errors with context."""
        logger.error(
            f"ERROR | phase={phase} | file_id={file_id} | type={error_type} | msg={error_msg}"
        )
    
    @staticmethod
    def log_file_cleanup(file_id: str, filepath: str, success: bool):
        """Log temporary file cleanup."""
        status = "success" if success else "failed"
        logger.debug(f"FILE_CLEANUP | file_id={file_id} | status={status} | path={filepath}")
    
    @staticmethod
    def log_api_request(method: str, endpoint: str, client_ip: str = None):
        """Log incoming API requests."""
        logger.info(f"API_REQUEST | method={method} | endpoint={endpoint} | ip={client_ip}")
    
    @staticmethod
    def log_api_response(endpoint: str, status_code: int, response_time_ms: float = None):
        """Log API responses."""
        logger.info(
            f"API_RESPONSE | endpoint={endpoint} | status={status_code} | duration_ms={response_time_ms}"
        )

def track_request_duration(func):
    """Decorator to track request duration and log it."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        import time
        start = time.time()
        try:
            result = func(*args, **kwargs)
            duration = (time.time() - start) * 1000
            logger.info(f"REQUEST_DURATION | function={func.__name__} | duration_ms={duration:.2f}")
            return result
        except Exception as e:
            duration = (time.time() - start) * 1000
            logger.error(
                f"REQUEST_FAILED | function={func.__name__} | duration_ms={duration:.2f} | error={str(e)}"
            )
            raise
    return wrapper