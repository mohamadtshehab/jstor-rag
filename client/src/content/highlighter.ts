import type { SourceLocator } from "../shared/types";

const HIGHLIGHT_CLASS = "jstor-rag-highlight";
const ACTIVE_CLASS = "jstor-rag-highlight--active";

export function highlightCitations(locators: SourceLocator[]): void {
  clearHighlights();

  const article = document.querySelector(
    "div.hlFld-Fulltext, div.hlFld-Abstract, article"
  );
  if (!article) return;

  for (const locator of locators) {
    highlightSnippet(article, locator);
  }
}

export function clearHighlights(): void {
  document.querySelectorAll(`.${HIGHLIGHT_CLASS}`).forEach((el) => {
    const parent = el.parentNode;
    if (parent) {
      parent.replaceChild(document.createTextNode(el.textContent || ""), el);
      parent.normalize();
    }
  });
}

export function scrollToHighlight(chunkId: string): void {
  document
    .querySelectorAll(`.${ACTIVE_CLASS}`)
    .forEach((el) => el.classList.remove(ACTIVE_CLASS));

  const target = document.querySelector(
    `.${HIGHLIGHT_CLASS}[data-chunk-id="${chunkId}"]`
  );
  if (target) {
    target.classList.add(ACTIVE_CLASS);
    target.scrollIntoView({ behavior: "smooth", block: "center" });
  }
}

function highlightSnippet(root: Element, locator: SourceLocator): void {
  const snippet = locator.contextSnippet.trim();
  if (!snippet) return;

  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let node: Text | null;

  while ((node = walker.nextNode() as Text | null)) {
    const idx = (node.textContent || "").indexOf(snippet);
    if (idx === -1) continue;

    const range = document.createRange();
    range.setStart(node, idx);
    range.setEnd(node, idx + snippet.length);

    const mark = document.createElement("mark");
    mark.className = HIGHLIGHT_CLASS;
    mark.dataset.chunkId = locator.chunkId;
    mark.dataset.section = locator.logicalSection;
    range.surroundContents(mark);
    break;
  }
}
