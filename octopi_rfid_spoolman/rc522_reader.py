from mfrc522 import SimpleMFRC522


class RC522Reader:
    """Small wrapper around the mfrc522 reader used by the plugin."""

    def __init__(self):
        self._reader = SimpleMFRC522()

    def read_id_no_block(self):
        """Return the detected tag UID, or None when no tag is present."""
        return self._reader.read_id_no_block()
