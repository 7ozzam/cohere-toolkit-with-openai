import { FileSystemDirectoryHandle } from 'file-system-access';
import React, { useEffect, useState } from 'react';
import { v4 as uuidv4 } from 'uuid';

import {
  ListConversationFile,
  UserConversationFileAndFolderList,
} from '@/cohere-client/generated/types.gen';
import { Icon, IconButton, ToggleCard } from '@/components/UI';
import { Button } from '@/components/UI/Button';
import { Modal } from '@/components/UI/Modal';
import { useFolderActions } from '@/hooks/use-folder';
import { useConversationStore, useFilesStore } from '@/stores';

import { KnowledgeItem } from '../FolderUpload/KnowledgeItemView';

type ExistingItemsViewModalProps = {
  isOpen: boolean;
  items: UserConversationFileAndFolderList[];
  // folderHandle: FileSystemDirectoryHandle | null;
  onCancel: VoidFunction;
  onConfirm: (id: string, is_associated?: boolean) => void;
};

export const ExistingItemsViewModal: React.FC<ExistingItemsViewModalProps> = ({
  isOpen,
  items,
  onCancel,
  onConfirm,
}) => {
  items = items.sort((a, b) =>
    a.is_associated === b.is_associated ? 0 : a.is_associated ? -1 : 1
  );

  const [isLoading, setIsLoading] = useState(false);
  const [isEmptyFolder, setIsEmptyFolder] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false); // Added state for processing

  // const {
  //   conversation: { associableItems },
  // } = useConversationStore();
  // useEffect(() => {
  //   // Guard against running on every render
  //   if (!isOpen) return;

  //   let isMounted = true;

  //   const fetchFolderData = async () => {
  //     setIsLoading(true); // Start loading

  //     const processedFolder = await processDirectoryHandle(folderHandle, getAllFiles);

  //     // Only update state if the component is still mounted
  //     if (isMounted) {
  //       setFolderView(processedFolder);
  //       setIsEmptyFolder(
  //         processedFolder && processedFolder.files && processedFolder.files.length === 0
  //       );
  //       setIsLoading(false); // Done loading
  //     }
  //   };

  //   fetchFolderData();

  //   return () => {
  //     isMounted = false; // Cleanup flag when component unmounts
  //   };
  // }, [isOpen, folderHandle]); // Only re-run when isOpen or folderHandle changes

  const handleItem = async (id: string, is_associated?: boolean) => {
    setIsProcessing(true); // Start processing
    await onConfirm(id, is_associated);
    setIsProcessing(false); // Start processing
  };

  return (
    <Modal isOpen={isOpen} onClose={onCancel} title="Confirm Folder Upload">
      <div
        className="rounded bg-marble-980 p-2 dark:bg-volcanic-100"
        style={{ maxHeight: '300px', overflowY: 'auto' }}
      >
        {isLoading ? (
          <p>Loading folder structure...</p>
        ) : isEmptyFolder ? (
          <p>This folder is empty. Please select a folder with files.</p>
        ) : (
          items &&
          items.map((item) => (
            <div className="flex flex-col gap-y-4" key={item.id}>
              <KnowledgeItem
                file={item}
                actions={
                  <IconButton
                    icon={
                      <Icon
                        name={item?.is_associated ? 'close' : 'add'}
                        className={
                          item?.is_associated
                            ? 'hover:fill-danger-600 fill-danger-500 dark:fill-danger-500'
                            : 'fill-coral hover:fill-coral-600 dark:fill-evolved-green-700'
                        }
                        size="sm"
                      />
                    }
                    onClick={() => {
                      handleItem(item.id, item.is_associated);
                    }}
                  ></IconButton>
                }
                actionsPosition="end"
                isDeleting={false}
                onDelete={() => {}}
              />
            </div>
          ))
        )}
      </div>
      {/* <div className="flex justify-between">
        <Button label="Cancel" kind="secondary" onClick={onCancel} />
        <Button
          label={isProcessing ? 'Processing...' : 'Confirm'}
          onClick={handleConfirm}
          disabled={isProcessing || isEmptyFolder || !folderView}
          icon="arrow-right"
          kind="primary"
          iconPosition="end"
        />
      </div> */}
    </Modal>
  );
};
