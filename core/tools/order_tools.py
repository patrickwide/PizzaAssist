from typing import Optional, List, Any, Dict
from datetime import datetime
import json
from core.constants import ORDER_FILE_PATH

def tool_place_order(
    pizza_type: str,
    size: str,
    quantity: Any,  # Accept Any initially, as LLM might send string or int
    delivery_address: str,
    customer_name: Optional[str] = None,
    phone_number: Optional[str] = None,
    crust_type: Optional[str] = "Regular",
    extra_toppings: Optional[List[str]] = None,
) -> str:
    """
    Places a pizza order with the specified details and saves it to a file.
    Use this tool *only* when the user explicitly confirms they want to place an order
    and has provided the necessary details (pizza type, size, quantity, delivery address).

    Args:
        pizza_type: The type of pizza being ordered (e.g., 'Pepperoni', 'Margherita').
        size: The size of the pizza (e.g., 'Large', 'Medium').
        quantity: The number of pizzas of this type and size (should be an integer).
        delivery_address: The full address for delivery.
        customer_name: The name of the customer placing the order (optional).
        phone_number: The contact phone number for the order (optional).
        crust_type: The desired crust type (e.g., 'Thin', 'Stuffed', defaults to 'Regular').
        extra_toppings: A list of any extra toppings requested (optional).

    Returns:
        A JSON string confirming the order details placed or an error message.
    """
    print(f"\n--- Tool Call: tool_place_order ---")
    print(f"--- Raw Args: pizza_type='{pizza_type}', size='{size}', quantity='{quantity}' (type: {type(quantity)}), address='{delivery_address}', "
          f"name='{customer_name}', phone='{phone_number}', crust='{crust_type}', extras={extra_toppings}")

    # --- Convert quantity to integer and validate ---
    quantity_int: Optional[int] = None
    try:
        quantity_int = int(quantity)  # Attempt conversion
        if quantity_int <= 0:
            raise ValueError("Quantity must be positive.")  # Add check for non-positive numbers
    except (ValueError, TypeError) as e:
        error_msg = f"Invalid quantity received: '{quantity}'. Quantity must be a positive whole number. Error: {e}"
        print(f"--- Validation Error: {error_msg}")
        return json.dumps({"error": error_msg})

    # --- Use the validated integer quantity_int moving forward ---
    print(f"--- Validated Args: pizza_type='{pizza_type}', size='{size}', quantity={quantity_int}, address='{delivery_address}', "
          f"name='{customer_name}', phone='{phone_number}', crust='{crust_type}', extras={extra_toppings}")

    # Simplified validation now relies on successful conversion above and checks other fields
    if not all([pizza_type, size, delivery_address]):  # quantity_int > 0 already checked
        error_msg = "Missing required order details: pizza_type, size, and delivery_address are mandatory."
        print(f"--- Validation Error: {error_msg}")
        return json.dumps({"error": error_msg})

    order_details = {
        "order_timestamp": datetime.now().isoformat(),
        "pizza_type": pizza_type,
        "size": size,
        "quantity": quantity_int,
        "crust_type": crust_type if crust_type else "Regular",
        "extra_toppings": extra_toppings if extra_toppings is not None else [],
        "delivery_address": delivery_address,
        "customer_name": customer_name,
        "phone_number": phone_number,
        "status": "Received"
    }

    try:
        # Append the order as a JSON line to the order file
        with open(ORDER_FILE_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps(order_details) + '\n')
        print(f"--- Order successfully saved to {ORDER_FILE_PATH}")

        confirmation_message = {
            "status": "Order Placed Successfully",
            "confirmation": f"OK. Your order for {quantity_int} x {size} {pizza_type} pizza(s) "
                          f"{('with crust ' + order_details['crust_type']) if order_details['crust_type'] != 'Regular' else ''} "
                          f"{('and extra ' + ', '.join(order_details['extra_toppings']) + ' ') if order_details['extra_toppings'] else ''}"
                          f"to be delivered to '{delivery_address}' has been received.",
        }
        return json.dumps(confirmation_message, indent=2)

    except IOError as e:
        print(f"Error saving order to {ORDER_FILE_PATH}: {e}")
        return json.dumps({"error": f"Failed to save the order due to a file system error: {str(e)}"})
    except Exception as e:
        print(f"An unexpected error occurred during order placement: {e}")
        return json.dumps({"error": f"An unexpected error occurred: {str(e)}"})

def get_tool_info() -> Dict[str, Any]:
    """Return the tool definition for this module."""
    return {
        "type": "function",
        "function": {
            "name": "tool_place_order",
            "description": "Places a pizza order with the specified details and saves it. Use this tool ONLY when the user explicitly confirms they want to place an order and has provided AT LEAST the pizza type, size, quantity, and delivery address. Ask clarifying questions first if details are missing. Do not invent details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pizza_type": {"type": "string", "description": "The type of pizza (e.g., 'Pepperoni', 'Margherita', 'Vegan Supreme')."},
                    "size": {"type": "string", "description": "The size of the pizza (e.g., 'Large', 'Medium', 'Small')."},
                    "quantity": {"type": "integer", "description": "The number of pizzas."},
                    "delivery_address": {"type": "string", "description": "The full delivery address."},
                    "customer_name": {"type": "string", "description": "Customer's name (optional). Omit if not provided."},
                    "phone_number": {"type": "string", "description": "Customer's phone number (optional). Omit if not provided."},
                    "crust_type": {"type": "string", "description": "Desired crust type (e.g., 'Thin', 'Regular', 'Stuffed'). Defaults to 'Regular' if not specified.", "default": "Regular"},
                    "extra_toppings": {"type": "array", "items": {"type": "string"}, "description": "List of extra toppings (optional). Provide as an empty list if none."},
                },
                "required": ["pizza_type", "size", "quantity", "delivery_address"],
            },
        },
    }