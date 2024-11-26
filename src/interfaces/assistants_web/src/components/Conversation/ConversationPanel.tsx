'use client';

import { Transition } from '@headlessui/react';
import { useMemo, useState } from 'react';

import { Banner, Button, Icon, IconButton, Text, Tooltip } from '@/components/UI';
// Import the new FileItem component
import {
  useAgent,
  useBrandedColors,
  useChatRoutes,
  useConversationFileActions,
  useListConversationFiles,
  useSession,
} from '@/hooks';
import { useParamsStore, useSettingsStore } from '@/stores';

import { KnowledgeItem } from './FolderUpload/KnowledgeItemView';

export const ConversationPanel: React.FC = () => {
  const [isDeletingFile, setIsDeletingFile] = useState(false);
  const { agentId, conversationId } = useChatRoutes();
  const { data: files } = useListConversationFiles(conversationId);
  const { deleteFile } = useConversationFileActions();
  const { disabledAssistantKnowledge, setRightPanelOpen } = useSettingsStore();
  const {
    params: { fileIds },
    setParams,
  } = useParamsStore();

  const handleDeleteFile = async (fileId: string) => {
    if (isDeletingFile || !conversationId) return;

    setIsDeletingFile(true);
    try {
      await deleteFile({ conversationId, fileId });
      setParams({ fileIds: (fileIds ?? []).filter((id) => id !== fileId) });
    } finally {
      setIsDeletingFile(false);
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
    </aside>
  );
};
