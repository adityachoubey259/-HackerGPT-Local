import type { ChatStreamEvent } from "../types/api";

interface RawSseEvent {
  event: string;
  data: string;
}

export async function* parseSseStream(stream: ReadableStream<Uint8Array>): AsyncGenerator<ChatStreamEvent> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    let result = await reader.read();
    while (!result.done) {
      buffer += decoder.decode(result.value, { stream: true });
      buffer = buffer.replace(/\r\n/g, "\n");
      let boundary = buffer.indexOf("\n\n");
      while (boundary !== -1) {
        const raw = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const event = parseRawEvent(raw);
        const normalized = event ? normalizeEvent(event) : null;
        if (normalized) {
          yield normalized;
        }
        boundary = buffer.indexOf("\n\n");
      }
      result = await reader.read();
    }
    buffer += decoder.decode();
    buffer = buffer.replace(/\r\n/g, "\n");
    if (buffer.trim()) {
      const event = parseRawEvent(buffer);
        const normalized = event ? normalizeEvent(event) : null;
        if (normalized) {
          yield normalized;
        }
    }
  } finally {
    reader.releaseLock();
  }
}

function parseRawEvent(raw: string): RawSseEvent | null {
  const lines = raw.replace(/\r\n/g, "\n").split("\n");
  let event = "message";
  const data: string[] = [];
  for (const line of lines) {
    if (!line || line.startsWith(":")) {
      continue;
    }
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      const value = line.slice(5);
      data.push(value.startsWith(" ") ? value.slice(1) : value);
    }
  }
  if (data.length === 0) {
    return null;
  }
  return { event, data: data.join("\n") };
}

function normalizeEvent(raw: RawSseEvent): ChatStreamEvent | null {
  const data = JSON.parse(raw.data) as unknown;
  switch (raw.event) {
    case "meta":
    case "generation.started":
      return { event: "meta", data } as ChatStreamEvent;
    case "delta":
    case "message.delta":
      return { event: "delta", data } as ChatStreamEvent;
    case "usage":
      return { event: raw.event, data } as ChatStreamEvent;
    case "context":
      return { event: "context", data } as ChatStreamEvent;
    case "metrics":
      return { event: "metrics", data } as ChatStreamEvent;
    case "error":
    case "generation.error":
      return { event: "error", data } as ChatStreamEvent;
    case "done":
    case "generation.completed":
      return { event: "done", data } as ChatStreamEvent;
    default:
      return null;
  }
}
