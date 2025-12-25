class AppError(Exception):
    """Base class for application exceptions"""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)

class FileUploadError(AppError):
    """Raised when file upload fails"""
    pass

class FileDownloadError(AppError):
    """Raised when file download fails"""
    pass

class FileValidationError(AppError):
    """Raised when file validation fails"""
    pass
