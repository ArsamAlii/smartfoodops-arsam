import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from app.workflows.order_workflow import OrderWorkflow
from app.workflows.activities.order_activities import (
    validate_order_workflow,
    update_order_status,
)


TEMPORAL_SERVER = "localhost:7233"
TASK_QUEUE = "smartfoodops-task-queue"


async def main():
    client = await Client.connect(
        TEMPORAL_SERVER
    )

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[
            OrderWorkflow,
        ],
        activities=[
            validate_order_workflow,
            update_order_status,
        ],
    )

    print(
        "Temporal worker started..."
    )

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())