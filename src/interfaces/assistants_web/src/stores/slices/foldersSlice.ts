import { StateCreator } from 'zustand';

import { StoreState } from '..';

// Adjust this path based on where StoreState is defined

// Initial folders state
const INITIAL_STATE: State = {
  uploadingFolders: [],
  isFolderInputQueuedToFocus: false,
  folderErrors: [], // Store errors related to folders
};

// Folder types
export interface UploadingFolder {
  id: string;
  folder: FileSystemDirectoryHandle;
  error?: string;
  progress: number;
}

type State = {
  isFolderInputQueuedToFocus: boolean;
  uploadingFolders: UploadingFolder[];
  folderErrors: string[]; // Array of folder errors
};

type Actions = {
  queueFocusFolderInput: () => void;
  clearFocusFolderInput: () => void;
  addUploadingFolder: (folder: UploadingFolder) => void;
  addUploadingFolders: (folders: UploadingFolder[]) => void;
  addFolderFiles: (folders: UploadingFolder[]) => void;
  updateUploadingFolderError: (folder: UploadingFolder, error: string) => void;
  deleteUploadingFolder: (id: string) => void;
  clearUploadingFolderErrors: () => void;
  clearFolderFiles: () => void;
  clearFolderErrors: () => void; // Add `clearFolderErrors`
  updateFolderError: (folderId: string, error: string) => void; // Add `updateFolderError`
  deleteFolderFile: (id: string) => void; // Add `deleteFolderFile`
};

// FoldersStore type combines State and Actions
export type FoldersStore = {
  folders: State;
} & Actions;

// Slice function
export const createFoldersSlice: StateCreator<StoreState, [], [], FoldersStore> = (set) => ({
  folders: INITIAL_STATE,

  // Action implementations
  queueFocusFolderInput() {
    set((state) => ({
      folders: {
        ...state.folders,
        isFolderInputQueuedToFocus: true,
      },
    }));
  },
  clearFocusFolderInput() {
    set((state) => ({
      folders: {
        ...state.folders,
        isFolderInputQueuedToFocus: false,
      },
    }));
  },
  addUploadingFolder(folder) {
    set((state) => ({
      folders: {
        ...state.folders,
        uploadingFolders: [...state.folders.uploadingFolders, folder],
      },
    }));
  },
  addUploadingFolders(folders) {
    set((state) => ({
      folders: {
        ...state.folders,
        uploadingFolders: [...state.folders.uploadingFolders, ...folders],
      },
    }));
  },
  addFolderFiles(folders) {
    set((state) => ({
      folders: {
        ...state.folders,
        uploadingFolders: [...state.folders.uploadingFolders, ...folders],
      },
    }));
  },
  updateUploadingFolderError(folder, error) {
    set((state) => {
      const newUploadingFolders = [...state.folders.uploadingFolders];
      const uploadingFolder = newUploadingFolders.find((f) => f.id === folder.id);
      if (uploadingFolder) {
        uploadingFolder.error = error;
      }
      return {
        folders: {
          ...state.folders,
          uploadingFolders: newUploadingFolders,
        },
      };
    });
  },
  deleteUploadingFolder(id) {
    set((state) => ({
      folders: {
        ...state.folders,
        uploadingFolders: state.folders.uploadingFolders.filter((f) => f.id !== id),
      },
    }));
  },
  clearUploadingFolderErrors() {
    set((state) => {
      const newUploadingFolders = state.folders.uploadingFolders.filter(
        (f) => typeof f.error === 'undefined'
      );
      return {
        folders: {
          ...state.folders,
          uploadingFolders: newUploadingFolders,
        },
      };
    });
  },
  clearFolderFiles() {
    set((state) => ({
      folders: {
        ...state.folders,
        uploadingFolders: [], // Clears the uploading folders
      },
    }));
  },

  // Add `clearFolderErrors` to reset errors
  clearFolderErrors() {
    set((state) => ({
      folders: {
        ...state.folders,
        folderErrors: [], // Reset errors
      },
    }));
  },

  // Add `updateFolderError` to update folder error for a specific folder
  updateFolderError(folderId, error) {
    set((state) => {
      const newFolderErrors = [...state.folders.folderErrors];
      const existingErrorIndex = newFolderErrors.findIndex((err) => err.includes(folderId));

      if (existingErrorIndex !== -1) {
        newFolderErrors[existingErrorIndex] = `${folderId}: ${error}`;
      } else {
        newFolderErrors.push(`${folderId}: ${error}`);
      }

      return {
        folders: {
          ...state.folders,
          folderErrors: newFolderErrors,
        },
      };
    });
  },

  // Add `deleteFolderFile` to remove folder by ID
  deleteFolderFile(id) {
    set((state) => ({
      folders: {
        ...state.folders,
        uploadingFolders: state.folders.uploadingFolders.filter((folder) => folder.id !== id),
      },
    }));
  },
});
