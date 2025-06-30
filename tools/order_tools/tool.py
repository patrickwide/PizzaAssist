"""Pizza ordering tool implementation."""
# --- Standard Library ---
import os
import json
from typing import Optional, List, Any, Dict
from datetime import datetime

# --- Core Imports ---
from core.interfaces.pizza_assist_tool import PizzaAssistTool
from constants import ORDER_FILE_PATH
from logging_config import setup_logger

# Initialize logger
logger = setup_logger(__name__)

class OrderTool(PizzaAssistTool):
    """Tool for placing pizza orders."""
    
    name = "place_pizza_order"
    description = "Places a pizza order with the specified details and saves it. Use this tool ONLY when the user explicitly confirms they want to place an order and has provided AT LEAST the pizza type, size, quantity, and delivery address. Ask clarifying questions first if details are missing. Do not invent details."
    parameters = {
        "type": "object",
        "properties": {
            "pizza_type": {
                "type": "string",
                "description": "The type of pizza (e.g., 'Pepperoni', 'Margherita', 'Vegan Supreme')."
            },
            "size": {
                "type": "string",
                "description": "The size of the pizza (e.g., 'Large', 'Medium', 'Small')."
            },
            "quantity": {
                "type": "integer",
                "description": "The number of pizzas."
            },
            "delivery_address": {
                "type": "string",
                "description": "The full delivery address."
            },
            "customer_name": {
                "type": "string",
                "description": "Customer's name (optional)."
            },
            "phone_number": {
                "type": "string",
                "description": "Customer's phone number (optional)."
            },
            "crust_type": {
                "type": "string",
                "description": "Desired crust type (e.g., 'Thin', 'Regular', 'Stuffed'). Defaults to 'Regular'."
            },
            "extra_toppings": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of extra toppings (optional)."
            }
        },
        "required": ["pizza_type", "size", "quantity", "delivery_address"]
    }
    
    def __init__(self):
        """Initialize the order tool."""
        self.order_file = ORDER_FILE_PATH
        
    def validate(self) -> bool:
        """Validate that the order file is accessible."""
        try:
            if not os.path.exists(self.order_file):
                with open(self.order_file, 'w') as f:
                    pass
            return True
        except Exception as e:
            logger.error(f"Order file validation failed: {e}")
            return False

    def place_pizza_order(
        self,
        pizza_type: str,
        size: str,
        quantity: Any,  # Accept Any initially, as LLM might send string or int
        delivery_address: str,
        customer_name: Optional[str] = None,
        phone_number: Optional[str] = None,
        crust_type: Optional[str] = "Regular",
        extra_toppings: Optional[List[str]] = None,
    ) -> str:
        """Places a pizza order with the specified details."""
        logger.debug(f"Order request received - pizza_type: '{pizza_type}', size: '{size}', quantity: '{quantity}', address: '{delivery_address}'")

        # --- Convert quantity to integer and validate ---
        quantity_int: Optional[int] = None
        try:
            quantity_int = int(quantity)
            if quantity_int <= 0:
                raise ValueError("Quantity must be positive.")
        except (ValueError, TypeError) as e:
            error_msg = f"Invalid quantity received: '{quantity}'. Quantity must be a positive whole number. Error: {e}"
            logger.error(f"Validation Error: {error_msg}")
            return json.dumps({"error": error_msg})

        if not all([pizza_type, size, delivery_address]):
            error_msg = "Missing required order details: pizza_type, size, and delivery_address are mandatory."
            logger.error(f"Validation Error: {error_msg}")
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
            with open(self.order_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(order_details) + '\n')
            logger.info(f"Order successfully saved to {self.order_file}")

            confirmation_message = {
                "status": "Order Placed Successfully",
                "confirmation": f"OK. Your order for {quantity_int} x {size} {pizza_type} pizza(s) "
                              f"{('with crust ' + order_details['crust_type']) if order_details['crust_type'] != 'Regular' else ''} "
                              f"{('and extra ' + ', '.join(order_details['extra_toppings']) + ' ') if order_details['extra_toppings'] else ''}"
                              f"to be delivered to '{delivery_address}' has been received.",
            }
            logger.info(f"Order confirmation: {confirmation_message['confirmation']}")
            return json.dumps(confirmation_message, indent=2)

        except IOError as e:
            logger.error(f"Error saving order to {self.order_file}: {e}")
            return json.dumps({"error": f"Failed to save the order due to a file system error: {str(e)}"})
        except Exception as e:
            logger.error(f"An unexpected error occurred during order placement: {e}")
            return json.dumps({"error": f"An unexpected error occurred: {str(e)}"})

    def get_tool_info(self) -> Dict[str, Any]:
        """Return the tool definition."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }