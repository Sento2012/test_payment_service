"""Consumer-роутинг ошибок: до исчерпания попыток — в retry-очередь уровня, после —
в DLQ. Проверяем, что сообщения реально уходят в нужную очередь."""


async def test_failed_processing_goes_to_retry_queue(app_setup, rabbit):
    from worker.consumer.main import _route_to_retry_or_dlq

    body = {"payment_id": "11111111-1111-1111-1111-111111111111"}
    # attempt=0 -> next попытка 1 (<= 3) -> retry-очередь уровня 1
    await _route_to_retry_or_dlq(body, attempt=0, exc=RuntimeError("boom"))

    message = await rabbit.get_message("payments.new.retry.1")
    assert message == body
    assert await rabbit.get_message("payments.new.dlq") is None


async def test_exhausted_retries_go_to_dlq(app_setup, rabbit):
    from worker.consumer.main import _route_to_retry_or_dlq

    body = {"payment_id": "22222222-2222-2222-2222-222222222222"}
    # attempt=3 -> next 4 (> 3 попыток) -> DLQ
    await _route_to_retry_or_dlq(body, attempt=3, exc=RuntimeError("boom"))

    message = await rabbit.get_message("payments.new.dlq")
    assert message == body
    assert await rabbit.get_message("payments.new.retry.1") is None
