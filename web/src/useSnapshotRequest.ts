import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';

export const REQUEST_TIMEOUT_MS = 15_000;
type State<Document, Field> = { kind: 'idle' | 'loading' }
  | { kind: 'error'; message: string; fields?: readonly Field[] }
  | { kind: 'ready'; document: Document };

/** One explicit request per mode. Abort is advisory; generation checks reject late results. */
export function useSnapshotRequest<Document, Field extends string>(enabled: boolean) {
  const [state, setState] = useState<State<Document, Field>>({ kind: 'idle' });
  const sequence = useRef(0);
  const pending = useRef<{ controller: AbortController; timer: ReturnType<typeof setTimeout> } | null>(null);
  const cancel = useCallback(() => {
    sequence.current += 1;
    if (pending.current) {
      clearTimeout(pending.current.timer);
      pending.current.controller.abort();
      pending.current = null;
    }
  }, []);
  useEffect(() => cancel, [cancel]);
  useLayoutEffect(() => {
    if (!enabled) {
      cancel();
      // Keep completed results and drafts when changing modes, but never keep a spinner.
      setState(previous => previous.kind === 'loading' ? { kind: 'idle' } : previous);
    }
  }, [enabled, cancel]);

  function invalidate() { cancel(); setState({ kind: 'idle' }); }
  function failValidation(message: string, fields?: readonly Field[]) {
    cancel(); setState({ kind: 'error', message, fields });
  }
  async function load(fetchDocument: (signal: AbortSignal) => Promise<Document>) {
    cancel();
    if (!enabled) return;
    const request = sequence.current;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      if (sequence.current !== request) return;
      cancel();
      // Finish the UI deadline even if a transport ignores AbortSignal.
      setState({ kind: 'error', message: 'The request timed out after 15 seconds. Check the local API before retrying; server work may still be running.' });
    }, REQUEST_TIMEOUT_MS);
    pending.current = { controller, timer };
    setState({ kind: 'loading' });
    try {
      const document = await fetchDocument(controller.signal);
      if (sequence.current === request && !controller.signal.aborted) setState({ kind: 'ready', document });
    } catch (error) {
      if (sequence.current === request) setState({ kind: 'error', message:
        error instanceof TypeError ? 'Cannot reach the local API. Start the configured API on 127.0.0.1:8000 and retry.'
        : error instanceof SyntaxError ? 'The API returned unreadable JSON. No measurements were displayed.'
        : error instanceof Error ? error.message : 'The evidence could not be loaded. Please retry.' });
    } finally {
      clearTimeout(timer);
      if (sequence.current === request) pending.current = null;
    }
  }
  return { state, invalidate, failValidation, load };
}
