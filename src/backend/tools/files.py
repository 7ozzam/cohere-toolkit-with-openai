from enum import StrEnum
from typing import Any, Dict, List

import backend.crud.file as file_crud
from backend.tools.base import BaseTool


class FileToolsArtifactTypes(StrEnum):
    local_file = "file"

class ReadFileTool(BaseTool):
    """
    Tool to read a file from the file system.
    """

    NAME = "read_document"
    MAX_NUM_CHUNKS = 10
    SEARCH_LIMIT = 5

    def __init__(self):
        pass

    @classmethod
    def is_available(cls) -> bool:
        return True

    async def call(self, parameters: dict, **kwargs: Any) -> List[Dict[str, Any]]:
        print("Read File is Called With Params", parameters)
        file = parameters.get("file")
        _file_id = parameters.get("file_id")
        _file_name = parameters.get("filename")
        
        session = kwargs.get("session")
        user_id = kwargs.get("user_id")
        if not file and not _file_id and not _file_name:
            return []
        elif file:
            _, file_id = file
            retrieved_file = file_crud.get_file(session, file_id, user_id)    
        elif _file_name and not _file_id:
            retrieved_file = file_crud.get_file_by_name(session, _file_name, user_id)
        elif _file_id:
            retrieved_file = file_crud.get_file(session, _file_id, user_id)
            
        
        
        
        if not retrieved_file:
            return []

        return [
            {
                "text": retrieved_file.file_content,
                "title": retrieved_file.file_name,
                "url": retrieved_file.file_name,
            }
        ]

class SearchFileTool(BaseTool):
    """
    Tool to query a list of files.
    """

    NAME = "search_file"
    MAX_NUM_CHUNKS = 10
    SEARCH_LIMIT = 5

    def __init__(self):
        pass

    @classmethod
    def is_available(cls) -> bool:
        return True

    async def call(
        self, parameters: dict, ctx: Any, **kwargs: Any
    ) -> List[Dict[str, Any]]:
        query = parameters.get("search_query")
        files = parameters.get("files")

        session = kwargs.get("session")
        user_id = kwargs.get("user_id")

        if not query or not files:
            return []

        file_ids = [file_id for _, file_id in files]
        retrieved_files = file_crud.get_files_by_ids(session, file_ids, user_id)
        if not retrieved_files:
            return []

        results = []
        for file in retrieved_files:
            results.append(
                {
                    "text": file.file_content,
                    "title": file.file_name,
                    "url": file.file_name,
                }
            )
        return results
