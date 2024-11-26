import { CohereClient } from '@/cohere-client';

export class CohereFolderHandling {
  private cohereClient: CohereClient;

  constructor(cohereClient: CohereClient) {
    this.cohereClient = cohereClient;
  }

  /**
   * Create a folder.
   * @param folderName The name of the folder to create.
   * @param conversationId The conversation ID for the folder.
   * @returns A promise resolving with the created folder details.
   */
  public async createFolder({
    folderName,
    conversationId,
    files,
  }: {
    folderName: string;
    conversationId: string;
    files: File[];
  }) {
    try {
      const response =
        await this.cohereClient.cohereService.default.uploadFolderV1ConversationsUploadFolderPost({
          formData: {
            files: files,
            folder_name: folderName,
            conversation_id: conversationId,
          },
        });
      return response;
    } catch (error) {
      console.error('Error creating folder:', error);
      throw new Error('Failed to create folder');
    }
  }

  /**
   * Delete a folder.
   * @param conversationId The conversation ID of the folder.
   * @param folderId The ID of the folder to delete.
   * @returns A promise resolving once the folder is deleted.
   */
  public async deleteFolder({
    conversationId,
    folderId,
  }: {
    conversationId: string;
    folderId: string;
  }) {
    try {
      const response =
        await this.cohereClient.cohereService.default.deleteFolderV1ConversationsConversationIdFoldersFolderIdDelete(
          {
            conversationId,
            folderId,
          }
        );
      return response;
    } catch (error) {
      console.error('Error deleting folder:', error);
      throw new Error('Failed to delete folder');
    }
  }

  /**
   * List all folders for a conversation.
   * @param conversationId The conversation ID to list folders for.
   * @returns A promise resolving with the list of folders.
   */
  public async listFolders({ conversationId }: { conversationId: string }) {
    try {
      const response =
        await this.cohereClient.cohereService.default.listFoldersV1ConversationsConversationIdFoldersGet(
          {
            conversationId,
          }
        );
      return response;
    } catch (error) {
      console.error('Error listing folders:', error);
      throw new Error('Failed to list folders');
    }
  }

  /**
   * Upload files to a folder.
   * @param folderId The folder ID where files will be uploaded.
   * @param files The files to upload.
   * @returns A promise resolving once the files are uploaded.
   */
  public async uploadFolderFiles({
    agentId,
    conversationId,
    folderName,
    files,
  }: {
    agentId: string;
    conversationId?: string;
    folderName: string;
    files: { original_file_name: string; path: string; file: Blob | File }[];
  }) {
    try {
      const formData = new FormData();
      const filesPayload: (File | Blob)[] = [];
      const pathsPayload: string[] = [];
      const originalFilesNamesPayload: string[] = [];

      // Sort files array by path before processing
      const sortedFiles = [...files].sort((a, b) => a.path.localeCompare(b.path));
      
      sortedFiles.forEach((file) => {
        formData.append('files', file.file);
        filesPayload.push(file.file);
        formData.append('paths', file.path);
        pathsPayload.push(file.path);
        formData.append('names', file.original_file_name);
        originalFilesNamesPayload.push(file.original_file_name);
      });

      const response =
        await this.cohereClient.cohereService.default.uploadFolderV1ConversationsUploadFolderPost({
          formData: {
            agent_id: agentId,
            conversation_id: conversationId,
            folder_name: folderName,
            files: filesPayload,
            paths: pathsPayload,
            names: originalFilesNamesPayload,
          },
        });
      return response;
    } catch (error) {
      console.error('Error uploading files to folder:', error);
      throw new Error('Failed to upload files');
    }
  }

  /**
   * List files in a folder.
   * @param folderId The folder ID to list files for.
   * @returns A promise resolving with the list of files in the folder.
   */
  public async listFolderFiles({ folderId }: { folderId: string }) {
    try {
      const response =
        await this.cohereClient.cohereService.default.listFolderFilesV1ConversationsConversationIdFoldersFolderIdFilesGet(
          {
            folderId,
          }
        );
      return response;
    } catch (error) {
      console.error('Error listing files in folder:', error);
      throw new Error('Failed to list files in folder');
    }
  }

  /**
   * Delete a file from a folder.
   * @param folderId The folder ID.
   * @param fileId The ID of the file to delete.
   * @returns A promise resolving once the file is deleted.
   */
  public async deleteFolderFile({ folderId, fileId }: { folderId: string; fileId: string }) {
    try {
      const response =
        await this.cohereClient.cohereService.default.deleteFolderFileV1ConversationsConversationIdFoldersFolderIdFilesFileIdDelete(
          { folderId, fileId }
        );
      return response;
    } catch (error) {
      console.error('Error deleting file from folder:', error);
      throw new Error('Failed to delete file from folder');
    }
  }
}
