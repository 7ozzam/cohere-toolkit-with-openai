import { StateCreator } from 'zustand';

import { DEFAULT_CONVERSATION_NAME } from '@/constants';
import {
  ChatMessage,
  FulfilledMessage,
  LoadingMessage,
  TypingMessage,
  isLoadingMessage,
  isTypingMessage,
} from '@/types/message';

import { StoreState } from '..';
import { UserConversationFileAndFolderList } from '@/cohere-client';

const INITIAL_STATE: State = {
  id: undefined,
  name: DEFAULT_CONVERSATION_NAME,
  messages: [],
  associableItems: []
};

type State = {
  id?: string;
  name?: string;
  messages: ChatMessage[];
  associableItems: UserConversationFileAndFolderList[];
};

type Actions = {
  setConversation: (conversation: Partial<State>) => void;
  setPendingMessage: (message: FulfilledMessage | LoadingMessage | TypingMessage | null) => void;
  resetConversation: VoidFunction;
  setAssociableItems: (associableItems: UserConversationFileAndFolderList[]) => void;
};

export type ConversationStore = {
  conversation: State;
} & Actions;

export const createConversationSlice: StateCreator<StoreState, [], [], ConversationStore> = (
  set
) => ({
  setAssociableItems(associableItems: UserConversationFileAndFolderList[]) {
    set((state) => ({
      conversation: {
        ...state.conversation,
        associableItems: associableItems,
      },
    }));
  },
  setConversation(conversation) {
    set((state) => ({
      conversation: {
        ...state.conversation,
        ...conversation,
      },
    }));
  },
  resetConversation() {
    set(() => ({
      conversation: INITIAL_STATE,
    }));
  },
  setPendingMessage(message) {
    if (!message) {
      set((state) => ({
        conversation: {
          ...state.conversation,
          messages: state.conversation.messages.filter((m) => !isLoadingMessage(m)),
        },
      }));
      return;
    }

    set((state) => {
      const messages = state.conversation.messages;
      const newMessages: ChatMessage[] = [];
      let found = false;

      messages.forEach((m) => {
        if (isTypingMessage(m) || isLoadingMessage(m)) {
          newMessages.push({
            ...m,
            ...message,
          });
          found = true;
        } else {
          newMessages.push(m);
        }
      });

      return {
        conversation: {
          ...state.conversation,
          messages: found ? newMessages : messages.concat(message),
        },
      };
    });
  },
  conversation: INITIAL_STATE,
});
