import { ApiClient, ApiClientError } from "./client";
import { jsonResponse, mockFetch } from "../test/testUtils";

describe("ApiClient", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("normalizes backend error envelopes", async () => {
    mockFetch(() =>
      jsonResponse(
        {
          error: {
            code: "PROVIDER_UNAVAILABLE",
            message: "Provider offline.",
            request_id: "abc",
            details: {}
          }
        },
        503,
        "abc"
      )
    );
    const client = new ApiClient("http://backend");
    await expect(client.get("/api/v1/models")).rejects.toMatchObject({
      code: "PROVIDER_UNAVAILABLE",
      requestId: "abc"
    });
  });

  it("reports backend offline", async () => {
    vi.spyOn(window, "fetch").mockRejectedValue(new TypeError("offline"));
    const client = new ApiClient("http://backend");
    await expect(client.get("/api/v1/health")).rejects.toBeInstanceOf(ApiClientError);
    await expect(client.get("/api/v1/health")).rejects.toMatchObject({ code: "BACKEND_OFFLINE" });
  });
});
