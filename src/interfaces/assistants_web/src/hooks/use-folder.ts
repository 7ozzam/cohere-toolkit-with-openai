import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FileSystemDirectoryHandle } from 'file-system-access';
import * as path from 'path';

import { ApiError, UserConversationFileAndFolderList, useCohereClient } from '@/cohere-client';
import { ACCEPTED_FILE_TYPES } from '@/constants';
import { useNotify, useSession } from '@/hooks';
import { useConversationStore, useFoldersStore, useParamsStore } from '@/stores';
import { getFileExtension, mapExtensionToMimeType } from '@/utils';
import { useRouter } from 'next/navigation';
import { useCallback } from 'react';

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
      files: { original_file_name: string; path: string; file: File }[];
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
  const { setAssociableItems } = useConversationStore();
  const { mutateAsync: deleteFolderFileAction } = useDeleteUploadedFolderFile();
  const {
    conversation: { id: selectedConversationId, name: conversationName },
    setConversation,
  } = useConversationStore();
  const { error } = useNotify();
  const queryClient = useQueryClient();
  const cohereClient = useCohereClient();
  const router = useRouter();
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
  ): Promise<{ original_file_name: string; path: string; file: File }[]> => {
    const files: { original_file_name: string; path: string; file: File }[] = [];

    // Define patterns to exclude
    const excludedPatterns = [
      /^\./,
      /\.git/,
      /\.obsidian/,
      /\.DS_Store$/,
      /\.env/,
      /\.vscode/,
      /\.idea/,
      /node_modules/,
      /\.config/,
      /thumbs\.db$/i,
      /desktop\.ini$/i,
      /\.gitignore$/,
      /\.gitattributes$/,
    ];

    // Helper function to check if path should be excluded
    const shouldExclude = (path: string): boolean => {
      return excludedPatterns.some((pattern) => pattern.test(path));
    };

    for await (const entry of directoryHandle.values()) {
      const fullPath = relativePath ? `${relativePath}/${entry.name}` : entry.name;

      // Skip if the path matches any excluded pattern
      if (shouldExclude(fullPath)) continue;

      if (entry.kind === 'file') {
        let directory = '.';
        if (fullPath.includes('/')) {
          directory = path.dirname(fullPath);
        }
        const file = await entry.getFile();
        const fileExtension = getFileExtension(file.name)!;

        if (file.type.length === 0 && fileExtension) {
          Object.defineProperty(file, 'type', {
            value: mapExtensionToMimeType(fileExtension),
          });
        }

        const isAcceptedExtension =
          file.type.length > 0 &&
          fileExtension &&
          ACCEPTED_FILE_TYPES.some((acceptedFile) => file.type === acceptedFile);

        if (isAcceptedExtension) {
          files.push({ path: directory, file, original_file_name: file.name });
        }
      } else if (entry.kind === 'directory') {
        const subFiles = await getAllFiles(entry, fullPath);
        files.push(...subFiles);
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

  // Function to associate an item to a conversation
  const handleAssociateItemToConversation = async (
    itemId: string,
    conversationId: string,
    agentId: string
  ) => {
    try {
      const response = await cohereClient.associateItemToConversation({
        itemId,
        conversationId,
        agentId,
      });
      setAssociableItems(response);

      const newConversationId = response[0].conversation_id;
      if (!conversationId || conversationId !== newConversationId) {
        // redirectToConversation(agentId, newConversationId);
      }
      
      
      setConversation({ id: newConversationId });
      
      await queryClient.invalidateQueries({ queryKey: ['conversations'] });
      await queryClient.invalidateQueries({ queryKey: ['associatableItems'] });
      await queryClient.invalidateQueries({ queryKey: ['listFiles'] });

      
    } catch (e) {
      console.error(e);
      throw e;
    }
  };

  // const redirectToConversation = useCallback((agentId?: string, conversationId?: string) => {
  //   if (agentId && conversationId) {
  //     router.push(`/a/${agentId}/c/${conversationId}`);
  //   }
    
  // }, [router]);
  const handleDeassociateItemToConversation = async (
    itemId: string,
    conversationId: string,
    agentId: string
  ) => {
    try {
      const response = await cohereClient.deassociateItemToConversation({
        itemId,
        conversationId,
        agentId,
      });
      setAssociableItems(response);
      if (!conversationId) {
        const newConversationId = response[0].conversation_id;
        setConversation({ id: newConversationId });
      }

      await queryClient.invalidateQueries({ queryKey: ['listFiles'] });
    } catch (e) {
      console.error(e);
      throw e;
    }
  };

  return {
    uploadingFolders,
    folderErrors,
    uploadFolder: handleUploadFolder,
    deleteFolderFile: handleDeleteFolderFile,
    clearFolderFiles,
    clearFolderErrors: handleClearFolderErrors,
    getAllFiles,
    associateItemToConversation: handleAssociateItemToConversation,
    deassociateItemToConversation: handleDeassociateItemToConversation,
  };
};
