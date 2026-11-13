import { useEffect, useState } from 'react';

type JsonDocument = { readonly json: string };

/** Own one download resource per validated document, shared by Scout and Decision Lab. */
export function useJsonDownload(document: JsonDocument) {
  const [resource, setResource] = useState<{ document: JsonDocument; url: string | null } | null>(null);
  useEffect(() => {
    let url: string;
    try {
      // Do not stringify the parsed object, round values or project out unrendered fields.
      url = URL.createObjectURL(new Blob([document.json], { type: 'application/json;charset=utf-8' }));
    } catch {
      setResource({ document, url: null });
      return;
    }
    setResource({ document, url });
    // Reuse one URL while the link is accessible; not a premature revoke on click.
    return () => URL.revokeObjectURL(url);
  }, [document]);

  // A new document must never temporarily link to the previous document's bytes.
  return resource?.document === document ? resource : null;
}
