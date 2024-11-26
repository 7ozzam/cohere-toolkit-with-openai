from enum import StrEnum
from typing import Any, Dict, List

import backend.crud.file as file_crud
from backend.tools.base import BaseTool
from backend.database_models import File


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
        _file_id = parameters.get("file_id") or parameters.get("id")
        _file_name = parameters.get("filename")
        _file_ids = parameters.get("file_ids")
        print("Called_file_ids: ", _file_ids)
        session = kwargs.get("session")
        user_id = kwargs.get("user_id")
        if not file and not _file_id and not _file_name and not _file_ids:
            return []
        elif file:
            if isinstance(file, str):
                file_id = file
            elif isinstance(file, dict):
                _, file_id = file
            elif isinstance(file, list):
                _, file_id = file
            retrieved_file = file_crud.get_file_by_name_or_id(session, file_id, user_id)    
        elif _file_name and not _file_id:
            retrieved_file = file_crud.get_file_by_name_or_id(session, _file_name, user_id)
        elif _file_id:
            retrieved_file = file_crud.get_file_by_name_or_id(session, _file_id, user_id)
        elif _file_ids:
            retrieved_files = file_crud.get_files_by_identifiers(session, _file_ids, user_id)
            print("retrieved_files_ont: ", retrieved_files)
            # Initialize a variable to hold the combined content
            combined_file_name = "Compination of Files "
            combined_content = ""

            # Iterate through the retrieved files
            for retrieved_file in retrieved_files:
                # Assuming each retrieved file has 'filename' and 'content' attributes
                filename = retrieved_file.file_name
                combined_file_name += f"{filename}, "
                file_content = retrieved_file.file_content
                
                # Append the content with the 'FILE START' and 'FILE END' markers
                combined_content += f"FILE START {filename}\n"
                combined_content += file_content + "\n"
                combined_content += f"FILE END {filename}\n\n"  # Adding extra newline for separation
            retrieved_file = File(file_name=combined_file_name,file_content=combined_content)
        
        
        
        if not retrieved_file:
            return ["It seems you're using wrong parameters or the file doesn't exist, please use the correct file_id from the conversation."]

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
        query = parameters.get("search_query") or parameters.get("query")
        
        
        def get_files(params):
            return (parameters.get("files") or 
                    [params.get("file")] or 
                    [])
        def get_file_ids(params):
            return (params.get("file_ids") or 
                    params.get("ids") or 
                    [params.get("file_id")] or 
                    [params.get("id")] or 
                    [])

        def get_file_names(params):
            return (params.get("file_names") or 
                    params.get("filenames") or 
                    [params.get("filename")] or 
                    [params.get("file_name")] or 
                    [])
        files = get_files(parameters)
        _file_ids = get_file_ids(parameters)
        _file_names = get_file_names(parameters)
        
        

        session = kwargs.get("session")
        user_id = kwargs.get("user_id")

        if not query or (not files and not _file_ids and not _file_names):
            return []

        if len(files):
            file_ids = [file_id for _, file_id in files]
            retrieved_files = file_crud.get_files_by_ids(session, file_ids, user_id)
        elif len(_file_ids):
            retrieved_files = file_crud.get_files_by_ids(session, _file_ids, user_id)
        elif len(_file_names):
            retrieved_files = file_crud.get_files_by_names(session, _file_names, user_id)
        
            
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
            
        if len(results) > 0:
            return results
        else:
            return ["It seems you're using wrong parameters or the file doesn't exist, please use the correct file_id from the conversation."]
