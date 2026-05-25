class FileRepository:

    def __init__(self):
        self._files = {}

    def save(
        self,
        filename,
        content,
    ):
        self._files[filename] = content

    def load(
        self,
        filename,
    ):
        return self._files.get(filename)

    def clear(self):
        self._files.clear()


file_repository = FileRepository()