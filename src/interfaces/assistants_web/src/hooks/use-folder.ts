import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useCohereClient } from '@/cohere-client';
import { useNotify, useSession } from '@/hooks';
import { useConversationStore, useFilesStore, useFoldersStore, useParamsStore } from '@/stores';
import {FileSystemDirectoryHandle} from 'file-system-access'
import { getFileExtension, mapExtensionToMimeType } from '@/utils';
import { ACCEPTED_FILE_TYPES } from '@/constants';

// Adjust this import based on your cohere client

// Query hook to list files in a folder
export const useListFolderFiles = (
  conversationId?: string,
  folderId?: string,
  options?: { enabled?: boolean }
) => {
  const cohereClient = useCohereClient();
  return useQuery({
    queryKey: ['listFolderFiles', conversationId, folderId],
    queryFn: async () => {
      if (!conversationId || !folderId) throw new Error('Conversation ID or Folder ID not found');
      try {
        return await cohereClient.listFolderFiles({ folderId }); // Adjusted to match CohereFolderHandling's method
      } catch (e) {
        console.error(e);
        throw e;
      }
    },
    enabled: !!conversationId && !!folderId,
    refetchOnWindowFocus: false,
    ...options,
  });
};

// Mutation hook to upload a single folder to a folder
export const useUploadFolderFiles = () => {
  const cohereClient = useCohereClient();
  return useMutation({
    mutationFn: ({
      folder,
      files,
      conversationId,
      agentId,
    }: {
      folder: FileSystemDirectoryHandle;
      files: { path: string; file: File }[];
      conversationId?: string;
      agentId: string;
    }) =>
      cohereClient.uploadFolderFiles({
        agentId: agentId,
        folderName: folder.name,
        files: files,
        conversationId: conversationId,
      }), // Uploading a single folder
  });
};

// Mutation hook to delete a file from a folder
export const useDeleteUploadedFolderFile = () => {
  const cohereClient = useCohereClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      conversationId,
      folderId,
      fileId,
    }: {
      conversationId: string;
      folderId: string;
      fileId: string;
    }) => cohereClient.deleteFolderFile({ folderId, fileId }), // Adjusted to match CohereFolderHandling's method
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['listFolderFiles'] });
    },
  });
};

// Hook to handle folder-related actions like upload, delete, and clear errors
export const useFolderActions = () => {
  const {
    folders: { uploadingFolders, folderErrors },
    addFolderFiles,
    deleteFolderFile,
    clearFolderFiles,
    updateFolderError,
    clearFolderErrors,
  } = useFoldersStore();

  const { userId } = useSession();
  const {
    params: { fileIds },
    setParams,
  } = useParamsStore();
  const { mutateAsync: uploadFolder } = useUploadFolderFiles();
  const { mutateAsync: deleteFolderFileAction } = useDeleteUploadedFolderFile();
  const { setConversation } = useConversationStore();
  const { error } = useNotify();
  const queryClient = useQueryClient();
  // const { addComposerFile } = useFilesStore();

  // Handle folder upload (single folder)
  const handleUploadFolder = async (
    folder: FileSystemDirectoryHandle,
    agentId: string,
    conversationId: string | undefined
  ) => {
    const files = await getAllFiles(folder);

    const newUploadingFolder = {
      id: new Date().valueOf().toString(),
      folder,
      error: '',
      progress: 0,
    };

    addFolderFiles([newUploadingFolder]);

    try {
      const uploadedFolder = await uploadFolder({
        folder,
        files,
        conversationId,
        agentId,
      });
      deleteFolderFile(newUploadingFolder.id);

      const newFileIds: string[] = fileIds ?? [];
      uploadedFolder.forEach((uploadedFile) => {
        newFileIds.push(uploadedFile.id);
        setParams({ fileIds: newFileIds });
        // addComposerFile({ ...uploadedFile });
      });

      if (!conversationId) {
        const newConversationId = uploadedFolder[0].conversation_id;
        setConversation({ id: newConversationId });
        
      }

      await queryClient.invalidateQueries({ queryKey: ['listFiles'] });

      return newFileIds;
    } catch (e: any) {
      updateFolderError(newUploadingFolder.id, e.message);
      throw e;
    }
  };

  const getAllFiles = async (
    directoryHandle: FileSystemDirectoryHandle,
    relativePath = ''
  ): Promise<{ path: string; file: File }[]> => {
    const files: { path: string; file: File }[] = [];

    for await (const entry of directoryHandle.values()) {
      const fullPath = relativePath ? `${relativePath}/${entry.name}` : entry.name;

      if (entry.kind === 'file') {
        const file = await entry.getFile();
        if (file.type.length === 0) {
          const fileExtension = getFileExtension(file.name)!;
          Object.defineProperty(file, 'type', {
            value: mapExtensionToMimeType(fileExtension),
          });
        }

        const isAcceptedExtension = ACCEPTED_FILE_TYPES.some(
          (acceptedFile) => file.type === acceptedFile
        );
        
        if (isAcceptedExtension) {
          files.push({ path: fullPath, file });
        }
      } else if (entry.kind === 'directory') {
        if (entry.name != '.get' && entry.name != '.obsedian') {
          const subFiles = await getAllFiles(entry, fullPath);
          files.push(...subFiles);
        }
      }
    }

    return files;
  };

  // Handle folder deletion
  const handleDeleteFolderFile = async ({
    folderId,
    fileId,
  }: {
    folderId: string;
    fileId: string;
  }) => {
    try {
      await deleteFolderFileAction({ folderId, fileId });
    } catch (e) {
      error('Unable to delete folder file');
    }
  };

  // Handle clearing folder errors
  const handleClearFolderErrors = () => {
    clearFolderErrors();
  };

  return {
    uploadingFolders,
    folderErrors,
    uploadFolder: handleUploadFolder,
    deleteFolderFile: handleDeleteFolderFile,
    clearFolderFiles,
    clearFolderErrors: handleClearFolderErrors,
    getAllFiles,
  };
};
