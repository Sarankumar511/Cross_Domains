# Deploying BridgeScout to SAP BTP Cloud Foundry

This deploys BridgeScout as a Multi-Target Application (MTA):

| Piece | What it is |
|---|---|
| `bridgescout-srv` | Python FastAPI backend (`bridgescout.api.app:app`), `python_buildpack` |
| `bridgescout-db` | **HDI deployer** (`hdb` / `nodejs_buildpack`) — creates the `PAPERS` / `DOMAINS` / `DELETED_PAPERS` tables |
| `bridgescout-hdi-container` | **HANA HDI container** (`hana` / `hdi-shared`) — stores the admin paper library (uploaded PDFs as BLOBs + metadata) |
| `bridgescoutui` | The React SPA, built and pushed to the **HTML5 Application Repository** |
| `bridgescout-uaa` | **XSUAA** instance (`application` plan) — auth + `BridgeScoutViewer` / `BridgeScoutAdmin` role collections |
| `bridgescout-destination` | `bridgescout-srv-api` destination so the SPA can call the backend through the approuter |

The admin paper library (papers an admin uploads through the **Upload file**
dialog: the PDF plus its metadata, custom domains, and seed/corpus deletions) is
kept in HANA so it survives Cloud Foundry restarts / restages. The backend picks
the store from `VCAP_SERVICES`: a bound `hana` container → HANA
(`bridgescout/storage/hana.py`); no binding → local JSON + PDF files under
`data/` (`bridgescout/storage/filesystem.py`), which is all that local dev and
`pytest` need.

**SAP Build Work Zone, standard edition** is a *subaccount subscription*, not a
space service — it is **not** in `mta.yaml`. Subscribe to it once in the cockpit
(step 5); its "HTML5 Apps" channel then auto-discovers the `bridgescout` app that
this MTA publishes to the HTML5 Application Repository.

The SPA is served by Work Zone's **managed approuter**; `/api/*` calls are routed
to the backend via the `bridgescout-srv-api` destination with the user's XSUAA
token forwarded (`HTML5.ForwardAuthToken`). The backend
([bridgescout/api/security.py](bridgescout/api/security.py)) validates that token
against the XSUAA JWKS and checks the `Analyze` scope.

Locally nothing changes: with no `VCAP_SERVICES` binding, auth is disabled and
`uvicorn bridgescout.api.app:app` + `pytest` run as before.

---

## 1. Prerequisites

**Tools**

```bash
npm install -g mbt                      # Cloud MTA Build Tool
cf install-plugin multiapps             # cf deploy / cf mta
# cf CLI v8+, Node 20+, Python 3.12, npm
```

**BTP subaccount entitlements** (add in the BTP cockpit → *Entitlements*):

- Cloud Foundry runtime (≥ 2 GB free — the backend asks for 1 GB, staging needs headroom)
- `xsuaa` — `application`
- `html5-apps-repo` — `app-host`, `app-runtime`
- `destination` — `lite`
- `hana` — `hdi-shared` (for the paper-library HDI container)
- **SAP Build Work Zone, standard edition** — add the entitlement, then
  **Instances and Subscriptions → Subscribe** (plan `standard`, or `free` on a
  trial account). This is a subscription, not a service in the MTA.

Enable Cloud Foundry on the subaccount and create a space.

**SAP HANA Cloud instance.** The `hdi-shared` service needs a *running* HANA
Cloud instance mapped to your space:

- BTP cockpit → your space → **SAP HANA Cloud** → *Create* → **SAP HANA Cloud,
  SAP HANA database**. Allow "all IP addresses" for the trial, set an admin
  password, create. First start takes ~10–15 min.
- Trial HANA Cloud instances **auto-stop every night** — restart from the same
  screen (or `Instances and Subscriptions`) before deploying / using the app.
- No separate binding step: `mta.yaml` creates `bridgescout-hdi-container` on
  `hana / hdi-shared` against this instance and binds it to `bridgescout-srv`
  and `bridgescout-db`.

### Assigning the admin role

`xs-security.json` defines two role collections. In the BTP cockpit →
**Security → Role Collections**, assign users:

- `BridgeScoutViewer` — run analyses, ask questions, upload a paper for one-off
  analysis. No paper library.
- `BridgeScoutAdmin` — everything above, plus the left-hand **paper library**
  (train/test corpus + uploads, foldered by domain), **Create domain** /
  **Upload file**, and viewing / downloading / deleting library papers.

---

## 2. Build

From the project root (`Cross_Domain/`):

```bash
mbt build
```

Produces `mta_archives/bridgescout_1.0.0.mtar`. The build runs
`npm ci && npm run build` in `frontend/` and bundles `frontend/dist/` (which now
includes `manifest.json` + `xs-app.json` from `frontend/public/`), and `npm ci`
in `db/` for the `@sap/hdi-deploy` deployer.

> `db/package.json` pins **both** `@sap/hdi-deploy` and the `hdb` HANA driver.
> `@sap/hdi-deploy` v5 needs a driver peer (`hdb` or `@sap/hana-client`) or the
> `bridgescout-db` task aborts with *"requires a peer of either
> '@sap/hana-client' or 'hdb'"*. `db/package-lock.json` is committed; if a build
> reuses a stale `db/node_modules`, run `rm -rf db/node_modules && (cd db && npm ci)`
> before `mbt build`.

---

## 3. Deploy

```bash
cf login -a https://api.cf.<region>.hana.ondemand.com     # e.g. eu10
cf target -o <org> -s <space>

cf deploy mta_archives/bridgescout_1.0.0.mtar
```

