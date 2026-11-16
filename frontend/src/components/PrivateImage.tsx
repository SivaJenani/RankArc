import { useEffect, useState, type ImgHTMLAttributes } from 'react';
import client from '../api/client';

export default function PrivateImage({ src, ...props }: ImgHTMLAttributes<HTMLImageElement>) {
  const [url, setUrl] = useState<string>();
  const [error, setError] = useState(false);
  useEffect(() => {
    let active = true;
    let objectUrl: string | undefined;
    setUrl(undefined); setError(false);
    if (!src) return;
    if (!src.startsWith('/api/papers/')) { setUrl(src); return; }
    client.get(src, { responseType: 'blob' }).then(({ data }) => {
      if (!active) return;
      objectUrl = URL.createObjectURL(data);
      setUrl(objectUrl);
    }).catch(() => { if (active) setError(true); });
    return () => { active = false; if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [src]);
  if (error) return <span role="alert" className="text-red-600 text-sm">Question image unavailable. Do not answer from an incomplete question; reload or upload the paper again.</span>;
  if (!url) return <span className="text-muted text-sm">Loading original question...</span>;
  return <img {...props} src={url} />;
}
