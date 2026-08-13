from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from app.workflows.activities.order_activities import (
        validate_order_workflow,
    )


@workflow.defn
class OrderWorkflow:

    def __init__(self):
        self.status_history: list[str] = []

    @workflow.run
    async def run(self, order_id: int) -> str:

        await workflow.execute_activity(
            validate_order_workflow,
            order_id,
            start_to_close_timeout=timedelta(seconds=30),
        )

        expected_statuses = [
            "payment_confirmed",
            "confirmed",
            "preparing",
            "ready",
            "assigned",
            "picked_up",
            "delivered",
            "completed",
        ]

        for expected_status in expected_statuses:

            await workflow.wait_condition(
                lambda expected=expected_status:
                expected in self.status_history
            )

        return f"Order {order_id} workflow completed"

    @workflow.signal
    async def update_status(self, status: str):
        self.status_history.append(status)