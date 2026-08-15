from temporalio.client import Client

from app.workflows.order_workflow import OrderWorkflow


TASK_QUEUE = "smartfoodops-task-queue"


async def start_order_workflow(
#    client: Client,
    order_id: int,
):
    workflow_id = f"order-workflow-{order_id}"

    return await client.start_workflow(
        OrderWorkflow.run,
        order_id,
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )


async def signal_order_status(
#    client: Client,
    order_id: int,
    status: str,
):
    workflow_id = f"order-workflow-{order_id}"

    handle = client.get_workflow_handle(
        workflow_id
    )

    await handle.signal(
        OrderWorkflow.update_status,
        status,
    )