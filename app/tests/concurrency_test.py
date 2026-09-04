import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.db.database import SessionLocal
from app.models.enums import UserRole
from app.models.menu_item import MenuItem
from app.models.order import Order
from app.models.restaurant import Restaurant
from app.models.users import User
from app.schemas.order import OrderCreate, PaymentMethod
from app.schemas.order_item import OrderItemCreate
from app.services.order_service import create_order
from app.services.rider_assignment_service import assign_available_rider


# ============================================================
# TEST CONFIGURATION
# ============================================================

STOCK_TO_TEST = 3
NUMBER_OF_STOCK_ORDERS = 5
NUMBER_OF_RIDER_ORDERS = 2


# ============================================================
# STOCK CONCURRENCY TEST
# ============================================================

def stock_worker(
    customer_id,
    restaurant_id,
    menu_item_id,
    start_event,
    worker_number,
    test_run_id,
):
    """
    Worker used by the stock concurrency test.

    Every worker gets a UNIQUE idempotency key so that
    previous test runs cannot cause create_order() to simply
    return an old order.
    """

    db = SessionLocal()

    try:
        # Make all workers wait until the test releases them.
        start_event.wait()

        order_data = OrderCreate(
            restaurant_id=restaurant_id,
            payment_method=PaymentMethod.COD,
            items=[
                OrderItemCreate(
                    menu_item_id=menu_item_id,
                    quantity=1,
                )
            ],
        )

        # IMPORTANT:
        # test_run_id makes the key unique for every execution.
        idempotency_key = (
            f"concurrency-stock-"
            f"{test_run_id}-"
            f"{worker_number}"
        )

        order = create_order(
            db=db,
            customer_id=customer_id,
            order_data=order_data,
            idempotency_key=idempotency_key,
        )

        return {
            "success": True,
            "order_id": order.order_id,
            "worker": worker_number,
        }

    except Exception as exc:
        return {
            "success": False,
            "worker": worker_number,
            "error": str(exc),
        }

    finally:
        db.close()


