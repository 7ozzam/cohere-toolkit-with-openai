'use client';

import React, { useState } from 'react';

import { ListConversationFile } from '@/cohere-client';
import { Button, Icon, IconButton, Tag, Text, Tooltip } from '@/components/UI';
import { cn } from '@/utils';

type KnowledgeItemProps = {
  file: ListConversationFile;
  filename?: string;
  actions?: React.ReactNode;
  actionsPosition?: 'start' | 'end';
  forceExpand?: boolean;
  isDeleting: boolean;
  onDelete: (fileId: string) => void;
};

export const KnowledgeItem: React.FC<KnowledgeItemProps> = ({
  file,
  filename,
  actions,
  actionsPosition = 'start',
  forceExpand,
  isDeleting,
  onDelete,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(true);

  return (
    <div className="group flex w-full flex-col gap-y-2 rounded-lg p-2 dark:hover:bg-volcanic-200">
      <div className="group flex w-full items-center justify-between gap-x-4">
        <div className="flex items-center gap-x-2 overflow-hidden ">
          <div className="flex-shrink-0">
            <Icon
              name={file.item_type === 'file' ? 'file' : 'folder'}
              kind="outline"
              className="fill-mushroom-300 dark:fill-marble-950"
            />
          </div>
          <Tooltip hover size="sm" label={filename || file.file_name}>
            <Text className="truncate">{filename || file.file_name}</Text>
          </Tooltip>
        </div>
        <div className="flex items-center gap-x-2">
          {actionsPosition === 'start' && actions}

          {file.files && file.files.length > 0 && !forceExpand && (
            <IconButton
              onClick={() => setIsCollapsed(!isCollapsed)}
              iconName="chevron-down"
              iconClassName={cn('transition-transform duration-300', {
                hidden: !setIsCollapsed,
                'rotate-180 transform': !isCollapsed,
              })}
              className="invisible group-hover:visible"
            />
          )}

          {actionsPosition === 'end' && actions}
        </div>
      </div>

      {/* {file.files && file.files.length > 0 && (
        <div
          className="flex cursor-pointer items-center"
          onClick={() => setIsCollapsed(!isCollapsed)}
        >
          <Text>{isCollapsed ? 'Show Files' : 'Hide Files'}</Text>
        </div>
      )} */}
      {file.files && file.files.length > 0 && (!isCollapsed || forceExpand) && (
        <div className="min flex max-h-64 w-full flex-col gap-2 overflow-y-auto pl-2">
          {file.files.map((childFile) => (
            <div
              key={childFile.id}
              className="flex items-center gap-x-3 overflow-hidden rounded-full bg-mushroom-600/10 p-2"
              style={{ minHeight: '50px' }}
            >
              <div className="flex-shrink-0">
                <Icon
                  name="file"
                  kind="outline"
                  className="fill-mushroom-300 dark:fill-marble-950"
                />
              </div>

              <div className="flex flex-col gap-x-4 truncate">
                {!!childFile.file_path?.length && (
                  <div className=" rounded-full">
                    <p className="text-caption text-marble-950/30">{childFile.file_path}</p>
                  </div>
                )}

                <Tooltip hover size="sm" label={childFile.file_name}>
                  <Text className="truncate">{childFile.file_name}</Text>
                </Tooltip>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
