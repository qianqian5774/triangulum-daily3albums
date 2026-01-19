# Command log

Commands run to investigate the cover image behavior and UI rendering:

- `rg -n "wikipedia|wikimedia" daily3albums -S`
- `rg -n "CoverArt|cover art|cover" -S`
- `rg -n "image_url|CoverArt" daily3albums -S`
- `rg -n "content-security|CSP|img-src|default-src" -S ui`
- `rg -n "serviceWorker|service worker|workbox" -S ui`
- `nl -ba daily3albums/cli.py | sed -n '230,310p'`
- `nl -ba daily3albums/cli.py | sed -n '500,540p'`
- `nl -ba ui/src/lib/types.ts | sed -n '1,140p'`
- `nl -ba ui/src/lib/data.ts`
- `nl -ba ui/src/routes/Today.tsx | sed -n '70,260p'`
- `nl -ba ui/src/routes/Today.tsx | sed -n '260,340p'`
- `nl -ba ui/src/routes/Archive.tsx | sed -n '130,170p'`
- `nl -ba ui/src/components/TreatmentViewerOverlay.tsx | sed -n '70,120p'`
- `nl -ba ui/public/data/today.json | sed -n '1,80p'`
- `rg -n "MusicBrainzAdapter|CoverArtArchiveAdapter|LastfmAdapter|ListenBrainzAdapter|DiscogsAdapter" -S`
- `rg -n "musicbrainz|lastfm|listenbrainz|discogs|coverart" daily3albums -S`
- `sed -n '1,220p' daily3albums/adapters.py`
- `sed -n '220,520p' daily3albums/adapters.py`
- `rg -n "RequestBroker|rate|throttle|sleep" daily3albums/request_broker.py -S`
- `sed -n '1,220p' daily3albums/request_broker.py`
- `ls logs`
- `grep "503" logs/musicbrainz_adapter.log`
- `curl -I "https://ws.audioscrobbler.com/2.0/?method=album.getinfo&api_key=<api_key>&artist=artist_name&album=album_name"`
- `curl -X GET "https://coverartarchive.org/release/<rg_mbid>/covers"`
