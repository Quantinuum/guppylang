"""A test fixture file with an intentional import-time error."""

# An import that does not exist, causing an import-time error
from a import a  # noqa: F401
