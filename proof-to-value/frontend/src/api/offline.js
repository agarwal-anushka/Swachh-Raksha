// Photo compression + a small offline queue (IndexedDB) for collectors on bad networks.
// The capture time is kept from the phone; the server still stamps its own time on arrival.

export async function compress(file, maxSide = 1600, quality = 0.8) {
  try {
    const bmp = await createImageBitmap(file)
    const scale = Math.min(1, maxSide / Math.max(bmp.width, bmp.height))
    const canvas = document.createElement('canvas')
    canvas.width = Math.round(bmp.width * scale)
    canvas.height = Math.round(bmp.height * scale)
    canvas.getContext('2d').drawImage(bmp, 0, 0, canvas.width, canvas.height)
    const blob = await new Promise((res) => canvas.toBlob(res, 'image/jpeg', quality))
    return blob && blob.size < file.size ? new File([blob], 'bin.jpg', { type: 'image/jpeg' }) : file
  } catch {
    return file // browser can't decode: send the original
  }
}

function db() {
  return new Promise((resolve, reject) => {
    const r = indexedDB.open('ptv-offline', 1)
    r.onupgradeneeded = () => r.result.createObjectStore('queue', { keyPath: 'id', autoIncrement: true })
    r.onsuccess = () => resolve(r.result)
    r.onerror = () => reject(r.error)
  })
}

const tx = async (mode, fn) => {
  const d = await db()
  return new Promise((resolve, reject) => {
    const t = d.transaction('queue', mode)
    const req = fn(t.objectStore('queue'))
    t.oncomplete = () => resolve(req?.result)
    t.onerror = () => reject(t.error)
  })
}

export const enqueue = (item) => tx('readwrite', (s) => s.add(item))
export const listQueue = () => tx('readonly', (s) => s.getAll())
export const removeFromQueue = (id) => tx('readwrite', (s) => s.delete(id))
