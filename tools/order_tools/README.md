# Pizza Order Tool

This tool handles pizza order placement and management.

## Features

- Place new pizza orders
- Validate order details
- Save orders to a persistent storage
- Generate order confirmations

## Usage

The tool can be accessed through the standard tool registry:

```python
from tools.order_tools import OrderTool

# Place an order
order = OrderTool()
result = order.place_pizza_order(
    pizza_type="Margherita",
    size="Large",
    quantity=1,
    delivery_address="123 Main St",
    customer_name="John Doe",  # Optional
    phone_number="555-0123",   # Optional
    crust_type="Thin",        # Optional
    extra_toppings=["Mushrooms", "Olives"]  # Optional
)
```

## Required Parameters

- `pizza_type`: Type of pizza (e.g., 'Pepperoni', 'Margherita')
- `size`: Size of pizza (e.g., 'Large', 'Medium', 'Small')
- `quantity`: Number of pizzas (positive integer)
- `delivery_address`: Full delivery address

## Optional Parameters

- `customer_name`: Customer's name
- `phone_number`: Contact number
- `crust_type`: Type of crust (defaults to 'Regular')
- `extra_toppings`: List of additional toppings

## Storage

Orders are stored in a JSON format in the configured order file location (ORDER_FILE_PATH).