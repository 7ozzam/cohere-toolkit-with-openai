import React, { useRef, useState } from 'react';

import { AgentPublic, ManagedTool } from '@/cohere-client';
import { Composer } from '@/components/Composer';
import { Header } from '@/components/Conversation';
import { MessagingContainer, WelcomeGuideTooltip } from '@/components/MessagingContainer';
// Add the modal component
import {
  WelcomeGuideStep,
  useChat,
  useConversationFileActions,
  useWelcomeGuideState,
} from '@/hooks';
import { useFolderActions } from '@/hooks/use-folder';
import { useConversationStore } from '@/stores';
import { ConfigurableParams } from '@/stores/slices/paramsSlice';
import { ChatMessage } from '@/types/message';

import { FolderPreviewModal } from './FolderUpload/FolderPreviewModal';

type Props = {
  startOptionsEnabled?: boolean;
  agent?: AgentPublic;
  tools?: ManagedTool[];
  history?: ChatMessage[];
};

export const Conversation: React.FC<Props> = ({ agent, tools, startOptionsEnabled = false }) => {
  const { uploadFiles } = useConversationFileActions();
  const { uploadFolder, getAllFiles } = useFolderActions();

  const { welcomeGuideState, finishWelcomeGuide } = useWelcomeGuideState();
  const {
    conversation: { messages, id: conversationId },
  } = useConversationStore();

  const {
    userMessage,
    isStreaming,
    isStreamingToolEvents,
    streamingMessage,
    setUserMessage,
    handleSend: send,
    handleStop,
    handleRetry,
    handleRegenerate,
  } = useChat({
    onSend: () => {
      if (welcomeGuideState !== WelcomeGuideStep.DONE) {
        finishWelcomeGuide();
      }
    },
  });

  const chatWindowRef = useRef<HTMLDivElement>(null);

  // State for folder preview modal
  const [isFolderModalOpen, setIsFolderModalOpen] = useState(false);
  const [folderStructure, setFolderStructure] = useState<{ path: string; file: File }[]>([]);
  const [selectedFolder, setSelectedFolder] = useState<FileSystemDirectoryHandle | null>(null);

  // Handle folder attachment with preview
  const handleAttachFolder = async (folder: FileSystemDirectoryHandle) => {
    console.log(folder);
    console.log(conversationId);

    const files = await getAllFiles(folder); // Fetch folder structure
    setFolderStructure(files);
    setSelectedFolder(folder); // Save folder for upload
    setIsFolderModalOpen(true); // Open the modal
  };

  // Handle folder upload after confirmation
  const handleConfirmUpload = async () => {
    if (selectedFolder) {
      try {
        if (!agent?.id)
          throw new Error('You Should Choose an assistant or conversation to upload a folder');
        await uploadFolder(selectedFolder, agent?.id, conversationId); // Proceed with folder upload
        console.log('Folder uploaded successfully.');
      } catch (error) {
        console.error('Folder upload failed:', error);
      }
    }
    setIsFolderModalOpen(false); // Close the modal
  };

  const handleCancelUpload = () => {
    setIsFolderModalOpen(false); // Close the modal without uploading
  };

  const handleUploadFile = async (files: File[]) => {
    try {
      if (!agent?.id)
        throw new Error('You Should Choose an assistant or conversation to upload your files');
      await uploadFiles(agent.id, files, conversationId);
      console.log('Files uploaded successfully.');
    } catch (error) {
      console.error('Files upload failed:', error);
    }
  };

  const handleSend = (msg?: string, overrides?: Partial<ConfigurableParams>) => {
    send({ suggestedMessage: msg }, overrides);
  };

  return (
    <div className="flex h-full flex-grow">
      <div className="flex h-full w-full min-w-0 flex-col rounded-l-lg rounded-r-lg border border-marble-950 bg-marble-980 dark:border-volcanic-200 dark:bg-volcanic-100 lg:rounded-r-none">
        <Header agent={agent} />
        <div className="relative flex h-full w-full flex-col" ref={chatWindowRef}>
          <MessagingContainer
            conversationId={conversationId}
            startOptionsEnabled={startOptionsEnabled}
            isStreaming={isStreaming}
            isStreamingToolEvents={isStreamingToolEvents}
            onRetry={handleRetry}
            onRegenerate={handleRegenerate}
            messages={messages}
            streamingMessage={streamingMessage}
            agentId={agent?.id}
            composer={
              <>
                <WelcomeGuideTooltip step={3} className="absolute bottom-full mb-4" />
                <Composer
                  isStreaming={isStreaming}
                  value={userMessage}
                  streamingMessage={streamingMessage}
                  chatWindowRef={chatWindowRef}
                  agent={agent}
                  tools={tools}
                  onChange={(message) => setUserMessage(message)}
                  onSend={handleSend}
                  onStop={handleStop}
                  onUploadFile={handleUploadFile}
                  onAttachFolder={handleAttachFolder}
                  lastUserMessage={messages.findLast((m) => m.type === 'user')}
                />
              </>
            }
          />
        </div>
      </div>
      {/* Folder Preview Modal */}
      {isFolderModalOpen && (
        <FolderPreviewModal
          isOpen={isFolderModalOpen}
          folderHandle={selectedFolder}
          onCancel={handleCancelUpload}
          onConfirm={handleConfirmUpload}
        />
      )}
    </div>
  );
};
