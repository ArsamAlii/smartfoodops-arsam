import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from app.workflows.order_workflow import OrderWorkflow

from app.workflows.activities.order_activities import (
    validate_order_workflow,
    update_order_status,
    cancel_order,
)


TEMPORAL_SERVER = "localhost:7233"

TASK_QUEUE = "smartfoodops-task-queue"


async def main():

    print("Connecting to Temporal...")

    client = await Client.connect(
        TEMPORAL_SERVER
    )

    print("Connected to Temporal.")

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[
            OrderWorkflow,
        ],
        activities=[
            validate_order_workflow,
            update_order_status,
            cancel_order,
        ],
    )

    print("Temporal worker started...")

    print(
        f"Task queue: {TASK_QUEUE}"
    )

    print(
        "Waiting for workflow/activity tasks..."
    )

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())