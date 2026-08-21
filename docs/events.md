# Domain events

The Week 3 event publisher/consumer uses JSON envelopes:

```json
{
  "event_id": "uuid",
  "event_type": "order.confirmed",
  "occurred_at": "ISO-8601 UTC",
  "version": 1,
  "correlation_id": "request id",
  "data": {"order_id": 123}
}
```

Events: `order.placed`, `payment.succeeded`, `order.confirmed`,
`rider.assigned`, `order.picked_up`, `order.delivered`, `order.cancelled`, and
`refund.processed`. Producers emit only after the corresponding durable state
change. Consumers must insert `event_id` into `processed_events` under a unique
constraint before updating aggregates; a duplicate insert means the event is a
no-op.
