
export type ApiError = {
  status: number;
  message: string;
  details?: unknown;
};

function isJsonResponse(res: Response): boolean {
  const ct = res.headers.get("content-type") ?? "";
  return ct.includes("application/json");
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!res.ok) {
    let details: unknown = undefined;
    let message = res.statusText || "Request failed";
    try {
      if (isJsonResponse(res)) {
        details = await res.json();
        if (typeof (details as any)?.message === "string") message = (details as any).message;
      } else {
        const text = await res.text();
        if (text) message = text;
      }
    } catch {
      // ignore parse errors
    }
    const err: ApiError = { status: res.status, message, details };
    throw err;
  }

  if (res.status === 204) return undefined as unknown as T;
  if (isJsonResponse(res)) return (await res.json()) as T;
  // If backend returns text (rare), handle gracefully
  return (await res.text()) as unknown as T;
}
