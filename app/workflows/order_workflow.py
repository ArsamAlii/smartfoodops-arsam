from datetime import timedelta

from temporalio import workflow


with workflow.unsafe.imports_passed_through():

    from app.workflows.activities.order_activities import (
        validate_order_workflow,
        update_order_status,
        cancel_order,
        assign_rider,
    )


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
        # Get current status
        # ---------------------------------------------------

        self.current_status = await workflow.execute_activity(
            validate_order_workflow,
            order_id,
            start_to_close_timeout=timedelta(
                seconds=30
            ),
        )

        workflow.logger.info(
            f"Order {order_id} workflow started "
            f"with status '{self.current_status}'"
        )

        # ---------------------------------------------------
        # Automatic payment confirmation
        # ---------------------------------------------------

        if self.current_status == "placed":

            await workflow.execute_activity(
                update_order_status,
                args=[
                    order_id,
                    "placed",
                    "payment_confirmed",
                ],
                start_to_close_timeout=timedelta(
                    seconds=30
                ),
            )

            self.current_status = "payment_confirmed"

        # ---------------------------------------------------
        # Normal transitions
        # ---------------------------------------------------

        allowed_transitions = {

            "placed": "payment_confirmed",

            "payment_confirmed": "confirmed",

            "confirmed": "preparing",

            "preparing": "ready",

            "assigned": "picked_up",

            "picked_up": "delivered",

            "delivered": "completed",
        }

        # ---------------------------------------------------
        # Process signals
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

            # =================================================
            # CANCELLATION / REJECTION
            # =================================================

            if new_status in {
                "cancelled",
                "rejected",
            }:

                cancellable_statuses = {
                    "placed",
                    "payment_confirmed",
                    "confirmed",
                }

                if (
                    self.current_status
                    not in cancellable_statuses
                ):
                    workflow.logger.warning(
                        f"Order {order_id}: "
                        f"cannot cancel/reject from "
                        f"'{self.current_status}'"
                    )
                    continue

                await workflow.execute_activity(
                    cancel_order,
                    args=[
                        order_id,
                        self.current_status,
                        new_status,
                    ],
                    start_to_close_timeout=timedelta(
                        seconds=30
                    ),
                )

                self.current_status = new_status

                return (
                    f"Order {order_id} "
                    f"was {new_status}"
                )

            # =================================================
            # AUTOMATIC DISPATCH
            #
            # READY → ASSIGNED
            #
            # This is a dispatch request.
            #
            # We DO NOT directly update the order to ASSIGNED.
            # The assignment activity atomically assigns the
            # rider and changes the database status.
            # =================================================

            if (
                self.current_status == "ready"
                and new_status == "assigned"
            ):

                workflow.logger.info(
                    f"Order {order_id}: "
                    f"attempting automatic rider assignment"
                )

                rider_id = await workflow.execute_activity(
                    assign_rider,
                    order_id,
                    start_to_close_timeout=timedelta(
                        seconds=30
                    ),
                )

                if rider_id is None:

                    workflow.logger.info(
                        f"Order {order_id}: "
                        f"no rider available. "
                        f"Order remains READY."
                    )

                    self.current_status = "ready"

                else:

                    workflow.logger.info(
                        f"Order {order_id}: "
                        f"rider {rider_id} assigned"
                    )

                    self.current_status = "assigned"

                continue

            # =================================================
            # NORMAL STATUS TRANSITION
            # =================================================

            expected_status = (
                allowed_transitions.get(
                    self.current_status
                )
            )

            # -------------------------------------------------
            # Ignore invalid signals
            # -------------------------------------------------

            if new_status != expected_status:

                workflow.logger.warning(
                    f"Order {order_id}: "
                    f"invalid transition requested: "
                    f"'{self.current_status}' "
                    f"-> '{new_status}'. "
                    f"Expected '{expected_status}'."
                )

                continue

            # -------------------------------------------------
            # Update PostgreSQL through activity
            # -------------------------------------------------

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

            # -------------------------------------------------
            # Update workflow state
            # -------------------------------------------------

            self.current_status = new_status

            workflow.logger.info(
                f"Order {order_id}: "
                f"transition completed. "
                f"Current status = "
                f"'{self.current_status}'"
            )

        # ---------------------------------------------------
        # Workflow completed
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
    # Status Signal
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

        self.requested_statuses.append(status)