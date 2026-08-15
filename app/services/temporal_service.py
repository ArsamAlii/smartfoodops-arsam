from temporalio.client import Client

from app.workflows.order_workflow import OrderWorkflow


TEMPORAL_SERVER = "localhost:7233"
TEMPORAL_TASK_QUEUE = "smartfoodops-task-queue"


async def start_order_workflow(order_id: int):
    client = await Client.connect(TEMPORAL_SERVER)

    workflow_id = f"order-workflow-{order_id}"

    handle = await client.start_workflow(
        OrderWorkflow.run,
        order_id,
        id=workflow_id,
        task_queue=TEMPORAL_TASK_QUEUE,
    )

    return handle