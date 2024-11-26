import React, { useEffect, useState } from 'react';
import { v4 as uuidv4 } from 'uuid';

import { ListConversationFile } from '@/cohere-client/generated/types.gen';
import { Button } from '@/components/UI/Button';
import { Modal } from '@/components/UI/Modal';
import { useFolderActions } from '@/hooks/use-folder';

import { KnowledgeItem } from './KnowledgeItemView';

type FolderPreviewModalProps = {
  isOpen: boolean;
  folderHandle: FileSystemDirectoryHandle | null;
  onCancel: VoidFunction;
  onConfirm: (folderData: ListConversationFile) => void;
};

export const FolderPreviewModal: React.FC<FolderPreviewModalProps> = ({
  isOpen,
  folderHandle,
  onCancel,
  onConfirm,
}) => {
  const { getAllFiles } = useFolderActions();
  const [folderView, setFolderView] = useState<ListConversationFile | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isEmptyFolder, setIsEmptyFolder] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false); // Added state for processing

  useEffect(() => {
    // Guard against running on every render
    if (!isOpen || !folderHandle) return;

    let isMounted = true;

    const fetchFolderData = async () => {
      setIsLoading(true); // Start loading

      const processedFolder = await processDirectoryHandle(folderHandle, getAllFiles);

      // Only update state if the component is still mounted
      if (isMounted) {
        setFolderView(processedFolder);
        setIsEmptyFolder(
          processedFolder && processedFolder.files && processedFolder.files.length === 0
        );
        setIsLoading(false); // Done loading
      }
    };

    fetchFolderData();

    return () => {
      isMounted = false; // Cleanup flag when component unmounts
    };
  }, [isOpen, folderHandle]); // Only re-run when isOpen or folderHandle changes

  const handleConfirm = async () => {
    if (folderView && !isEmptyFolder) {
      setIsProcessing(true); // Start processing

      try {
        // Call the onConfirm function and pass the folderView data
        await onConfirm(folderView);
      } catch (error) {
        // Handle errors if needed
        console.error('Error during folder confirmation:', error);
      } finally {
        setIsProcessing(false); // End processing
      }
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onCancel} title="Confirm Folder Upload">
      <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
        {isLoading ? (
          <p>Loading folder structure...</p>
        ) : isEmptyFolder ? (
          <p>This folder is empty. Please select a folder with files.</p>
        ) : (
          folderView && (
            <div className="flex flex-col gap-y-4">
              <KnowledgeItem
                key={folderView.id}
                file={folderView}
                isDeleting={false}
                onDelete={() => {}}
              />
            </div>
          )
        )}
      </div>
      <div className="flex justify-between">
        <Button label="Cancel" kind="secondary" onClick={onCancel} />
        <Button
          label={isProcessing ? 'Processing...' : 'Confirm'}
          onClick={handleConfirm}
          disabled={isProcessing || isEmptyFolder || !folderView}
          icon="arrow-right"
          kind="primary"
          iconPosition="end"
        />
      </div>
    </Modal>
  );
};

export const processDirectoryHandle = async (
  directoryHandle: FileSystemDirectoryHandle,
  getAllFiles: (handle: FileSystemDirectoryHandle) => Promise<{ path: string; file: File }[]>
): Promise<ListConversationFile> => {
  const folderId = uuidv4();
  const files: ListConversationFile[] = [];
  const conversationId = 'xxx'; // Replace with dynamic conversation ID if needed
  const userId = 'xxx'; // Replace with dynamic user ID if needed

  const allFiles = await getAllFiles(directoryHandle);

  allFiles.forEach(({ path, file }) => {
    files.push({
      id: uuidv4(),
      conversation_id: conversationId,
      file_size: file.size,
      user_id: userId,
      created_at: new Date(file.lastModified).toISOString(),
      updated_at: new Date(file.lastModified).toISOString(),
      file_name: path,
      folder_id: folderId,
      item_type: 'file',
    });
  });

  return {
    id: folderId,
    user_id: userId,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    conversation_id: conversationId,
    file_name: directoryHandle.name,
    file_size: files.reduce((size, file) => size + (file.file_size || 0), 0),
    item_type: 'folder',
    folder_id: folderId,
    files,
  };
};
