import "./content.css";
import type { ExtensionMessage, SourceLocator } from "../shared/types";
import { clearHighlights, highlightCitations } from "./highlighter";

chrome.runtime.onMessage.addListener(
  (
    msg: ExtensionMessage,
    _sender: chrome.runtime.MessageSender,
    sendResponse: (response: unknown) => void
  ) => {
    switch (msg.type) {
      case "HIGHLIGHT_CITATIONS": {
        const locators = msg.payload as SourceLocator[];
        highlightCitations(locators);
        sendResponse({ type: "HIGHLIGHT_CITATIONS", payload: true });
        break;
      }
      case "CLEAR_HIGHLIGHTS": {
        clearHighlights();
        sendResponse({ type: "CLEAR_HIGHLIGHTS", payload: true });
        break;
      }
      default:
        break;
    }
    return true;
  }
);
