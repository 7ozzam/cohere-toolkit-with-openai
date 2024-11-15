import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNotify, useSession } from '@/hooks';
import { useFoldersStore, useParamsStore } from '@/stores';
import { useCohereClient } from '@/cohere-client'; // Adjust this import based on your cohere client

// Query hook to list files in a folder
export const useListFolderFiles = (conversationId?: string, folderId?: string, options?: { enabled?: boolean }) => {
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
    mutationFn: ({ folder, conversationId }: { folder: FileSystemDirectoryHandle, conversationId?: string }) =>
      cohereClient.uploadFolderFiles({ folderId: folder.name, files: [], conversationId: conversationId }),  // Uploading a single folder
  });
};

// Mutation hook to delete a file from a folder
export const useDeleteUploadedFolderFile = () => {
  const cohereClient = useCohereClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ conversationId, folderId, fileId }: { conversationId: string; folderId: string; fileId: string }) =>
      cohereClient.deleteFolderFile({ folderId, fileId }), // Adjusted to match CohereFolderHandling's method
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
  const { mutateAsync: uploadFolder } = useUploadFolderFiles();
  const { mutateAsync: deleteFolderFileAction } = useDeleteUploadedFolderFile();
  const { error } = useNotify();
  

  // Handle folder upload (single folder)
  const handleUploadFolder = async (folder: FileSystemDirectoryHandle, conversationId: string | undefined) => {
    // Cleanup uploadingFolders with errors
    const uploadingFoldersWithErrors = uploadingFolders.filter((folder) => folder.error);
    uploadingFoldersWithErrors.forEach((folder) => deleteFolderFile(folder.id));

    if (!folder) return;

    const newUploadingFolder = {
      id: new Date().valueOf().toString(),
      folder,
      error: '',
      progress: 0,
    };

    // Add new folder to the uploading state
    addFolderFiles([newUploadingFolder]);

    try {
      console.log(conversationId);
      const uploadedFolder = await uploadFolder({ conversationId, folder: folder });

      // Remove the folder from uploading state after successful upload
      deleteFolderFile(newUploadingFolder.id);

      // You could update state or params with the new folder ID
      return uploadedFolder.id;
    } catch (e: any) {
      // Update state with errors
      updateFolderError(newUploadingFolder.id, e.message);
      error(`Folder upload failed ${e.message}`);
    }
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
  };
};
