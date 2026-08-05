from enum import Enum


class UserRole(str, Enum):
    CUSTOMER = "customer"
    RESTAURANT_ADMIN = "restaurant_admin"
    RIDER = "rider"
    ADMIN = "admin"