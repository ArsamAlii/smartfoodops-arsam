# SmartFoodOps design

## Modules

`api` authenticates and authorizes requests; `services` owns domain rules;
`models` maps PostgreSQL tables; Temporal owns long-running fulfilment; Celery
handles periodic retry work; and the Kafka consumer (to be added in the Week 3
event slice) owns analytics projections.

## Ordering and fulfilment

`POST /orders` creates one order per customer idempotency key and returns 202.
The database transaction validates every cart item, snapshots its price,
reserves finite stock, records the payment authorization, history row and
idempotency record. Temporal then projects `PLACED -> PAYMENT_CONFIRMED` and
waits for authorized restaurant/rider signals. The order row is a projection;
Temporal workflow history is the durable orchestration record.

## Concurrency decisions

Stock rows are selected with `FOR UPDATE` before finite stock is decremented,
so competing transactions serialize. A null `stock` means unlimited and is
never decremented.

Rider dispatch locks both the READY order and an AVAILABLE rider with
`FOR UPDATE SKIP LOCKED`, changes availability and assignment in one
transaction, and has a partial unique index over active rider assignments.
The index is a final database-level guard; a read-then-write availability check
would race under concurrent dispatchers.

## Search-ready menu data

Publishing a menu stores deterministic restaurant and available-item chunks in
`content_chunks`. Each chunk has the restaurant/item relationship, category,
ordinal, text, and approximate token count. Part B can embed these rows without
reconstructing menus.

## Tradeoffs

The current payment authorizer is intentionally internal and deterministic: it
permits exercising failure handling without handling payment-card data. Rider
selection is first-available rather than geographic routing, which keeps the
assignment focus on correctness under concurrency.
