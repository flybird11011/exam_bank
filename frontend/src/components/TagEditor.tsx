import { useState } from "react";

type TagItem = {
  id: string;
  name: string;
  tag_type: string;
  source: string;
  confidence: number | null;
};

type TagEditorProps = {
  tags?: TagItem[];
  onAdd: (payload: { tag_type: string; name: string }) => void;
  onRemove: (tag: TagItem) => void;
};

export function TagEditor({ tags = [], onAdd, onRemove }: TagEditorProps) {
  const [draft, setDraft] = useState("");

  function handleAdd() {
    const name = draft.trim();
    if (!name) {
      return;
    }
    onAdd({ tag_type: "knowledge_point", name });
    setDraft("");
  }

  return (
    <div className="tag-editor">
      <div className="tag-list">
        {tags.map((tag) => (
          <button key={tag.id} type="button" className="tag-pill" onClick={() => onRemove(tag)}>
            {tag.name}
          </button>
        ))}
      </div>

      <div className="tag-editor-row">
        <input
          aria-label="新标签"
          className="tag-input"
          placeholder="输入标签名"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
        />
        <button type="button" className="secondary-btn" onClick={handleAdd}>
          + 添加标签
        </button>
      </div>
    </div>
  );
}
