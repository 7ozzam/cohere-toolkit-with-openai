'use client';

import { Transition } from '@headlessui/react';
import { useEffect, useMemo, useState } from 'react';

import { UserConversationFileAndFolderList } from '@/cohere-client';
import { Banner, Button, Icon, IconButton, Text, Tooltip } from '@/components/UI';
// Import the new FileItem component
import {
  useAgent,
  useBrandedColors,
  useChatRoutes,
  useConversationFileActions,
  useGetConversationAssociatableItems,
  useListConversationFiles,
  useSession,
} from '@/hooks';
import { useFolderActions } from '@/hooks/use-folder';
import { useFilesStore, useParamsStore, useSettingsStore } from '@/stores';

import { ExistingItemsViewModal } from './ExistingItemsView/ExistingItemsViewModal';
import { KnowledgeItem } from './FolderUpload/KnowledgeItemView';

export const ConversationPanel: React.FC = () => {
  const [isDeletingFile, setIsDeletingFile] = useState(false);
  const [isExistingItemsModalOpen, setIsExistingItemsModalOpen] = useState(false);
  const {
    setAssociableItems,
    files: { associableItems },
  } = useFilesStore();
  // const [associatableItems, setAssociatableItems] = useState(Array<UserConversationFileAndFolderList>(0));
  const { agentId, conversationId } = useChatRoutes();
  const { data: files } = useListConversationFiles(conversationId);
  const { deleteFile } = useConversationFileActions();
  const { disabledAssistantKnowledge, setRightPanelOpen } = useSettingsStore();
  const {
    params: { fileIds },
    setParams,
  } = useParamsStore();

  const { associateItemToConversation, deassociateItemToConversation } = useFolderActions();

  // Handle folder upload after confirmation
  const handleConfirmUpload = async () => {
    // if (selectedFolder) {
    //   try {
    //     if (!agent?.id)
    //       throw new Error('You Should Choose an assistant or conversation to upload a folder');
    //     await uploadFolder(selectedFolder, agent?.id, conversationId); // Proceed with folder upload
    //     console.log('Folder uploaded successfully.');
    //   } catch (error) {
    //     console.error('Folder upload failed:', error);
    //   }
    // }
    setIsExistingItemsModalOpen(false); // Close the modal
  };

  const handleCancelUpload = () => {
    setIsExistingItemsModalOpen(false); // Close the modal without uploading
  };

  const handleDeleteFile = async (fileId: string) => {
    handleItemAssociation(fileId, true);
  };

  const handleItemAssociation = async (id: string, is_associated?: boolean) => {
    if (agentId) {
      try {
        // Call the onConfirm function and pass the folderView data
        if (!is_associated) {
          await associateItemToConversation(id, conversationId || 'all', agentId);
        } else {
          await deassociateItemToConversation(id, conversationId || 'all', agentId);
        }
      } catch (error) {
        // Handle errors if needed
        console.error('Error during folder confirmation:', error);
      }
    }
  };

  return (
    <aside className="space-y-5 py-4">
      <header className="flex items-center gap-2">
        <IconButton
          onClick={() => setRightPanelOpen(false)}
          iconName="arrow-right"
          className="flex h-auto flex-shrink-0 self-center lg:hidden"
        />
        <Text styleAs="p-sm" className="font-medium uppercase">
          Knowledge Management
        </Text>
      </header>
      <div className="flex flex-col gap-y-10">
        <section className="relative flex flex-col gap-y-6">
          <div className="flex gap-x-2">
            <Button
              onClick={() => setIsExistingItemsModalOpen(true)}
              className="flex-grow"
              icon="add"
              kind="primary"
            >
              Asscoiate Existing Item
            </Button>
          </div>
        </section>
        <section className="relative flex flex-col gap-y-6">
          <div className="flex gap-x-2">
            <Text styleAs="label" className="font-medium">
              My files
            </Text>
            <Tooltip
              hover
              size="sm"
              placement="top-start"
              label="To use uploaded files, at least 1 File Upload tool must be enabled"
            />
          </div>
          {files && files.length > 0 && (
            <div className="flex flex-col gap-y-4">
              {files.map((file) => (
                <KnowledgeItem
                  key={file.id}
                  file={file}
                  actions={
                    <div className="flex items-center gap-x-2">
                      <IconButton
                        onClick={() => handleDeleteFile(file.id)}
                        disabled={isDeletingFile}
                        iconName="close"
                        iconClassName="transition-transform duration-300"
                        className="invisible group-hover:visible"
                      />
                    </div>
                  }
                  isDeleting={isDeletingFile}
                  onDelete={handleDeleteFile}
                />
              ))}
            </div>
          )}
          {/* <Text styleAs="caption" className="text-mushroom-300 dark:text-marble-800">
            These files will only be accessible to you and won’t impact others.
          </Text> */}
        </section>
      </div>
      {/* Folder Preview Modal */}
      {isExistingItemsModalOpen && (
        <ExistingItemsViewModal
          isOpen={isExistingItemsModalOpen}
          items={associableItems}
          onCancel={handleCancelUpload}
          onConfirm={handleItemAssociation}
        />
      )}
    </aside>
  );
};
