"""
Orders domain service: query, update address, cancel order.
"""
from typing import Optional, Dict, Any, List
import json
from services.db import get_connection

def get_order(order_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["items"] = json.loads(d["items_json"])
    return d

def get_customer_orders(customer_id: str, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE customer_id = ? ORDER BY order_date DESC", (customer_id,))
    rows = cursor.fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["items"] = json.loads(d["items_json"])
        result.append(d)
    return result

def update_shipping_address(order_id: str, new_address: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    order = get_order(order_id, db_path)
    if not order:
        return {"success": False, "error": f"Order {order_id} not found."}
    
    if order["status"] in ["shipped", "delivered"]:
        return {
            "success": False, 
            "error": f"Cannot change shipping address: order is already '{order['status']}'. Policy requires order to be in 'pending' or 'processing' status."
        }
    
    conn = get_connection(db_path)
    with conn:
        conn.execute("UPDATE orders SET shipping_address = ? WHERE id = ?", (new_address, order_id))
    conn.close()
    return {"success": True, "order_id": order_id, "new_address": new_address, "status": order["status"]}

def cancel_order(order_id: str, reason: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    order = get_order(order_id, db_path)
    if not order:
        return {"success": False, "error": f"Order {order_id} not found."}
    
    if order["status"] in ["shipped", "delivered"]:
        return {
            "success": False, 
            "error": f"Cannot cancel order: order is already '{order['status']}'. Return process must be initiated instead."
        }
    
    if order["status"] == "cancelled":
        return {"success": True, "message": f"Order {order_id} is already cancelled."}
    
    conn = get_connection(db_path)
    with conn:
        conn.execute("UPDATE orders SET status = 'cancelled' WHERE id = ?", (order_id,))
    conn.close()
    return {"success": True, "order_id": order_id, "status": "cancelled", "reason": reason}
