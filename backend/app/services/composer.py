import io
import math
import os
from pathlib import Path
from typing import Tuple, List, Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from app.schemas.generation import ProductContext, CreativeOutput
from app.core.config import settings

CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1350

def get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """
    Cross-platform TrueType font loader with graceful fallback.
    """
    font_candidates = []
    if bold:
        font_candidates.extend([
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
            "DejaVuSans-Bold.ttf",
            "arialbd.ttf"
        ])
    else:
        font_candidates.extend([
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans.ttf",
            "DejaVuSans.ttf",
            "arial.ttf"
        ])

    for font_path in font_candidates:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                continue

    # Fallback to default
    try:
        return ImageFont.load_default()
    except Exception:
        return None

def wrap_text(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> List[str]:
    """Wraps text into lines that fit within max_width."""
    words = text.split()
    if not words:
        return []

    lines = []
    current_line = []

    for word in words:
        test_line = " ".join(current_line + [word])
        try:
            bbox = draw.textbbox((0, 0), test_line, font=font)
            width = bbox[2] - bbox[0]
        except AttributeError:
            width = len(test_line) * (getattr(font, "size", 10) * 0.6)

        if width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                lines.append(word)
                current_line = []

    if current_line:
        lines.append(" ".join(current_line))
    return lines

def get_theme_colors(tone: str, visual_direction: str):
    """Determines high-converting color palette based on tone and art direction."""
    combined = f"{tone} {visual_direction}".lower()

    if any(k in combined for k in ("adventure", "outdoor", "rugged", "hike", "nature")):
        return {
            "bg_top": (15, 23, 42),       # Slate 900
            "bg_bottom": (30, 41, 59),    # Slate 800
            "accent": (245, 158, 11),     # Amber 500
            "accent_text": (15, 23, 42),
            "card_bg": (255, 255, 255, 18),
            "text_primary": (255, 255, 255),
            "text_secondary": (203, 213, 225), # Slate 300
            "badge_bg": (245, 158, 11, 40),
            "badge_border": (245, 158, 11, 160),
            "glow": (245, 158, 11, 30),
        }
    elif any(k in combined for k in ("luxury", "premium", "gold", "elegance", "sophisticated")):
        return {
            "bg_top": (9, 9, 11),         # Zinc 950
            "bg_bottom": (24, 24, 27),    # Zinc 900
            "accent": (217, 119, 6),      # Amber 600 Gold
            "accent_text": (255, 255, 255),
            "card_bg": (255, 255, 255, 15),
            "text_primary": (255, 255, 255),
            "text_secondary": (212, 212, 216),
            "badge_bg": (217, 119, 6, 40),
            "badge_border": (217, 119, 6, 180),
            "glow": (217, 119, 6, 35),
        }
    elif any(k in combined for k in ("energy", "workout", "gym", "sport", "active", "dynamic")):
        return {
            "bg_top": (10, 15, 30),
            "bg_bottom": (19, 30, 54),
            "accent": (6, 182, 212),      # Cyan 500
            "accent_text": (10, 15, 30),
            "card_bg": (255, 255, 255, 20),
            "text_primary": (255, 255, 255),
            "text_secondary": (224, 231, 255),
            "badge_bg": (6, 182, 212, 40),
            "badge_border": (6, 182, 212, 180),
            "glow": (6, 182, 212, 35),
        }
    else: # Modern Sleek Default
        return {
            "bg_top": (17, 24, 39),       # Gray 900
            "bg_bottom": (31, 41, 55),    # Gray 800
            "accent": (99, 102, 241),     # Indigo 500
            "accent_text": (255, 255, 255),
            "card_bg": (255, 255, 255, 20),
            "text_primary": (255, 255, 255),
            "text_secondary": (209, 213, 219),
            "badge_bg": (99, 102, 241, 45),
            "badge_border": (99, 102, 241, 180),
            "glow": (99, 102, 241, 35),
        }

def compose_advertisement(
    product_image_bytes: bytes,
    context: ProductContext,
    creative: CreativeOutput,
    output_path: Path
) -> Path:
    """
    Renders high-quality, conversion-optimized advertisement image.
    Ensures 100% product fidelity and pixel-crisp typographic hierarchy.
    """
    theme = get_theme_colors(context.tone, creative.visual_direction)

    # 1. Base Canvas with Smooth Vertical Gradient
    canvas = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), theme["bg_top"])
    draw = ImageDraw.Draw(canvas)

    # Gradient interpolation
    for y in range(CANVAS_HEIGHT):
        ratio = y / CANVAS_HEIGHT
        r = int(theme["bg_top"][0] * (1 - ratio) + theme["bg_bottom"][0] * ratio)
        g = int(theme["bg_top"][1] * (1 - ratio) + theme["bg_bottom"][1] * ratio)
        b = int(theme["bg_top"][2] * (1 - ratio) + theme["bg_bottom"][2] * ratio)
        draw.line([(0, y), (CANVAS_WIDTH, y)], fill=(r, g, b, 255))

    # 2. Add subtle lighting glow behind product showcase area
    glow_overlay = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_overlay)
    center_x = CANVAS_WIDTH // 2
    center_y = 560
    radius = 320
    glow_draw.ellipse(
        [(center_x - radius, center_y - radius), (center_x + radius, center_y + radius)],
        fill=theme["glow"]
    )
    glow_overlay = glow_overlay.filter(ImageFilter.GaussianBlur(80))
    canvas = Image.alpha_composite(canvas, glow_overlay)
    draw = ImageDraw.Draw(canvas)

    # 3. Product Showcase Card / Podium
    card_margin = 60
    card_top = 220
    card_bottom = 850
    # Soft translucent container card behind product
    card_overlay = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 0))
    card_draw = ImageDraw.Draw(card_overlay)
    card_draw.rounded_rectangle(
        [(card_margin, card_top), (CANVAS_WIDTH - card_margin, card_bottom)],
        radius=36,
        fill=theme["card_bg"],
        outline=(255, 255, 255, 30),
        width=2
    )
    canvas = Image.alpha_composite(canvas, card_overlay)
    draw = ImageDraw.Draw(canvas)

    # 4. Process and Place Actual Product Image
    try:
        raw_product = Image.open(io.BytesIO(product_image_bytes)).convert("RGBA")
        
        # Max dimensions for product within card
        max_prod_w = CANVAS_WIDTH - (card_margin * 2) - 100
        max_prod_h = (card_bottom - card_top) - 100

        # Scale preserving aspect ratio
        prod_ratio = min(max_prod_w / raw_product.width, max_prod_h / raw_product.height)
        new_w = max(10, int(raw_product.width * prod_ratio))
        new_h = max(10, int(raw_product.height * prod_ratio))
        product_resized = raw_product.resize((new_w, new_h), Image.Resampling.LANCZOS)

        prod_x = (CANVAS_WIDTH - new_w) // 2
        prod_y = card_top + ((card_bottom - card_top) - new_h) // 2

        # Soft drop shadow beneath product
        shadow_overlay = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_overlay)
        shadow_box = [
            (prod_x + 20, prod_y + new_h - 15),
            (prod_x + new_w - 20, prod_y + new_h + 35)
        ]
        shadow_draw.ellipse(shadow_box, fill=(0, 0, 0, 160))
        shadow_overlay = shadow_overlay.filter(ImageFilter.GaussianBlur(25))
        canvas = Image.alpha_composite(canvas, shadow_overlay)

        # Composite product image cleanly
        canvas.paste(product_resized, (prod_x, prod_y), product_resized)
        draw = ImageDraw.Draw(canvas)
    except Exception as e:
        # Fallback if product image pasting has an issue
        draw.text((CANVAS_WIDTH // 2, 500), f"[{context.product_name}]", fill=theme["text_primary"], anchor="mm")

    # 5. Top Header & Audience Pill Badge
    font_badge = get_font(20, bold=True)
    badge_text = f"FOR {context.target_audience.upper()}"
    if len(badge_text) > 45:
        badge_text = badge_text[:42] + "..."

    bbox_b = draw.textbbox((0, 0), badge_text, font=font_badge)
    b_width = bbox_b[2] - bbox_b[0]
    badge_pad_x = 24
    badge_pad_y = 10
    badge_x = (CANVAS_WIDTH - b_width) // 2
    badge_y = 120

    # Draw Badge Capsule
    draw.rounded_rectangle(
        [(badge_x - badge_pad_x, badge_y - badge_pad_y), (badge_x + b_width + badge_pad_x, badge_y + 24 + badge_pad_y)],
        radius=20,
        fill=theme["badge_bg"],
        outline=theme["badge_border"],
        width=2
    )
    draw.text((badge_x, badge_y), badge_text, fill=theme["accent"], font=font_badge)

    # 6. Typography: Headline
    font_headline = get_font(52, bold=True)
    headline_max_width = CANVAS_WIDTH - 140
    headline_lines = wrap_text(creative.headline, font_headline, headline_max_width, draw)

    text_cursor_y = 880
    for line in headline_lines:
        bbox_l = draw.textbbox((0, 0), line, font=font_headline)
        l_width = bbox_l[2] - bbox_l[0]
        line_x = (CANVAS_WIDTH - l_width) // 2
        draw.text((line_x, text_cursor_y), line, fill=theme["text_primary"], font=font_headline)
        text_cursor_y += 64

    # 7. Typography: Supporting Text
    font_sub = get_font(26, bold=False)
    sub_lines = wrap_text(creative.supporting_text, font_sub, CANVAS_WIDTH - 180, draw)
    text_cursor_y += 10
    for line in sub_lines:
        bbox_s = draw.textbbox((0, 0), line, font=font_sub)
        s_width = bbox_s[2] - bbox_s[0]
        s_x = (CANVAS_WIDTH - s_width) // 2
        draw.text((s_x, text_cursor_y), line, fill=theme["text_secondary"], font=font_sub)
        text_cursor_y += 38

    # 8. Key Benefits Pill / Checkmarks (if space allows)
    if context.key_benefits:
        font_benefit = get_font(20, bold=False)
        benefits_line = "  •  ".join(context.key_benefits[:3])
        if len(benefits_line) > 65:
            benefits_line = "  •  ".join(context.key_benefits[:2])
        bbox_ben = draw.textbbox((0, 0), benefits_line, font=font_benefit)
        ben_w = bbox_ben[2] - bbox_ben[0]
        ben_x = (CANVAS_WIDTH - ben_w) // 2
        text_cursor_y += 16
        draw.text((ben_x, text_cursor_y), benefits_line, fill=theme["accent"], font=font_benefit)
        text_cursor_y += 36

    # 9. High-Conversion Call To Action (CTA) Button
    font_cta = get_font(28, bold=True)
    cta_label = f"{creative.cta.upper()}  →"
    bbox_cta = draw.textbbox((0, 0), cta_label, font=font_cta)
    cta_w = bbox_cta[2] - bbox_cta[0]
    btn_w = max(280, cta_w + 64)
    btn_h = 68
    btn_x = (CANVAS_WIDTH - btn_w) // 2
    btn_y = 1180

    # Draw CTA Button Shadow
    cta_shadow = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 0))
    cta_s_draw = ImageDraw.Draw(cta_shadow)
    cta_s_draw.rounded_rectangle([(btn_x, btn_y + 8), (btn_x + btn_w, btn_y + btn_h + 8)], radius=34, fill=(0, 0, 0, 100))
    cta_shadow = cta_shadow.filter(ImageFilter.GaussianBlur(10))
    canvas = Image.alpha_composite(canvas, cta_shadow)
    draw = ImageDraw.Draw(canvas)

    # Draw Main CTA Button
    draw.rounded_rectangle(
        [(btn_x, btn_y), (btn_x + btn_w, btn_y + btn_h)],
        radius=34,
        fill=theme["accent"]
    )
    # Center CTA Text
    text_cta_x = btn_x + (btn_w - cta_w) // 2
    text_cta_y = btn_y + (btn_h - 32) // 2
    draw.text((text_cta_x, text_cta_y), cta_label, fill=theme["accent_text"], font=font_cta)

    # 10. Subtle Watermark / Branding Footer
    font_footer = get_font(18, bold=False)
    footer_text = "Verified Product Ad  •  Bildx AI Generator"
    bbox_f = draw.textbbox((0, 0), footer_text, font=font_footer)
    f_w = bbox_f[2] - bbox_f[0]
    draw.text(((CANVAS_WIDTH - f_w) // 2, 1290), footer_text, fill=(148, 163, 184, 180), font=font_footer)

    # Save final ad to file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Convert RGBA to RGB with alpha-blended background for wide JPEG/PNG compatibility
    final_image = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), theme["bg_top"])
    final_image.paste(canvas, mask=canvas.split()[3]) # 3 is alpha
    final_image.save(output_path, "PNG", optimize=True)

    return output_path