def run_stock_test():
    """
    Test concurrent stock reservation.

    Initial stock = 3
    Concurrent orders = 5

    Expected:
        3 successful orders
        2 rejected orders
        final stock = 0

    The test verifies that row-level locking prevents
    overselling when multiple transactions try to reserve
    the same stock simultaneously.
    """

    print()
    print("=" * 60)
    print("FLOW 2 — STOCK CONCURRENCY TEST")
    print("=" * 60)

    db = SessionLocal()

    try:
        # ----------------------------------------------------
        # Find an open restaurant
        # ----------------------------------------------------

        restaurant = (
            db.query(Restaurant)
            .filter(Restaurant.is_open.is_(True))
            .first()
        )

        if restaurant is None:
            raise RuntimeError(
                "No open restaurant found."
            )

        # ----------------------------------------------------
        # Find an available menu item with stock
        # ----------------------------------------------------

        menu_item = (
            db.query(MenuItem)
            .join(MenuItem.category)
            .filter(
                MenuItem.is_available.is_(True),
                MenuItem.stock.isnot(None),
                MenuItem.stock > 0,
                MenuItem.category.has(
                    restaurant_id=restaurant.restaurant_id
                ),
            )
            .order_by(MenuItem.menu_item_id)
            .first()
        )

        if menu_item is None:
            raise RuntimeError(
                "No available menu item with stock found."
            )

        # ----------------------------------------------------
        # Find a customer
        # ----------------------------------------------------

        customer = (
            db.query(User)
            .filter(
                User.role == UserRole.CUSTOMER
            )
            .first()
        )

        if customer is None:
            raise RuntimeError(
                "No customer found."
            )

        # ----------------------------------------------------
        # Reset stock to exactly 3
        # ----------------------------------------------------

        menu_item.stock = STOCK_TO_TEST
        db.commit()

        restaurant_id = restaurant.restaurant_id
        menu_item_id = menu_item.menu_item_id
        customer_id = customer.user_id
        menu_item_name = menu_item.name

        print(
            f"Restaurant ID : {restaurant_id}"
        )
        print(
            f"Menu Item ID   : {menu_item_id}"
        )
        print(
            f"Menu Item      : {menu_item_name}"
        )
        print(
            f"Initial Stock  : {STOCK_TO_TEST}"
        )
        print(
            f"Concurrent Orders: "
            f"{NUMBER_OF_STOCK_ORDERS}"
        )
        print()

        # ----------------------------------------------------
        # Create a unique test-run identifier
        # ----------------------------------------------------

        test_run_id = time.time_ns()

        # ----------------------------------------------------
        # Start workers simultaneously
        # ----------------------------------------------------

        start_event = threading.Event()

        results = []

        with ThreadPoolExecutor(
            max_workers=NUMBER_OF_STOCK_ORDERS
        ) as executor:

            futures = [
                executor.submit(
                    stock_worker,
                    customer_id,
                    restaurant_id,
                    menu_item_id,
                    start_event,
                    worker_number,
                    test_run_id,
                )
                for worker_number in range(
                    NUMBER_OF_STOCK_ORDERS
                )
            ]

            # Release all workers at approximately
            # the same time.
            start_event.set()

            for future in as_completed(futures):
                results.append(
                    future.result()
                )

        # ----------------------------------------------------
        # Read final stock using a fresh transaction
        # ----------------------------------------------------

        db.expire_all()

        final_item = (
            db.query(MenuItem)
            .filter(
                MenuItem.menu_item_id
                == menu_item_id
            )
            .first()
        )

        # ----------------------------------------------------
        # Separate successful and failed orders
        # ----------------------------------------------------

        successful = [
            result
            for result in results
            if result["success"]
        ]

        failed = [
            result
            for result in results
            if not result["success"]
        ]

        # ----------------------------------------------------
        # Print results
        # ----------------------------------------------------

        print("RESULTS")
        print("-" * 60)

        for result in sorted(
            results,
            key=lambda x: x["worker"],
        ):

            if result["success"]:

                print(
                    f"SUCCESS -> "
                    f"Order {result['order_id']} "
                    f"(worker {result['worker']})"
                )

            else:

                print(
                    f"REJECTED -> "
                    f"worker {result['worker']}: "
                    f"{result['error']}"
                )

        print("-" * 60)

        print(
            f"Successful orders : "
            f"{len(successful)}"
        )

        print(
            f"Rejected orders   : "
            f"{len(failed)}"
        )

        print(
            f"Final stock       : "
            f"{final_item.stock}"
        )

        # ----------------------------------------------------
        # Verify invariant
        # ----------------------------------------------------

        if (
            len(successful) == STOCK_TO_TEST
            and len(failed)
            == (
                NUMBER_OF_STOCK_ORDERS
                - STOCK_TO_TEST
            )
            and final_item.stock == 0
        ):

            print()
            print(
                "PASS: Stock concurrency "
                "invariant preserved."
            )

        else:

            print()
            print(
                "FAIL: Stock concurrency "
                "invariant violated."
            )

            print()
            print(
                "Expected:"
            )

            print(
                f"  Successful orders = "
                f"{STOCK_TO_TEST}"
            )

            print(
                f"  Rejected orders = "
                f"{NUMBER_OF_STOCK_ORDERS - STOCK_TO_TEST}"
            )

            print(
                "  Final stock = 0"
            )

    finally:
        db.close()


# ============================================================
# RIDER CONCURRENCY TEST
# ============================================================

def rider_worker(
    order_id,
    start_event,
):
    """
    Worker used by the rider concurrency test.

    Both workers attempt to assign the same available rider
    to different READY orders at the same time.
    """

    db = SessionLocal()

    try:
        # Make both workers start together.
        start_event.wait()

        rider_id = assign_available_rider(
            db=db,
            order_id=order_id,
        )

        return {
            "order_id": order_id,
            "rider_id": rider_id,
        }

    except Exception as exc:

        return {
            "order_id": order_id,
            "error": str(exc),
        }

    finally:
        db.close()


