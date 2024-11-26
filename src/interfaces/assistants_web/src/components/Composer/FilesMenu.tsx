import { Popover, PopoverButton, PopoverPanel } from '@headlessui/react';
import { useRef } from 'react';

import { Icon, Text, Tooltip } from '@/components/UI';
import { ACCEPTED_FILE_TYPES } from '@/constants';
import { useBrandedColors, useChatRoutes } from '@/hooks';
import { cn, mapMimeTypeToExtension } from '@/utils';
import { showDirectoryPicker } from 'file-system-access';

type Props = {
  onUploadFile: (files: File[]) => void;
  onAttachFolder: (folder: FileSystemDirectoryHandle) => void;
};

export const FilesMenu: React.FC<Props> = ({ onUploadFile, onAttachFolder }) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { agentId } = useChatRoutes();
  const { bg, contrastFill } = useBrandedColors(agentId);

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onUploadFile([...(e.target.files ?? [])]);
  };

  const handleOpenFileExplorer = (callback: VoidFunction) => {
    if (!fileInputRef.current) return;
    fileInputRef.current.click();
    callback();
  };

  const handleAttachFolder = async (callback: VoidFunction) => {
    try {
      const directoryHandle = await showDirectoryPicker();
      onAttachFolder(directoryHandle);
      callback();
    } catch (error) {
      console.error('Error selecting folder:', error);
    }
  };

  return (
    <>
      <Popover className="relative">
        <PopoverButton
          as="button"
          className={({ open }) =>
            cn('flex items-center justify-center rounded p-1 outline-none dark:fill-marble-800', {
              [bg]: open,
            })
          }
        >
          {({ open }) => <Icon className={cn({ [contrastFill]: open })} name="paperclip" />}
        </PopoverButton>
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_FILE_TYPES.map(
            (fileType) => `.${mapMimeTypeToExtension(fileType)}`
          ).join(',')}
          className="hidden"
          multiple
          onChange={handleFileInputChange}
        />
        <PopoverPanel
          className="flex origin-top -translate-y-2 flex-col transition duration-200 ease-out data-[closed]:scale-95 data-[closed]:opacity-0"
          anchor="top start"
        >
          {({ close }) => (
            <div
              role="listbox"
              aria-multiselectable="true"
              className={cn(
                'z-tag-suggestions w-fit',
                'w-full rounded-md p-2 focus:outline-none',
                'bg-mushroom-950 dark:bg-volcanic-150'
              )}
            >
              <Tooltip
                label="Attach file (.PDF, .TXT, .MD, .JSON, .CSV, .TSV, .XSLS, .XLS, .DOCX, .PARQUET Max 20 MB)"
                size="sm"
                placement="top-start"
                hover
                hoverDelay={{ open: 250 }}
              >
                <button
                  onClick={() => handleOpenFileExplorer(close)}
                  className="flex w-full items-center rounded p-2"
                >
                  <Icon name="upload" />
                  <Text as="span" className="ml-2">
                    Upload files
                  </Text>
                </button>
              </Tooltip>

              <Tooltip
                label="Attach Folder / Directory / Obsidian Vault (Experimental)"
                size="sm"
                placement="top-start"
                hover
                hoverDelay={{ open: 250 }}
              >
                <button
                  onClick={() => handleAttachFolder(close)}
                  className="flex w-full items-center rounded p-2"
                >
                  <Icon name="upload" />
                  <Text as="span" className="ml-2">
                    Attach Folder (Experimental)
                  </Text>
                </button>
              </Tooltip>
            </div>
          )}
        </PopoverPanel>
      </Popover>
    </>
  );
};
