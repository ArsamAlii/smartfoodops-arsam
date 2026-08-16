from datetime import timedelta

from temporalio import workflow


with workflow.unsafe.imports_passed_through():

    from app.workflows.activities.order_activities import (
        update_order_status,
        validate_order_workflow,
    )


# ===========================================================
# Order Workflow
# ===========================================================

@workflow.defn
class OrderWorkflow:

    def __init__(self):
        self.current_status = None
        self.requested_statuses = []

    # =======================================================
    # Workflow Run
    # =======================================================

    @workflow.run
    async def run(
        self,
        order_id: int,
    ) -> str:

        # ---------------------------------------------------
        # 1. Get actual order status from PostgreSQL
        # ---------------------------------------------------

        self.current_status = (
            await workflow.execute_activity(
                validate_order_workflow,
                order_id,
                start_to_close_timeout=timedelta(
                    seconds=30
                ),
            )
        )

        workflow.logger.info(
            f"Order {order_id} workflow started "
            f"with status '{self.current_status}'"
        )

        # ---------------------------------------------------
        # 2. Allowed Temporal transitions
        # ---------------------------------------------------

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

        # ---------------------------------------------------
        # 3. Process requested status changes
        # ---------------------------------------------------

        while self.current_status != "completed":

            await workflow.wait_condition(
                lambda: len(
                    self.requested_statuses
                ) > 0
            )

            new_status = (
                self.requested_statuses.pop(0)
            )

            expected_status = (
                allowed_transitions.get(
                    self.current_status
                )
            )

            # ------------------------------------------------
            # Ignore invalid Temporal signals
            # ------------------------------------------------

            if new_status != expected_status:

                workflow.logger.warning(
                    f"Order {order_id}: "
                    f"invalid transition requested: "
                    f"'{self.current_status}' "
                    f"-> '{new_status}'. "
                    f"Expected '{expected_status}'."
                )

                continue

            # ------------------------------------------------
            # Log transition
            # ------------------------------------------------

            workflow.logger.info(
                f"Order {order_id}: "
                f"transitioning "
                f"'{self.current_status}' "
                f"-> '{new_status}'"
            )

            # ------------------------------------------------
            # Update PostgreSQL through Activity
            # ------------------------------------------------

            await workflow.execute_activity(
                update_order_status,
                args=[
                    order_id,
                    self.current_status,
                    new_status,
                ],
                start_to_close_timeout=timedelta(
                    seconds=30
                ),
            )

            # ------------------------------------------------
            # Only update workflow state after the
            # database Activity succeeds
            # ------------------------------------------------

            self.current_status = new_status

            workflow.logger.info(
                f"Order {order_id}: "
                f"transition completed. "
                f"Current status = "
                f"'{self.current_status}'"
            )

        # ---------------------------------------------------
        # 4. Wait for signal handlers to finish
        # ---------------------------------------------------

        await workflow.wait_condition(
            workflow.all_handlers_finished
        )

        workflow.logger.info(
            f"Order {order_id} workflow completed"
        )

        return (
            f"Order {order_id} workflow completed"
        )

    # =======================================================
    # Update Status Signal
    # =======================================================

    @workflow.signal
    async def update_status(
        self,
        status: str,
    ):

        workflow.logger.info(
            f"Order {self.current_status}: "
            f"received status signal '{status}'"
        )

        self.requested_statuses.append(
            status
        )