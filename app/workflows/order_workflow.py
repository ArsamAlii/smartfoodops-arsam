from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from app.workflows.activities.order_activities import (
        validate_order_workflow,
        update_order_status,
    )


@workflow.defn
class OrderWorkflow:

    def __init__(self):
        self.current_status = "placed"
        self.order_id = None

    @workflow.run
    async def run(self, order_id: int) -> str:

        # Save the order ID inside the Workflow state
        self.order_id = order_id

        # ---------------------------------------------------
        # Verify that the order exists
        # ---------------------------------------------------

        await workflow.execute_activity(
            validate_order_workflow,
            order_id,
            start_to_close_timeout=timedelta(seconds=30),
        )

        # ---------------------------------------------------
        # Wait until order is completed
        # ---------------------------------------------------

        await workflow.wait_condition(
            lambda: self.current_status == "completed"
        )

        return (
            f"Order {order_id} workflow completed"
        )

    @workflow.signal
    async def update_status(self, status: str):

        # Update Temporal state
        self.current_status = status

        # Update PostgreSQL through an Activity
        await workflow.wait_condition(
            lambda: self.current_status == "completed"
        )

        await workflow.wait_condition(
            workflow.all_handlers_finished
        )

        return f"Order {order_id} workflow completed"