import os

from temporalio.client import Client
from temporalio.exceptions import WorkflowAlreadyStartedError

from app.workflows.order_workflow import OrderWorkflow


TEMPORAL_SERVER = os.getenv(
    "TEMPORAL_HOST",
    "localhost:7233",
)

TASK_QUEUE = os.getenv(
    "TEMPORAL_TASK_QUEUE",
    "smartfoodops-task-queue",
)


# ===========================================================
# Temporal Client
# ===========================================================

async def get_temporal_client() -> Client:
    return await Client.connect(TEMPORAL_SERVER)


# ===========================================================
# Start Order Workflow
# ===========================================================

async def start_order_workflow(
    order_id: int,
):
    client = await get_temporal_client()

    workflow_id = f"order-workflow-{order_id}"

    try:
        handle = await client.start_workflow(
            OrderWorkflow.run,
            order_id,
            id=workflow_id,
            task_queue=TASK_QUEUE,
        )

        print(
            f"Started Temporal workflow: {workflow_id}"
        )

        return handle

    except WorkflowAlreadyStartedError:

        print(
            f"Temporal workflow already exists: "
            f"{workflow_id}"
        )

        return client.get_workflow_handle(
            workflow_id
        )


# ===========================================================
# Signal Order Workflow
# ===========================================================

async def signal_order_workflow(
    order_id: int,
    status: str,
):
    client = await get_temporal_client()

    workflow_id = f"order-workflow-{order_id}"

    handle = client.get_workflow_handle(
        workflow_id
    )

    description = await handle.describe()

    print(
        f"Temporal workflow found: "
        f"{workflow_id}, "
        f"status={description.status}"
    )

    await handle.signal(
        OrderWorkflow.update_status,
        status,
    )

    print(
        f"Temporal signal sent: "
        f"{status} -> {workflow_id}"
    )