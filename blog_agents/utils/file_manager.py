"""File I/O utilities for blog agents."""

import json
import aiofiles
from pathlib import Path
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class FileManager:
    """Manager for file operations."""

    def __init__(self, base_dir: str = "outputs"):
        """Initialize file manager.

        Args:
            base_dir: Base directory for file operations
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def write_json(self, filename: str, data: Dict[str, Any]) -> Path:
        """Write JSON data to file.

        Args:
            filename: Name of file to write
            data: Data to write

        Returns:
            Path to written file
        """
        filepath = self.base_dir / filename
        async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(data, indent=2, ensure_ascii=False))
        logger.info(f"Wrote JSON to {filepath}")
        return filepath

    async def read_json(self, filename: str) -> Optional[Dict[str, Any]]:
        """Read JSON data from file.

        Args:
            filename: Name of file to read

        Returns:
            Parsed JSON data or None if file doesn't exist
        """
        filepath = self.base_dir / filename
        if not filepath.exists():
            logger.warning(f"File not found: {filepath}")
            return None

        async with aiofiles.open(filepath, 'r', encoding='utf-8') as f:
            content = await f.read()
            return json.loads(content)

    async def write_text(self, filename: str, content: str) -> Path:
        """Write text content to file.

        Args:
            filename: Name of file to write
            content: Text content to write

        Returns:
            Path to written file
        """
        filepath = self.base_dir / filename
        async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
            await f.write(content)
        logger.info(f"Wrote text to {filepath}")
        return filepath

    async def read_text(self, filename: str) -> Optional[str]:
        """Read text content from file.

        Args:
            filename: Name of file to read

        Returns:
            File content or None if file doesn't exist
        """
        filepath = self.base_dir / filename
        if not filepath.exists():
            logger.warning(f"File not found: {filepath}")
            return None

        async with aiofiles.open(filepath, 'r', encoding='utf-8') as f:
            return await f.read()

    def exists(self, filename: str) -> bool:
        """Check if file exists.

        Args:
            filename: Name of file to check

        Returns:
            True if file exists, False otherwise
        """
        return (self.base_dir / filename).exists()

    def list_files(self, pattern: str = "*") -> list[Path]:
        """List files matching pattern.

        Args:
            pattern: Glob pattern to match

        Returns:
            List of matching file paths
        """
        return list(self.base_dir.glob(pattern))

    async def delete(self, filename: str) -> bool:
        """Delete file.

        Args:
            filename: Name of file to delete

        Returns:
            True if deleted, False if file didn't exist
        """
        filepath = self.base_dir / filename
        if filepath.exists():
            filepath.unlink()
            logger.info(f"Deleted {filepath}")
            return True
        return False


def read_text_sync(filepath: str | Path) -> str:
    """Synchronously read text file.

    Args:
        filepath: Path to file

    Returns:
        File content

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def write_text_sync(filepath: str | Path, content: str) -> Path:
    """Synchronously write text file.

    Args:
        filepath: Path to file
        content: Text content to write

    Returns:
        Path to written file
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

    logger.info(f"Wrote text to {path}")
    return path
