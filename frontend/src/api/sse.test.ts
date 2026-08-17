import { parseSseStream } from "./sse";

function streamFromChunks(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    }
  });
}

function streamFromByteChunks(chunks: Uint8Array[]): ReadableStream<Uint8Array> {
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(chunk);
      }
      controller.close();
    }
  });
}

async function collectEvents(stream: ReadableStream<Uint8Array>) {
  const events = [];
  for await (const event of parseSseStream(stream)) {
    events.push(event);
  }
  return events;
}

describe("parseSseStream", () => {
  it("parses events split across arbitrary chunks", async () => {
    const events = await collectEvents(
      streamFromChunks([
        "event: meta\ndata: {\"request_id\":\"req",
        "-1\",\"generation_id\":\"gen-1\",\"conversation_id\":\"conv-1\",",
        "\"user_message_id\":\"user-1\",\"assistant_message_id\":\"assistant-1\",",
        "\"provider\":\"fake\",\"model\":\"fake-model\",\"created_at\":\"2026-08-10T00:00:00Z\"}\n\n",
        "event: delta\r\ndata: {\"text\":\"Hel\"}\r\n\r\n",
        "event: done\ndata: {\"assistant_message_id\":\"assistant-1\",\"status\":\"completed\",\"finish_reason\":\"stop\"}\n\n"
      ])
    );

    expect(events).toHaveLength(3);
    expect(events[0]).toMatchObject({ event: "meta", data: { request_id: "req-1" } });
    expect(events[1]).toEqual({ event: "delta", data: { text: "Hel" } });
    expect(events[2]).toMatchObject({ event: "done", data: { status: "completed" } });
  });

  it("normalizes versioned event aliases", async () => {
    const events = await collectEvents(
      streamFromChunks([
        "event: generation.started\ndata: {\"request_id\":\"req-1\",\"generation_id\":\"gen-1\",",
        "\"conversation_id\":\"conv-1\",\"user_message_id\":\"user-1\",",
        "\"assistant_message_id\":\"assistant-1\",\"provider\":\"fake\",\"model\":\"fake-model\",",
        "\"agent_id\":null,\"created_at\":\"2026-08-10T00:00:00Z\"}\n\n",
        "event: message.delta\ndata: {\"text\":\"Hi\"}\n\n",
        "event: generation.completed\ndata: {\"assistant_message_id\":\"assistant-1\",\"status\":\"completed\",\"finish_reason\":\"stop\"}\n\n"
      ])
    );

    expect(events.map((event) => event.event)).toEqual(["meta", "delta", "done"]);
  });

  it("parses multiple events in one chunk and ignores unknown metadata events", async () => {
    const events = await collectEvents(
      streamFromChunks([
        "event: trace\ndata: {\"ignored\":true}\n\n",
        "event: delta\ndata: {\"text\":\"A\"}\n\nevent: delta\ndata: {\"text\":\"B\"}\n\n"
      ])
    );

    expect(events).toEqual([
      { event: "delta", data: { text: "A" } },
      { event: "delta", data: { text: "B" } }
    ]);
  });

  it("preserves source syntax and leading spaces inside JSON-encoded deltas", async () => {
    const code = [
      "```cpp",
      "#include <iostream>",
      "",
      "int main() {",
      "    std::cout << 2 * 3 << '\\n';",
      "}",
      "```"
    ].join("\n");
    const events = await collectEvents(
      streamFromChunks([`event: delta\ndata: ${JSON.stringify({ text: code })}\n\n`])
    );

    expect(events).toEqual([{ event: "delta", data: { text: code } }]);
  });

  it("preserves streamed code fences split across syntax boundaries", async () => {
    const chunks = [
      "event: delta\ndata: {\"text\":\"```cpp\\n#incl\"}\n\n",
      "event: delta\ndata: {\"text\":\"ude <iost\"}\n\n",
      "event: delta\ndata: {\"text\":\"ream>\\n\\nint main() {\\n\"}\n\n",
      "event: delta\ndata: {\"text\":\"    std::cout << 2 * 3;\\n}\\n\"}\n\n",
      "event: delta\ndata: {\"text\":\"```\"}\n\n"
    ];
    const events = await collectEvents(streamFromChunks(chunks));
    const assembled = events
      .filter((event) => event.event === "delta")
      .map((event) => ("text" in event.data ? event.data.text : ""))
      .join("");

    expect(assembled).toBe(
      "```cpp\n#include <iostream>\n\nint main() {\n    std::cout << 2 * 3;\n}\n```"
    );
    expect(assembled).not.toContain("\\#include");
    expect(assembled).not.toContain("\\<iostream");
    expect(assembled).not.toContain("2 \\* 3");
  });

  it("preserves leading spaces if a non-backend multiline SSE event is parsed", async () => {
    const events = await collectEvents(
      streamFromChunks(["event: delta\ndata:   {\"text\":\"kept\"}\n\n"])
    );

    expect(events).toEqual([{ event: "delta", data: { text: "kept" } }]);
  });

  it("preserves UTF-8 characters fragmented across byte chunks", async () => {
    const encoder = new TextEncoder();
    const bytes = encoder.encode("event: delta\ndata: {\"text\":\"héllo\"}\n\n");
    const events = await collectEvents(
      streamFromByteChunks([bytes.slice(0, 28), bytes.slice(28, 30), bytes.slice(30)])
    );

    expect(events).toEqual([{ event: "delta", data: { text: "héllo" } }]);
  });

  it("parses error and completion events", async () => {
    const events = await collectEvents(
      streamFromChunks([
        "event: generation.error\ndata: {\"code\":\"provider_empty_response\",",
        "\"message\":\"Provider completed without visible assistant content.\",",
        "\"request_id\":\"req-1\",\"generation_id\":\"gen-1\",\"retryable\":true}\n\n",
        "event: done\ndata: {\"assistant_message_id\":\"assistant-1\",\"status\":\"failed\",",
        "\"finish_reason\":\"provider_empty_response\"}\n\n"
      ])
    );

    expect(events).toMatchObject([
      { event: "error", data: { code: "provider_empty_response" } },
      { event: "done", data: { status: "failed" } }
    ]);
  });

  it("rejects malformed JSON for known events", async () => {
    await expect(collectEvents(streamFromChunks(["event: delta\ndata: {bad}\n\n"]))).rejects.toThrow(
      SyntaxError
    );
  });
});
