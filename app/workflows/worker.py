import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from app.workflows.order_workflow import OrderWorkflow
from app.workflows.activities.order_activities import (
    validate_order_workflow,
)


async def main():
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue="smartfoodops-task-queue",
        workflows=[OrderWorkflow],
        activities=[
            validate_order_workflow,
        ],
    )

    print("Temporal worker started...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())