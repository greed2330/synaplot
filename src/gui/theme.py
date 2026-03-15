"""Central design system — all colors, fonts, and dimensions."""

# --- Colors ---
BG          = "#111111"   # App root background
SURFACE     = "#1C1C1C"   # Panel / card background
SURFACE2    = "#252525"   # Slightly elevated (input bg, hover)
SURFACE3    = "#2E2E2E"   # Most elevated (active item)
BORDER      = "#2F2F2F"   # Subtle border
PRIMARY     = "#3B82F6"   # Blue — primary action
PRIMARY_H   = "#2563EB"   # Primary hover
TEXT        = "#EBEBEB"   # Primary text
TEXT2       = "#909090"   # Secondary text
TEXT3       = "#555555"   # Muted / placeholder
SUCCESS     = "#22C55E"
WARNING     = "#E6993A"
DANGER      = "#EF4444"
DANGER_H    = "#DC2626"

# --- Typography (tuples: family, size[, weight]) ---
FONT_APP    = ("Malgun Gothic", 14, "bold")    # App title
FONT_H1     = ("Malgun Gothic", 17, "bold")    # Screen heading
FONT_H2     = ("Malgun Gothic", 13, "bold")    # Section heading
FONT_BODY   = ("Malgun Gothic", 13)            # Default body
FONT_SMALL  = ("Malgun Gothic", 11)            # Caption / helper
FONT_MONO   = ("Consolas", 12)                 # Code / file paths

# --- Dimensions ---
RADIUS_LG   = 10   # Large card
RADIUS_MD   = 7    # Button, input
RADIUS_SM   = 4    # Badge, tag

TOPBAR_H    = 50
SIDEBAR_L   = 200  # Left sidebar width
SIDEBAR_R   = 250  # Right sidebar width

PAD         = 16   # Standard padding
PAD_SM      = 8


# --- Helpers ---
def btn_primary(extra=None):
    d = dict(fg_color=PRIMARY, hover_color=PRIMARY_H, corner_radius=RADIUS_MD,
             text_color=TEXT, font=FONT_BODY)
    if extra:
        d.update(extra)
    return d


def btn_ghost(extra=None):
    d = dict(fg_color="transparent", hover_color=SURFACE3, corner_radius=RADIUS_MD,
             text_color=TEXT2, font=FONT_BODY)
    if extra:
        d.update(extra)
    return d


def btn_danger(extra=None):
    d = dict(fg_color=DANGER, hover_color=DANGER_H, corner_radius=RADIUS_MD,
             text_color=TEXT, font=FONT_BODY)
    if extra:
        d.update(extra)
    return d


def card(extra=None):
    d = dict(fg_color=SURFACE, corner_radius=RADIUS_LG, border_width=1, border_color=BORDER)
    if extra:
        d.update(extra)
    return d


def input_style(extra=None):
    d = dict(fg_color=SURFACE2, border_color=BORDER, border_width=1,
             corner_radius=RADIUS_MD, text_color=TEXT,
             placeholder_text_color=TEXT3, font=FONT_BODY)
    if extra:
        d.update(extra)
    return d
