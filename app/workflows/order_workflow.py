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
        self.requested_statuses = []

    @workflow.run
    async def run(self, order_id: int) -> str:

        # 1. Verify that the order exists
        await workflow.execute_activity(
            validate_order_workflow,
            order_id,
            start_to_close_timeout=timedelta(seconds=30),
        )

        # 2. Allowed order status transitions
        allowed_transitions = {
            "placed": "payment_confirmed",
            "payment_confirmed": "confirmed",
            "confirmed": "preparing",
            "preparing": "ready",
            "ready": "assigned",
            "assigned": "picked_up",
            "picked_up": "delivered",
            "delivered": "completed",
        }

        # 3. Process status changes
        while self.current_status != "completed":

            await workflow.wait_condition(
                lambda: len(self.requested_statuses) > 0
            )

            new_status = self.requested_statuses.pop(0)

            expected_status = allowed_transitions.get(
                self.current_status
            )

            if new_status != expected_status:
                continue

            await workflow.execute_activity(
                update_order_status,
                args=[order_id, new_status],
                start_to_close_timeout=timedelta(seconds=30),
            )

            self.current_status = new_status
                    # 7. Wait for signal handlers
                    await workflow.wait_condition(
                        workflow.all_handlers_finished
                    )

        return f"Order {order_id} workflow completed"

    @workflow.signal
    async def update_status(
        self,
        status: str,
    ):
        self.requested_statuses.append(status)