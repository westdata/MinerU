from contextlib import contextmanager
from types import SimpleNamespace

from fastapi.responses import JSONResponse
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


def test_fast_api_health_allows_missing_api_key_when_configured():
    with _fast_api_test_client(api_key="secret-key") as client:
        response = client.get("/health")

    assert response.status_code in {200, 503}


def test_fast_api_health_ignores_invalid_bearer_token_when_configured():
    with _fast_api_test_client(api_key="secret-key") as client:
        response = client.get(
            "/health",
            headers=_authorized_headers("wrong-key", scheme="bearer"),
        )

    assert response.status_code in {200, 503}


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


def test_router_health_allows_missing_api_key_when_configured():
    with _router_test_client(api_key="secret-key") as client:
        response = client.get("/health")

    assert response.status_code in {200, 503}


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


def test_router_apply_request_option_overrides_updates_payload_fields():
    payload = router.MultipartPayload(
        temp_dir="temp",
        fields=[
            ("return_md", "true"),
            ("return_middle_json", "false"),
            ("return_model_output", "false"),
            ("return_content_list", "true"),
            ("return_images", "false"),
            ("return_original_file", "false"),
            ("client_side_output_generation", "true"),
            ("md_page_anchor", "false"),
            ("image_analysis", "true"),
        ],
        uploads=[],
    )
    request_options = SimpleNamespace(
        return_md=False,
        return_middle_json=True,
        return_model_output=True,
        return_content_list=False,
        return_images=True,
        return_original_file=False,
        client_side_output_generation=True,
        md_page_anchor=True,
        image_analysis=False,
    )

    router.apply_request_option_overrides(payload, request_options)

    assert payload.get_field_value("return_md") == "false"
    assert payload.get_field_value("return_middle_json") == "true"
    assert payload.get_field_value("return_model_output") == "true"
    assert payload.get_field_value("return_content_list") == "false"
    assert payload.get_field_value("return_images") == "true"
    assert payload.get_field_value("client_side_output_generation") == "true"
    assert payload.get_field_value("md_page_anchor") == "true"
    assert payload.get_field_value("image_analysis") == "false"


def test_router_tasks_endpoint_rewrites_multipart_fields_from_request_options():
    captured_fields = {}

    async def fake_submit_router_task(request, payload):
        del request
        captured_fields.update(
            {
                "return_md": payload.get_field_value("return_md"),
                "return_middle_json": payload.get_field_value("return_middle_json"),
                "return_model_output": payload.get_field_value("return_model_output"),
                "return_content_list": payload.get_field_value("return_content_list"),
                "return_images": payload.get_field_value("return_images"),
                "client_side_output_generation": payload.get_field_value("client_side_output_generation"),
                "md_page_anchor": payload.get_field_value("md_page_anchor"),
                "image_analysis": payload.get_field_value("image_analysis"),
            }
        )

        return SimpleNamespace(
            to_status_payload=lambda _request: {
                "task_id": "router-task-1",
                "status": "pending",
                "backend": "pipeline",
            }
        )

    with _router_test_client(
        api_key="secret-key",
        submit_router_task_impl=fake_submit_router_task,
    ) as client:
        response = client.post(
            "/tasks",
            headers=_authorized_headers("secret-key", scheme="x-api-key"),
            files=[
                ("files", ("demo.pdf", b"%PDF-1.4\n", "application/pdf")),
            ],
            data={
                "backend": "pipeline",
                "parse_method": "auto",
                "client_side_output_generation": "true",
                "return_md": "true",
                "return_middle_json": "false",
                "return_model_output": "false",
                "return_content_list": "true",
                "return_images": "false",
                "md_page_anchor": "true",
                "image_analysis": "false",
            },
        )

    assert response.status_code == 202
    assert captured_fields == {
        "return_md": "false",
        "return_middle_json": "true",
        "return_model_output": "true",
        "return_content_list": "false",
        "return_images": "true",
        "client_side_output_generation": "true",
        "md_page_anchor": "true",
        "image_analysis": "false",
    }


def test_router_file_parse_endpoint_rewrites_fields_and_returns_sync_response():
    captured_fields = {}

    async def fake_submit_router_task(request, payload):
        del request
        captured_fields.update(
            {
                "return_md": payload.get_field_value("return_md"),
                "return_middle_json": payload.get_field_value("return_middle_json"),
                "return_model_output": payload.get_field_value("return_model_output"),
                "return_content_list": payload.get_field_value("return_content_list"),
                "return_images": payload.get_field_value("return_images"),
                "client_side_output_generation": payload.get_field_value("client_side_output_generation"),
                "md_page_anchor": payload.get_field_value("md_page_anchor"),
                "image_analysis": payload.get_field_value("image_analysis"),
            }
        )

        return SimpleNamespace(
            status=router.TASK_PENDING,
            to_status_payload=lambda _request: {
                "task_id": "router-task-2",
                "status": "pending",
                "backend": "pipeline",
            },
        )

    async def fake_wait_for_router_task_terminal_state(request, task):
        del request
        task.status = router.TASK_COMPLETED
        return task

    async def fake_build_sync_router_task_result_response(request, task):
        del request, task
        return JSONResponse({"ok": True})

    with _router_test_client(
        api_key="secret-key",
        submit_router_task_impl=fake_submit_router_task,
        wait_for_router_task_terminal_state_impl=fake_wait_for_router_task_terminal_state,
        build_sync_router_task_result_response_impl=fake_build_sync_router_task_result_response,
    ) as client:
        response = client.post(
            "/file_parse",
            headers=_authorized_headers("secret-key", scheme="x-api-key"),
            files=[
                ("files", ("demo.pdf", b"%PDF-1.4\n", "application/pdf")),
            ],
            data={
                "backend": "pipeline",
                "parse_method": "auto",
                "client_side_output_generation": "true",
                "return_md": "true",
                "return_middle_json": "false",
                "return_model_output": "false",
                "return_content_list": "true",
                "return_images": "false",
                "md_page_anchor": "false",
                "image_analysis": "true",
            },
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert captured_fields == {
        "return_md": "false",
        "return_middle_json": "true",
        "return_model_output": "true",
        "return_content_list": "false",
        "return_images": "true",
        "client_side_output_generation": "true",
        "md_page_anchor": "false",
        "image_analysis": "true",
    }


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
def _router_test_client(
    api_key,
    submit_router_task_impl=None,
    wait_for_router_task_terminal_state_impl=None,
    build_sync_router_task_result_response_impl=None,
):
    original_startup = router.startup_router_state
    original_shutdown = router.shutdown_router_state
    original_submit_router_task = router.submit_router_task
    original_wait_for_router_task_terminal_state = router.wait_for_router_task_terminal_state
    original_build_sync_router_task_result_response = router.build_sync_router_task_result_response

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
    if submit_router_task_impl is not None:
        router.submit_router_task = submit_router_task_impl
    if wait_for_router_task_terminal_state_impl is not None:
        router.wait_for_router_task_terminal_state = wait_for_router_task_terminal_state_impl
    if build_sync_router_task_result_response_impl is not None:
        router.build_sync_router_task_result_response = build_sync_router_task_result_response_impl
    try:
        app = router.create_app(router.RouterSettings(local_gpus=router.LOCAL_GPU_NONE))
        app.state.api_key = api_key
        with TestClient(app) as client:
            yield client
    finally:
        router.startup_router_state = original_startup
        router.shutdown_router_state = original_shutdown
        router.submit_router_task = original_submit_router_task
        router.wait_for_router_task_terminal_state = original_wait_for_router_task_terminal_state
        router.build_sync_router_task_result_response = original_build_sync_router_task_result_response
