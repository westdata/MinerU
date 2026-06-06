from contextlib import contextmanager

from fastapi.testclient import TestClient

from mineru.cli import fast_api, router


def _authorized_headers(api_key: str, *, scheme: str = "bearer") -> dict[str, str]:
    if scheme == "bearer":
        return {"Authorization": f"Bearer {api_key}"}
    if scheme == "x-api-key":
        return {"X-API-Key": api_key}
    raise ValueError(f"Unsupported auth scheme: {scheme}")


def test_fast_api_health_allows_request_when_api_key_not_configured():
    with _fast_api_test_client(api_key=None) as client:
        response = client.get("/health")

    assert response.status_code in {200, 503}


def test_fast_api_health_rejects_missing_api_key_when_configured():
    with _fast_api_test_client(api_key="secret-key") as client:
        response = client.get("/health")

    assert response.status_code == 401


def test_fast_api_health_rejects_invalid_bearer_token_when_configured():
    with _fast_api_test_client(api_key="secret-key") as client:
        response = client.get(
            "/health",
            headers=_authorized_headers("wrong-key", scheme="bearer"),
        )

    assert response.status_code == 401


def test_fast_api_health_accepts_bearer_token_when_configured():
    with _fast_api_test_client(api_key="secret-key") as client:
        response = client.get(
            "/health",
            headers=_authorized_headers("secret-key", scheme="bearer"),
        )

    assert response.status_code in {200, 503}


def test_fast_api_health_accepts_x_api_key_when_configured():
    with _fast_api_test_client(api_key="secret-key") as client:
        response = client.get(
            "/health",
            headers=_authorized_headers("secret-key", scheme="x-api-key"),
        )

    assert response.status_code in {200, 503}


def test_fast_api_health_accepts_trimmed_bearer_token_when_configured_key_has_whitespace():
    with _fast_api_test_client(api_key="  secret-key  ") as client:
        response = client.get(
            "/health",
            headers=_authorized_headers("secret-key", scheme="bearer"),
        )

    assert response.status_code in {200, 503}


def test_router_health_rejects_missing_api_key_when_configured():
    with _router_test_client(api_key="secret-key") as client:
        response = client.get("/health")

    assert response.status_code == 401


def test_router_health_accepts_x_api_key_when_configured():
    with _router_test_client(api_key="secret-key") as client:
        response = client.get(
            "/health",
            headers=_authorized_headers("secret-key", scheme="x-api-key"),
        )

    assert response.status_code in {200, 503}


def test_router_health_accepts_trimmed_x_api_key_when_configured_key_has_whitespace():
    with _router_test_client(api_key="  secret-key  ") as client:
        response = client.get(
            "/health",
            headers=_authorized_headers("secret-key", scheme="x-api-key"),
        )

    assert response.status_code in {200, 503}


@contextmanager
def _fast_api_test_client(api_key):
    original_startup = fast_api.startup_app_state
    original_shutdown = fast_api.shutdown_app_state
    original_api_key = getattr(fast_api.app.state, "api_key", None)

    async def fake_startup(app):
        class _TaskManager:
            last_worker_error = None
            task_retention_seconds = 0
            task_cleanup_interval_seconds = 0
            cleanup_task = None

            def is_healthy(self):
                return True

            def get_stats(self):
                return {
                    fast_api.TASK_PENDING: 0,
                    fast_api.TASK_PROCESSING: 0,
                    fast_api.TASK_COMPLETED: 0,
                    fast_api.TASK_FAILED: 0,
                }

        app.state.task_manager = _TaskManager()
        return app.state.task_manager

    async def fake_shutdown(app):
        app.state.task_manager = None

    fast_api.startup_app_state = fake_startup
    fast_api.shutdown_app_state = fake_shutdown
    fast_api.app.state.api_key = api_key
    try:
        with TestClient(fast_api.app) as client:
            yield client
    finally:
        fast_api.startup_app_state = original_startup
        fast_api.shutdown_app_state = original_shutdown
        fast_api.app.state.api_key = original_api_key


@contextmanager
def _router_test_client(api_key):
    original_startup = router.startup_router_state
    original_shutdown = router.shutdown_router_state

    async def fake_startup(app, settings):
        del settings

        class _WorkerPool:
            def health_payload(self):
                return True, {"status": "healthy"}

        app.state.worker_pool = _WorkerPool()

    async def fake_shutdown(app):
        del app

    router.startup_router_state = fake_startup
    router.shutdown_router_state = fake_shutdown
    try:
        app = router.create_app(router.RouterSettings(local_gpus=router.LOCAL_GPU_NONE))
        app.state.api_key = api_key
        with TestClient(app) as client:
            yield client
    finally:
        router.startup_router_state = original_startup
        router.shutdown_router_state = original_shutdown
