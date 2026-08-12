import asyncio

from temporalio.client import Client

from app.workflows.test_workflow import TestWorkflow


async def main():
    client = await Client.connect("localhost:7233")

    result = await client.execute_workflow(
        TestWorkflow.run,
        "SmartFoodOps",
        id="test-workflow-1",
        task_queue="smartfoodops-task-queue",
    )

    print("Workflow result:", result)


if __name__ == "__main__":
    asyncio.run(main())