from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from app.workflows.activities.order_activities import (
        update_order_status,
        validate_order_workflow,
    )


@workflow.defn
class OrderWorkflow:

    def __init__(self):
        self.current_status = "placed"
        self.requested_status = None

    @workflow.run
    async def run(self, order_id: int) -> str:

        # --------------------------------------------------
        # 1. Verify that the order exists
        # --------------------------------------------------

        await workflow.execute_activity(
            validate_order_workflow,
            order_id,
            start_to_close_timeout=timedelta(seconds=30),
        )

        # --------------------------------------------------
        # 2. Process status changes
        # --------------------------------------------------

        while self.current_status != "completed":

            # Wait until a status signal arrives
            await workflow.wait_condition(
                lambda: self.requested_status is not None
            )

            # Get requested status
            new_status = self.requested_status

            # Clear it so we can wait for the next signal
            self.requested_status = None

            # Update database
            await workflow.execute_activity(
                update_order_status,
                args=[order_id, new_status],
                start_to_close_timeout=timedelta(seconds=30),
            )

            # Update workflow state only after database update succeeds
            self.current_status = new_status

        # --------------------------------------------------
        # 3. Wait for signal handlers to finish
        # --------------------------------------------------

        await workflow.wait_condition(
            workflow.all_handlers_finished
        )

        return f"Order {order_id} workflow completed"

    @workflow.signal
    async def update_status(
        self,
        status: str,
    ):
        self.requested_status = status