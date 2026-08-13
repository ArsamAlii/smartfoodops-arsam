import asyncio

from temporalio.client import Client

from app.workflows.order_workflow import OrderWorkflow


async def main():
    client = await Client.connect("localhost:7233")

    workflow_id = "order-workflow-1"

    handle = await client.start_workflow(
        OrderWorkflow.run,
        1,
        id=workflow_id,
        task_queue="smartfoodops-task-queue",
    )

    print(f"Started workflow: {workflow_id}")

    statuses = [
        "payment_confirmed",
        "confirmed",
        "preparing",
        "ready",
        "assigned",
        "picked_up",
        "delivered",
        "completed",
    ]

    for status in statuses:

        await handle.signal(
            OrderWorkflow.update_status,
            status,
        )

        print(f"Sent signal: {status}")

        await asyncio.sleep(1)

    result = await handle.result()

    print("Workflow result:", result)


if __name__ == "__main__":
    asyncio.run(main())