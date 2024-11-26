'use client';

import { ListConversationFile } from '@/cohere-client';
import { Icon, IconButton, Text } from '@/components/UI';

type KnowledgeItemProps = {
  file: ListConversationFile;
  isDeleting: boolean;
  onDelete: (fileId: string) => void;
};

export const KnowledgeItem: React.FC<KnowledgeItemProps> = ({ file, isDeleting, onDelete }) => {
  return (
    <div className="group flex w-full flex-col gap-y-2 rounded-lg p-2 dark:hover:bg-volcanic-200">
      <div className="group flex w-full items-center justify-between gap-x-4">
        <div className="flex items-center gap-x-2 overflow-hidden">
          <Icon
            name={file.item_type === 'file' ? 'file' : 'folder'}
            kind="outline"
            className="fill-mushroom-300 dark:fill-marble-950"
          />
          <Text className="truncate">{file.file_name}</Text>
        </div>
        <IconButton
          onClick={() => onDelete(file.id)}
          disabled={isDeleting}
          iconName="close"
          className="invisible group-hover:visible"
        />
      </div>
      {file.files && file.files.length > 0 && (
        <div className="flex w-full flex-col gap-2 pl-2">
          {file.files.map((childFile) => (
            <div
              key={childFile.id}
              className="flex items-center gap-x-2 overflow-hidden rounded-full bg-mushroom-600/10 p-2"
            >
              <Icon name="file" kind="outline" className="fill-mushroom-300 dark:fill-marble-950" />
              <Text className="truncate">{childFile.file_name}</Text>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
