"""Errors raised by document definition resolution."""


class DocumentContractError(Exception):
    """Base error for document contract operations."""


class DefinitionNotFoundError(DocumentContractError):
    """No definition package was found for a document type and variant."""


class InvalidManifestError(DocumentContractError):
    """A manifest exists but cannot be used."""


class InvalidResourceError(DocumentContractError):
    """A declared resource is missing or malformed."""
