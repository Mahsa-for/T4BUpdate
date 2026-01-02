// fs-save.ts
export async function saveWithPicker(
  blob: Blob,
  suggestedName: string,
  mime = blob.type || 'application/octet-stream'
) {
  // Feature-detect File System Access API
  const anyWin = window as any;
  const hasPicker = typeof anyWin.showSaveFilePicker === 'function';

  if (!hasPicker) {
    // Fallback to classic download
    classicDownload(blob, suggestedName);
    return;
  }

  // Ask user for a path/filename
  const handle: FileSystemFileHandle = await anyWin.showSaveFilePicker({
    suggestedName,
    types: [
      {
        description: mime,
        accept: { [mime || 'application/octet-stream']: [`.${suggestedName.split('.').pop()}`] }
      }
    ]
  });

  const writable = await handle.createWritable();
  await writable.write(blob);
  await writable.close();
}

export async function saveImageDataUrlWithPicker(dataUrl: string, suggestedName: string) {
  const res = await fetch(dataUrl);
  const blob = await res.blob();
  return saveWithPicker(blob, suggestedName, blob.type);
}

export function classicDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
