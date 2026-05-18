import type { ReactNode } from "react";

import type { StemBlock } from "../lib/api";

type TableCellContent = string | { text?: string | null; blocks?: StemBlock[] };

type RichContentProps = {
  blocks: StemBlock[];
  emptyLabel: string;
  className?: string;
};

function mergeInlineBlocks(blocks: StemBlock[]): StemBlock[] {
  const merged: StemBlock[] = [];

  for (const block of blocks) {
    const previous = merged[merged.length - 1];
    if (block.kind === "text" && block.source === "ocr" && previous?.kind === "text" && previous.source !== "ocr") {
      merged[merged.length - 1] = {
        ...previous,
        text: `${previous.text ?? ""}${block.text ?? ""}`,
      };
      continue;
    }

    merged.push(block);
  }

  return merged;
}

export function isLabelOnlyBlocks(blocks: StemBlock[], label: string): boolean {
  if (blocks.length !== 1) {
    return false;
  }

  const [block] = blocks;
  return block.kind === "text" && (block.text ?? "").trim() === label.trim();
}

function renderBlocks(blocks: StemBlock[]): ReactNode[] {
  const mergedBlocks = mergeInlineBlocks(blocks);
  const renderedBlocks: ReactNode[] = [];
  let inlineChildren: ReactNode[] = [];
  let paragraphIndex = 0;

  function flushInlineChildren() {
    if (inlineChildren.length === 0) {
      return;
    }

    renderedBlocks.push(
      <p key={`inline-${paragraphIndex++}`} className="inline-content-text">
        {inlineChildren}
      </p>,
    );
    inlineChildren = [];
  }

  for (const block of mergedBlocks) {
    if (block.kind === "table" && block.rows?.length) {
      flushInlineChildren();
      renderedBlocks.push(
        <div key={`${block.kind}-${paragraphIndex++}`} className="inline-content-table">
          <table>
            <tbody>
              {block.rows.map((row, rowIndex) => (
                <tr key={`${block.kind}-${paragraphIndex}-row-${rowIndex}`}>
                  {row.map((cell, cellIndex) => {
                    const content = cell as TableCellContent;
                    const cellNode = typeof content === "string" ? (
                      content
                    ) : content?.blocks?.length ? (
                      <div className="inline-content-table-cell-body">
                        {renderBlocks(content.blocks)}
                      </div>
                    ) : (
                      content?.text ?? ""
                    );

                    return cellIndex === 0 ? (
                      <th key={`${block.kind}-${paragraphIndex}-cell-${rowIndex}-${cellIndex}`} scope="row">
                        {cellNode}
                      </th>
                    ) : (
                      <td key={`${block.kind}-${paragraphIndex}-cell-${rowIndex}-${cellIndex}`}>{cellNode}</td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>,
      );
      continue;
    }

    if (block.kind === "image" && block.url) {
      flushInlineChildren();
      const imageName = block.original_file_name ?? block.file_name ?? `图片 ${paragraphIndex + 1}`;
      renderedBlocks.push(
        <figure key={`${block.kind}-${paragraphIndex++}`} className="inline-content-image">
          <img src={block.url} alt={imageName} loading="lazy" />
          <figcaption>{imageName}</figcaption>
        </figure>,
      );
      continue;
    }

    if (block.kind === "text") {
      const isFormula = block.source === "formula";
      inlineChildren.push(
        <span
          key={`${block.kind}-${paragraphIndex}-${inlineChildren.length}`}
          className={isFormula ? "inline-content-formula" : undefined}
        >
          {block.text ?? ""}
        </span>,
      );
    }
  }

  flushInlineChildren();
  return renderedBlocks;
}

export function RichContentBlocks({ blocks, emptyLabel, className }: RichContentProps) {
  if (blocks.length === 0) {
    return <div className={`empty-state ${className ?? ""}`.trim()}>{emptyLabel}</div>;
  }

  return <>{renderBlocks(blocks)}</>;
}
