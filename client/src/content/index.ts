import "./content.css";
import type { ExtensionMessage } from "../shared/types";

chrome.runtime.onMessage.addListener(
  (
    _msg: ExtensionMessage,
    _sender: chrome.runtime.MessageSender,
    _sendResponse: (response: unknown) => void
  ) => {
    return true;
  }
);