This creates the service instances (XSUAA, HTML5 repo, destination, **HANA HDI
container**), runs `bridgescout-db` once to deploy the `PAPERS` / `DOMAINS` /
`DELETED_PAPERS` tables into the container, pushes `bridgescout-srv`, and uploads
the SPA to the HTML5 repo.

> The HANA Cloud instance must be **running** before `cf deploy`, or
> `bridgescout-hdi-container` creation / `bridgescout-db` fails. Restart a
> stopped trial instance first.

Check:

```bash
cf apps
cf mta bridgescout
cf app bridgescout-srv | grep routes                       # note the backend URL
curl https://<bridgescout-srv-url>/health                  # {"status":"ok","auth":"xsuaa"}
cf app bridgescout-db                                       # should be "stopped" after a successful one-off deploy task
```

If `bridgescout-srv` logs `HANA store unavailable (...); falling back to
filesystem`, the container binding or the tables are missing — check
`cf services`, that `bridgescout-db` finished, and that HANA Cloud is running.
Uploads still work in that state but do **not** persist across a restart.

> First backend start downloads the `all-MiniLM-L6-v2` model (~80 MB) from
> Hugging Face and builds the FAISS index in memory. If it crashes on memory,
> raise `memory: 1024M` → `2048M` for `bridgescout-srv` in `mta.yaml` and redeploy.

---

## 4. Create the backend destination

The MTA does **not** create the SPA-to-backend destination (the backend URL isn't
known until it's deployed, and `com.sap.application.content` can only make
service-key destinations). Create it once, by hand:

BTP cockpit → your subaccount → **Connectivity → Destinations → New Destination**:

| Field | Value |
|---|---|
| Name | `bridgescout-srv-api` |
| Type | `HTTP` |
| URL | `https://<bridgescout-srv-url>` (from step 3) |
| Proxy Type | `Internet` |
| Authentication | `NoAuthentication` |

Add these **Additional Properties**:

| Property | Value |
|---|---|
| `HTML5.DynamicDestination` | `true` |
| `HTML5.ForwardAuthToken` | `true` |

This name matches the `destination` in `frontend/public/xs-app.json`.

**Or** add it to the `bridgescout-destination` service instance from the CLI
(fill in your backend URL from step 3):

```bash
cf update-service bridgescout-destination -c '{
  "init_data": { "instance": {
    "existing_destinations_policy": "update",
    "destinations": [{
      "Name": "bridgescout-srv-api",
      "Type": "HTTP",
      "URL": "https://<bridgescout-srv-url>",
      "ProxyType": "Internet",
      "Authentication": "NoAuthentication",
      "HTML5.DynamicDestination": true,
      "HTML5.ForwardAuthToken": true
    }]
  }}
}'
```

---

## 5. Assign the role

In the BTP cockpit → **Security → Role Collections → `BridgeScoutViewer`** →
add your user (and anyone else who should use the app). Without this the token
won't carry the `Analyze` scope and the backend returns `403`.

---

## 6. Surface it in SAP Build Work Zone, standard edition

In the BTP cockpit, open **SAP Build Work Zone, standard edition** (Instances and
Subscriptions → the `SAPLaunchpad` app / "Site Manager").

1. **Channel Manager** → the *HTML5 Apps* content channel → **Update content**.
   The `bridgescout` HTML5 app now appears as available content.
2. **Content Manager** → **New** → **Group** → add the **BridgeScout** app tile.
3. **Content Manager** → open **Everyone** (or a dedicated role) → add the
   BridgeScout app so it's visible to assigned users.
4. **Site Directory** → create a site (or edit the existing one) → assign the
   group. **Publish**.
5. Open the site URL → the **BridgeScout** tile launches the React app inside the
   Work Zone shell; `/api/*` is authenticated automatically.

The app's launch target is the intent **`BridgeScout-display`** (from
`frontend/public/manifest.json` → `sap.app.crossNavigation.inbounds`).

---

## 7. Updating

```bash
mbt build && cf deploy mta_archives/bridgescout_1.0.0.mtar
```

Bump `version:` in `mta.yaml` and `applicationVersion` in
`frontend/public/manifest.json` for a clean HTML5-repo version. Re-run
*Channel Manager → Update content* in Work Zone to pick up UI changes.

---

## 8. Undeploy

```bash
cf undeploy bridgescout --delete-services --delete-service-keys
```

Then delete the manually-created `bridgescout-srv-api` destination.

---

## Files added for BTP

| File | Purpose |
|---|---|
| `mta.yaml` | MTA descriptor (modules + services) |
| `xs-security.json` | XSUAA scopes / role template / role collection |
| `Procfile`, `runtime.txt` | Python buildpack start command + version |
| `.cfignore` | Keeps `dataset/`, `frontend/`, tests out of the backend push |
| `bridgescout/api/security.py` | XSUAA JWT validation (no-op locally) |
| `frontend/public/xs-app.json` | Approuter routes: `/api/*` → destination, rest → HTML5 repo |
| `frontend/public/manifest.json` | HTML5 app descriptor for Work Zone (tile + launch intent) |

## Local development

`requirements.txt` is the slim Cloud Foundry set (no `sentence-transformers` /
torch). For full-quality local runs and the test suite:

```bash
pip install -r requirements-dev.txt        # adds sentence-transformers + pytest
uvicorn bridgescout.api.app:app --reload --port 8000
cd frontend && npm run dev                 # Vite proxies /api -> :8000
```

On Cloud Foundry (no `sentence-transformers`), `embedder.py` falls back to a
scikit-learn `HashingVectorizer` — lower-quality embeddings, but the pipeline
runs with a ~60 MB droplet instead of ~2 GB.
