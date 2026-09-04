from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any, cast


def create_qr(
    link: str,
    size: int = 10,
    background: str = "white",
    color: str = "black",
    border: int = 4,
) -> BytesIO:
    """Render a branded PNG QR code.

    Pillow and qrcode are imported only when this function is called so URL,
    transfer, and RPC users do not pay the import or installation cost.
    """

    try:
        import qrcode
        from PIL import Image
        from qrcode.image.styles.moduledrawers.pil import RoundedModuleDrawer
    except ImportError as error:  # pragma: no cover - depends on installation extra
        raise ImportError(
            "QR generation requires the optional dependencies; "
            "install them with 'pip install solathon[qr]'"
        ) from error
    if not isinstance(link, str) or not link:
        raise ValueError("link must be a non-empty string")
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        raise ValueError("size must be a positive integer")
    if not isinstance(border, int) or isinstance(border, bool) or border < 0:
        raise ValueError("border must be a non-negative integer")

    qr = qrcode.QRCode(
        box_size=size,
        border=border,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
    )
    qr.add_data(link)
    qr.make(fit=True)
    image = cast(
        Any,
        qr.make_image(
            fill_color=color,
            back_color=background,
            module_drawer=RoundedModuleDrawer(),
        ),
    ).convert("RGB")

    logo_path = Path(__file__).with_name("qr-logo.png")
    with Image.open(logo_path) as source_logo:
        logo_width = int(image.width * 0.2)
        logo_height = int(source_logo.height * logo_width / source_logo.width)
        logo = source_logo.convert("RGBA").resize((logo_width, logo_height))
    position = (
        (image.width - logo.width) // 2,
        (image.height - logo.height) // 2,
    )
    output = BytesIO()
    try:
        image.paste(logo, position, logo)
        image.save(output, format="PNG")
    finally:
        logo.close()
        image.close()
    output.seek(0)
    return output
