import { create } from 'zustand';
import { shallow } from 'zustand/shallow';

import { Tool } from '@/cohere-client';
import { CitationsStore, createCitationsSlice } from '@/stores/slices/citationsSlice';
import { ConversationStore, createConversationSlice } from '@/stores/slices/conversationSlice';
import { FilesStore, createFilesSlice } from '@/stores/slices/filesSlice';
import { ParamStore, createParamsSlice } from '@/stores/slices/paramsSlice';

import { FoldersStore, createFoldersSlice } from './slices/foldersSlice';

export type ChatSettingsDefaultsValue = {
  preamble?: string;
  model?: string;
  temperature?: number;
  tools?: Tool[];
};

export type StoreState = CitationsStore &
  ConversationStore &
  FilesStore &
  ParamStore &
  FoldersStore;

const useStore = create<StoreState>((...a) => ({
  ...createCitationsSlice(...a),
  ...createConversationSlice(...a),
  ...createFilesSlice(...a),
  ...createParamsSlice(...a),
  ...createFoldersSlice(...a),
}));

export const useCitationsStore = () => {
  return useStore(
    (state) => ({
      citations: state.citations,
      addSearchResults: state.addSearchResults,
      addCitation: state.addCitation,
      resetCitations: state.resetCitations,
      saveOutputFiles: state.saveOutputFiles,
    }),
    shallow
  );
};

export const useConversationStore = () => {
  return useStore(
    (state) => ({
      conversation: state.conversation,
      setConversation: state.setConversation,
      setPendingMessage: state.setPendingMessage,
      resetConversation: state.resetConversation,
      setAssociableItems: state.setAssociableItems,
    }),
    shallow
  );
};

export const useFilesStore = () => {
  return useStore(
    (state) => ({
      files: state.files,
      queueFocusFileInput: state.queueFocusFileInput,
      clearFocusFileInput: state.clearFocusFileInput,
      addUploadingFile: state.addUploadingFile,
      addUploadingFiles: state.addUploadingFiles,
      deleteUploadingFile: state.deleteUploadingFile,
      addComposerFile: state.addComposerFile,
      deleteComposerFile: state.deleteComposerFile,
      clearComposerFiles: state.clearComposerFiles,
      clearUploadingErrors: state.clearUploadingErrors,
      updateUploadingFileError: state.updateUploadingFileError,
    }),
    shallow
  );
};

export const useFoldersStore = () => {
  return useStore(
    (state) => ({
      folders: state.folders,
      addFolderFiles: state.addFolderFiles,
      deleteFolderFile: state.deleteFolderFile,
      clearFolderFiles: state.clearFolderFiles,
      updateFolderError: state.updateFolderError,
      clearFolderErrors: state.clearFolderErrors,
    }),
    shallow
  );
};

export const useParamsStore = () => {
  return useStore(
    (state) => ({
      params: state.params,
      setParams: state.setParams,
      resetFileParams: state.resetFileParams,
    }),
    shallow
  );
};

export const useOutputFiles = () => {
  return useStore(
    (state) => ({
      outputFiles: state.citations.outputFiles,
    }),
    shallow
  );
};

export { useSettingsStore } from '@/stores/persistedStore';