def run_rider_test():
    """
    Test concurrent rider assignment.

    Two READY orders compete for one available rider.

    Expected:
        One order gets the rider.
        One order remains READY.
        Rider becomes unavailable.

    This verifies that the rider row lock and
    skip_locked behavior prevent assigning the same rider
    to multiple orders.
    """

    print()
    print("=" * 60)
    print("FLOW 2 — RIDER CONCURRENCY TEST")
    print("=" * 60)

    db = SessionLocal()

    try:
        # ----------------------------------------------------
        # Find an open restaurant
        # ----------------------------------------------------

        restaurant = (
            db.query(Restaurant)
            .filter(Restaurant.is_open.is_(True))
            .first()
        )

        if restaurant is None:
            raise RuntimeError(
                "No open restaurant found."
            )

        # ----------------------------------------------------
        # Find a customer
        # ----------------------------------------------------

        customer = (
            db.query(User)
            .filter(
                User.role == UserRole.CUSTOMER
            )
            .first()
        )

        if customer is None:
            raise RuntimeError(
                "No customer found."
            )

        # ----------------------------------------------------
        # Find a rider
        # ----------------------------------------------------

        rider = (
            db.query(User)
            .filter(
                User.role == UserRole.RIDER,
            )
            .order_by(User.user_id)
            .first()
        )

        if rider is None:
            raise RuntimeError(
                "No rider found."
            )

        # ----------------------------------------------------
        # IMPORTANT:
        # Reset rider availability before the test.
        #
        # Previous concurrency tests may have left the rider
        # unavailable.
        # ----------------------------------------------------

        rider.is_available = True
        db.commit()

        # ----------------------------------------------------
        # Create two READY orders
        # ----------------------------------------------------

        order1 = Order(
            customer_id=customer.user_id,
            restaurant_id=restaurant.restaurant_id,
            status="ready",
            total_amount=0,
        )

        order2 = Order(
            customer_id=customer.user_id,
            restaurant_id=restaurant.restaurant_id,
            status="ready",
            total_amount=0,
        )

        db.add_all(
            [
                order1,
                order2,
            ]
        )

        db.commit()

        db.refresh(order1)
        db.refresh(order2)

        order1_id = order1.order_id
        order2_id = order2.order_id
        rider_id = rider.user_id

        print(
            f"Available Rider : {rider_id}"
        )

        print(
            f"Order 1         : {order1_id}"
        )

        print(
            f"Order 2         : {order2_id}"
        )

        print(
            "Both orders are READY."
        )

        print(
            "Both will compete for the SAME rider."
        )

        print()

        # ----------------------------------------------------
        # Start both workers simultaneously
        # ----------------------------------------------------

        start_event = threading.Event()

        results = []

        with ThreadPoolExecutor(
            max_workers=NUMBER_OF_RIDER_ORDERS
        ) as executor:

            futures = [
                executor.submit(
                    rider_worker,
                    order1_id,
                    start_event,
                ),
                executor.submit(
                    rider_worker,
                    order2_id,
                    start_event,
                ),
            ]

            # Release both workers.
            start_event.set()

            for future in as_completed(futures):
                results.append(
                    future.result()
                )

        # ----------------------------------------------------
        # Reload orders and rider
        # ----------------------------------------------------

        db.expire_all()

        final_orders = (
            db.query(Order)
            .filter(
                Order.order_id.in_(
                    [
                        order1_id,
                        order2_id,
                    ]
                )
            )
            .order_by(Order.order_id)
            .all()
        )

        final_rider = (
            db.query(User)
            .filter(
                User.user_id == rider_id
            )
            .first()
        )

        # ----------------------------------------------------
        # Identify assigned/unassigned orders
        # ----------------------------------------------------

        assigned_orders = [
            order
            for order in final_orders
            if order.rider_id is not None
        ]

        unassigned_orders = [
            order
            for order in final_orders
            if order.rider_id is None
        ]

        # ----------------------------------------------------
        # Print results
        # ----------------------------------------------------

        print("RESULTS")
        print("-" * 60)

        for order in final_orders:

            print(
                f"Order {order.order_id}: "
                f"status={order.status}, "
                f"rider_id={order.rider_id}"
            )

        print("-" * 60)

        print(
            f"Assigned orders   : "
            f"{len(assigned_orders)}"
        )

        print(
            f"Unassigned orders : "
            f"{len(unassigned_orders)}"
        )

        print(
            f"Rider available   : "
            f"{final_rider.is_available}"
        )

        # ----------------------------------------------------
        # Verify rider concurrency invariant
        # ----------------------------------------------------

        if (
            len(assigned_orders) == 1
            and len(unassigned_orders) == 1
            and final_rider.is_available is False
        ):

            print()
            print(
                "PASS: Rider concurrency "
                "invariant preserved."
            )

        else:

            print()
            print(
                "FAIL: Rider concurrency "
                "invariant violated."
            )

    finally:
        db.close()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    run_stock_test()

    run_rider_test()

    print()
    print("=" * 60)
    print("FLOW 2 CONCURRENCY TEST COMPLETE")
    print("=" * 60)
