# gulasch-sites

Static versions of selected `gulasch.site` properties plus backend source snapshots without secrets.

## Included static sites

- `ocpncord.gulasch.site` from `sites/ocpncord`
- `pokemon.gulasch.site` from `sites/pokemon`
- `drive.gulasch.site` from `sites/drive`, with the global leaderboard temporarily disabled
- `aisaas.gulasch.site` from `sites/aisaas`, using embedded static AI responses instead of `/api/chat`
- `c3cock.gulasch.site` from `sites/c3cock`, using embedded/local editor state instead of `/api/state`
- `testwebseite.gulasch.site` from `sites/testwebseite`
- `testwebseite2.gulasch.site` from `sites/testwebseite2`
- `chat.gulasch.site` from `sites/chat`
- `angular.gulasch.site` from `sites/angular`

## Included backend source

- `backend/drive/server.js`
- `backend/aisaas/app.py`
- `backend/c3cock/server.js`
- `backend/conversation/conversation_app.py`
- `backend/conversation/run.sh`
- `backend/richard/richard_app.py`
- `backend/richard/status_server.py`
- `backend/richard/baresip_supervisor.py`
- `backend/richard/run.sh`

Secrets, `.env` files, SIP runtime state, recordings, caches, and persisted runtime data are intentionally excluded.

## NixOS module

Import `nixosModules.gulasch-sites` or `nixosModules.default` and enable:

```nix
{
  imports = [ inputs.gulasch-sites.nixosModules.default ];

  services.gulasch-sites.enable = true;
}
```

The module enables nginx and hosts the selected static sites directly from the Nix store. It does not host `conversation.gulasch.site` or `richard.gulasch.site`.
