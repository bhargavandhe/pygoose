class PygooseError(Exception):
    """Base exception for all Pygoose errors."""


class DocumentNotFound(PygooseError):
    """Raised when a document is not found in the database."""


class NotConnected(PygooseError):
    """Raised when attempting to use a database that is not connected."""


class MultipleDocumentsFound(PygooseError):
    """Raised when a single document was expected but multiple were found."""
