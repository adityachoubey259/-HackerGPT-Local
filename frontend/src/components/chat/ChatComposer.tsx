import { CornerDownLeft, Paperclip, Send, Square, Wrench } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "../ui/Button";
import { IconButton } from "../ui/IconButton";
import { Textarea } from "../ui/Form";
import { AgentSelector } from "./AgentSelector";
import { ModelSelector } from "./ModelSelector";

export function ChatComposer({
  onSubmit,
  onStop,
  streaming
}: {
  onSubmit: (content: string) => void;
  onStop: () => void;
  streaming: boolean;
}) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const canSend = value.trim().length > 0;

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) {
      return;
    }
    textarea.style.height = "0px";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 180).toString()}px`;
  }, [value]);

  return (
    <form
      className="border-t border-border-subtle bg-panel/80 p-3 backdrop-blur"
      onSubmit={(event) => {
        event.preventDefault();
        const content = value.trim();
        if (content) {
          onSubmit(content);
          setValue("");
        }
      }}
    >
      <div className="mx-auto max-w-4xl rounded-2xl border border-border-subtle bg-floating/90 p-2 shadow-popover">
        <Textarea
          aria-label="Message"
          placeholder="Message your selected local model"
          className="max-h-44 min-h-16 w-full resize-none border-transparent bg-transparent px-3 py-3 shadow-none hover:border-transparent focus:border-transparent focus:bg-transparent focus:ring-0"
          ref={textareaRef}
          rows={1}
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey && canSend && !streaming) {
              event.preventDefault();
              event.currentTarget.form?.requestSubmit();
            }
          }}
        />
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border-subtle px-1 pt-2">
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <IconButton label="Attach file placeholder" icon={<Paperclip size={16} />} disabled />
            <IconButton label="Tools placeholder" icon={<Wrench size={16} />} disabled />
            <ModelSelector />
            <AgentSelector />
          </div>
          <div className="flex items-center gap-2">
            <span className="hidden items-center gap-1 text-xs text-muted sm:flex">
              <kbd className="rounded border border-border-subtle bg-elevated px-1.5 py-0.5">Enter</kbd>
            </span>
            {streaming ? (
              <Button type="button" variant="danger" icon={<Square size={15} />} onClick={onStop}>
                Stop
              </Button>
            ) : (
              <Button
                type="submit"
                variant="primary"
                icon={<Send size={16} />}
                disabled={!canSend}
              >
                Send
                <CornerDownLeft aria-hidden size={13} className="hidden opacity-75 sm:block" />
              </Button>
            )}
          </div>
        </div>
      </div>
    </form>
  );
}
