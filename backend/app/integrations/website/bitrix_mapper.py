from __future__ import annotations

from typing import Any

from app.integrations.website.schemas import WebsiteProductDTO


def extract_bitrix_product(result: Any) -> dict[str, Any] | None:
    """Normalize catalog.product.get / list payload item to a product dict."""
    if not isinstance(result, dict):
        return None
    if "product" in result and isinstance(result["product"], dict):
        return result["product"]
    if "products" in result and isinstance(result["products"], list):
        return None
    if "id" in result or "name" in result:
        return result
    return None


def extract_bitrix_products(result: Any) -> list[dict[str, Any]]:
    if not isinstance(result, dict):
        return []
    products = result.get("products")
    if isinstance(products, list):
        return [item for item in products if isinstance(item, dict)]
    product = extract_bitrix_product(result)
    return [product] if product else []


def extract_bitrix_price(result: Any) -> dict[str, Any] | None:
    if not isinstance(result, dict):
        return None
    prices = result.get("prices")
    if isinstance(prices, list) and prices:
        first = prices[0]
        return first if isinstance(first, dict) else None
    return None


def map_bitrix_product_to_dto(
    product: dict[str, Any],
    price_row: dict[str, Any] | None = None,
) -> WebsiteProductDTO:
    """Map Bitrix catalog product (+ optional price row) to WebsiteProductDTO.

    Identifiers:
    - sku ← code (primary external id)
    - id ← Bitrix id
    - xmlId stored in characteristics when present
    """
    bitrix_id = product.get("id")
    code = _as_text(product.get("code"))
    xml_id = _as_text(product.get("xmlId"))
    name = _as_text(product.get("name")) or code or (str(bitrix_id) if bitrix_id is not None else "")
    sku = code or xml_id or (str(bitrix_id) if bitrix_id is not None else "")

    description = _as_text(product.get("previewText")) or _as_text(product.get("detailText"))
    category_id = product.get("iblockSectionId")
    characteristics = _extract_characteristics(product)
    if xml_id:
        characteristics["xmlId"] = xml_id
    if code:
        characteristics["code"] = code
    if bitrix_id is not None:
        characteristics["bitrixId"] = str(bitrix_id)

    availability = _map_availability(product.get("available"))
    stock_qty = _as_int(product.get("quantity"))

    price: float | None = None
    currency: str | None = None
    if price_row:
        price = _as_float(price_row.get("price"))
        currency = _as_text(price_row.get("currency")) or None

    payload: dict[str, Any] = {
        "sku": sku,
        "name": name,
    }
    if bitrix_id is not None:
        payload["id"] = str(bitrix_id)
    if description:
        payload["description"] = description
    if category_id is not None:
        payload["category_id"] = str(category_id)
    if price is not None:
        payload["price"] = price
    if currency:
        payload["currency"] = currency
    if availability:
        payload["availability_status"] = availability
    if stock_qty is not None:
        payload["stock_qty"] = stock_qty
    if characteristics:
        payload["characteristics"] = characteristics

    return WebsiteProductDTO.model_validate(payload)


def _extract_characteristics(product: dict[str, Any]) -> dict[str, str]:
    characteristics: dict[str, str] = {}
    for key, value in product.items():
        if not str(key).startswith("property"):
            continue
        if isinstance(value, dict):
            label = _as_text(value.get("valueEnum")) or _as_text(value.get("value"))
            if label:
                characteristics[str(key)] = label
        elif value not in (None, "", "N"):
            text = _as_text(value)
            if text and text != "N":
                characteristics[str(key)] = text
    return characteristics


def _map_availability(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().upper()
    if text == "Y":
        return "in_stock"
    if text == "N":
        return "out_of_stock"
    return None


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
