# Operations runbook

## An order is stuck in PREPARING

Look up `GET /orders/{id}` and the order's `order_status_history` rows. In
Temporal UI inspect `order-workflow-{id}` for the last signal/activity and then
tail `temporal-worker` logs using the request correlation ID. Verify that the
restaurant submitted the READY transition and retry only a failed activity.

## Events are not being consumed

Check `docker compose --profile week3 ps`, then inspect the Kafka topic in the
Kafka UI. Compare consumer lag with the `processed_events` table. Do not replay
blindly: replay is safe only because the consumer first claims the event ID.

## Riders are waiting unassigned

Check the order is READY and inspect rider availability. The Celery beat task
`requeue_waiting_orders` retries dispatch every 30 seconds. If it is not
running, start `beat` and the Celery `worker`; do not hand-edit rider state.
