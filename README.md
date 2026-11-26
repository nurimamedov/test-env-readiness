# Test Environment Readiness

A small Docker Compose experiment that separates **container launch** from
**ready for a test**. All services and data are fictional. The goal is to
measure end-to-end readiness, then see what removing an unnecessary
startup dependency buys you without cutting a check.

| Mode | Startup graph |
|---|---|
| Cold (serialized) | `alpha → beta → app`; a separate registry runs alongside. |
| Fast (parallel) | Alpha and beta start independently; the app still waits for both and for the registry. |

Alpha and beta represent independent preparation work with controlled delays.
The app listens before its readiness handler returns 200. It registers
with the independent registry after becoming ready. The host observer
requires three signals on the same pass:

1. A TCP connection to the app's published port.
2. HTTP 200 from the app's `/ready` handler.
3. The registry's `/services` response includes `app`.

## Run

Use Docker Engine with the Compose v2 plugin and Python 3 on your host.
Only the app and registry are published, on randomly allocated loopback
ports. Use the same already pulled image for both runs; neither measures
an image download.

```sh
docker compose pull
python3 benchmark.py
```

The command starts a fresh Compose project for each mode and writes elapsed
seconds as JSON only after actual runs. A failed readiness check or Docker
operation exits nonzero; cleanup removes the experiment's containers,
network and volumes. Timing starts immediately before `compose up` and
stops on the first passing sample after the host ports are known. The
interval includes Compose startup and health-check overhead. It excludes
pulling an image and tearing the project down. Compare repeated samples
if measuring on a noisy host.

| Startup mode | Observed seconds |
|---|---|
| Cold | Not measured on the authoring host; run the command above or see a successful CI artifact. |
| Fast | Not measured on the authoring host; run the command above or see a successful CI artifact. |

This intentionally models preparations with small HTTP services rather than
pulling a database, message broker or a coordination system. The controlled
delays illustrate ordering, not production performance.

## Checks

```sh
PYTHONPATH=. python3 -B -m unittest discover -s tests -v
docker compose -f compose.yml -f compose.cold.yml config --quiet
docker compose -f compose.yml -f compose.fast.yml config --quiet
```

The unit tests use loopback fixtures and do not require Docker. The CI
workflow runs both modes and saves `timings.json` from the runner's
observed measurements.
