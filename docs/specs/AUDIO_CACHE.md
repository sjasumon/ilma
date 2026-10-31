# Saved service audio storage

The service worker stores recordings after they are listened to, with best-effort limits of 32 MiB and 40 clips. It evicts the least recently used clips when either limit is exceeded. Browser storage availability may impose a lower limit. This is a partial convenience cache, not a complete offline audio download.

Audio byte measurement, storage, usage metadata, manifest cleanup and eviction run in the fetch event's background lifetime. They never delay delivery of a successful network media response. Storage or quota failures do not fail playback. A complete byte-range representation may be stored as status 200; partial fragments are not stored as full recordings.

Activation measures and bounds legacy entries. Offline hits update usage and enforce the same limits in the background. A serial queue prevents simultaneous writes from exceeding the limits after maintenance finishes. Persistent metadata records byte counts and recent use; orphaned metadata is removed.

Current service, bank and optional account manifests remove obsolete recording URLs only after a successful network response with valid nonempty reviewed clip entries, filenames and SHA-256 hashes. A positive remaining-clip count is rejected even if the bundle claims completion. The optional account manifest is requested on activation only when account audio is already saved. Failed, empty, malformed or explicitly incomplete manifests retain saved clips. Activation manifest fetches have a four-second deadline including the response body. Manifest checks fetch JSON only, not recordings. Current source/text/audio integrity checks in the application remain authoritative for whether a recording may be played.
