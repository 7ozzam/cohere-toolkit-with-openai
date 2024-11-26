'use client';

import { ListConversationFile } from '@/cohere-client';
import { Icon, IconButton, Tag, Text } from '@/components/UI';

type KnowledgeItemProps = {
  file: ListConversationFile;
  filename?: string;
  isDeleting: boolean;
  onDelete: (fileId: string) => void;
};

export const KnowledgeItem: React.FC<KnowledgeItemProps> = ({
  file,
  filename,
  isDeleting,
  onDelete,
}) => {
  return (
    <div className="group flex w-full flex-col gap-y-2 rounded-lg p-2 dark:hover:bg-volcanic-200">
      <div className="group flex w-full items-center justify-between gap-x-4">
        <div className="flex items-center gap-x-2 overflow-hidden">
          <Icon
            name={file.item_type === 'file' ? 'file' : 'folder'}
            kind="outline"
            className="fill-mushroom-300 dark:fill-marble-950"
          />

          <Text className="truncate">{filename || file.file_name}</Text>
        </div>
        <IconButton
          onClick={() => onDelete(file.id)}
          disabled={isDeleting}
          iconName="close"
          className="invisible group-hover:visible"
        />
      </div>
      {file.files && file.files.length > 0 && (
        <div className="min flex max-h-64 w-full flex-col gap-2 overflow-y-auto pl-2">
          {file.files.map((childFile) => (
            <div
              key={childFile.id}
              className="flex items-center gap-x-3 overflow-hidden rounded-full bg-mushroom-600/10 p-2"
              style={{ minHeight: '50px' }}
            >
              <Icon name="file" kind="outline" className="fill-mushroom-300 dark:fill-marble-950" />

              <div className="flex flex-col gap-x-4">
                {!!childFile.file_path?.length && (
                  <div className=" rounded-full">
                    <p className='text-marble-950/30 text-caption'>{childFile.file_path}</p>
                  </div>
                )}
                <Text className="truncate">{childFile.file_name}</Text>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
