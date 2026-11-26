/**
 * Minimal IndexedDB key-value storage for offline use (two stores: cached reads and the
 * check-in outbox). Falls back to memory when IndexedDB is unavailable (private mode, tests),
 * so the app still works; it just won't remember anything across reloads there.
 */
export type StoreName = "cache" | "outbox"

const DB_NAME = "atomic-streak"
const STORES: StoreName[] = ["cache", "outbox"]
const memory: Record<StoreName, Map<string, unknown>> = { cache: new Map(), outbox: new Map() }
let opening: Promise<IDBDatabase | null> | null = null

function open(): Promise<IDBDatabase | null> {
	if (!opening) {
		opening = new Promise((resolve) => {
			try {
				if (typeof indexedDB === "undefined") return resolve(null)
				const req = indexedDB.open(DB_NAME, 1)
				req.onupgradeneeded = () => {
					for (const s of STORES) if (!req.result.objectStoreNames.contains(s)) req.result.createObjectStore(s)
				}
				req.onsuccess = () => resolve(req.result)
				req.onerror = () => resolve(null)
				req.onblocked = () => resolve(null)
			} catch {
				resolve(null)
			}
		})
	}
	return opening
}

function run<T>(store: StoreName, mode: IDBTransactionMode, fn: (s: IDBObjectStore) => IDBRequest): Promise<T> {
	return open().then(
		(db) =>
			new Promise<T>((resolve, reject) => {
				if (!db) return reject(new Error("no-idb"))
				const req = fn(db.transaction(store, mode).objectStore(store))
				req.onsuccess = () => resolve(req.result as T)
				req.onerror = () => reject(req.error)
			}),
	)
}

export async function idbGet<T>(store: StoreName, key: string): Promise<T | undefined> {
	try {
		return await run<T | undefined>(store, "readonly", (s) => s.get(key))
	} catch {
		return memory[store].get(key) as T | undefined
	}
}

export async function idbSet(store: StoreName, key: string, value: unknown): Promise<void> {
	try {
		await run(store, "readwrite", (s) => s.put(value, key))
	} catch {
		memory[store].set(key, value)
	}
}

export async function idbDelete(store: StoreName, key: string): Promise<void> {
	memory[store].delete(key)
	try {
		await run(store, "readwrite", (s) => s.delete(key))
	} catch {
		/* memory only */
	}
}

export async function idbEntries<T>(store: StoreName): Promise<[string, T][]> {
	try {
		const [keys, values] = await Promise.all([
			run<IDBValidKey[]>(store, "readonly", (s) => s.getAllKeys()),
			run<T[]>(store, "readonly", (s) => s.getAll()),
		])
		return keys.map((k, i) => [String(k), values[i]!])
	} catch {
		return [...memory[store].entries()] as [string, T][]
	}
}
