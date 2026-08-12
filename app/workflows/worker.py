import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from app.workflows.test_workflow import TestWorkflow


async def main():
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue="smartfoodops-task-queue",
        workflows=[TestWorkflow],
    )

    print("Temporal worker started...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())