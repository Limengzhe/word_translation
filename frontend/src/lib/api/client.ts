const BASE = '/api'

export async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  console.log(`[api] ${options?.method ?? 'GET'} ${path}`)
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const msg = body?.error?.message ?? `HTTP ${res.status}`
    console.error(`[api] ERROR ${res.status} ${path}`, body)
    const err = new Error(msg) as Error & { code?: string; status: number }
    err.code = body?.error?.code
    err.status = res.status
    throw err
  }
  const json = await res.json()
  console.log(`[api] OK ${path}`, json)
  return json as T
}

/** SSE helper — async generator over a fetch-based SSE stream */
export async function* fetchSSE(
  path: string,
  options?: RequestInit,
): AsyncGenerator<{ event: string; data: string }> {
  console.log(`[sse] connect ${path}`)
  const res = await fetch(`${BASE}${path}`, {
    headers: { Accept: 'text/event-stream', ...options?.headers },
    ...options,
  })
  if (!res.ok || !res.body) {
    const msg = `SSE fetch failed: ${res.status}`
    console.error(`[sse] ${msg}`)
    throw new Error(msg)
  }
  console.log(`[sse] stream opened ${path}`)

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''
  let currentEvent = 'message'
  let chunkCount = 0

  while (true) {
    const { done, value } = await reader.read()
    if (done) {
      console.log(`[sse] stream closed ${path} (${chunkCount} chunks)`)
      break
    }
    chunkCount++
    buf += decoder.decode(value, { stream: true })

    // SSE spec: messages are separated by blank lines (\n\n)
    // Split on double-newline to get complete messages first
    const messages = buf.split('\n\n')
    buf = messages.pop() ?? ''   // keep incomplete tail

    for (const msg of messages) {
      if (!msg.trim()) continue
      let evt = 'message'
      let dataLine = ''
      for (const line of msg.split('\n')) {
        if (line.startsWith('event:')) {
          evt = line.slice(6).trim()
        } else if (line.startsWith('data:')) {
          dataLine = line.slice(5).trim()
        }
      }
      if (dataLine) {
        console.log(`[sse] event="${evt}" data=${dataLine.slice(0, 120)}`)
        yield { event: evt, data: dataLine }
      }
    }
  }
}
