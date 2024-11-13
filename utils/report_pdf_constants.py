dmk_red_color = "#d6382d"


PARTY_WISE_COLORS = {
    "DMK": "#e82b1e",
    "VCK": "#0961b3",
    "BJP": "#e87007",
    "AIADMK": "#215e1b",
    "PMK": "#d9ce09",
    "NTK": "#141210",
    "Others": "#b3b4b5",
    "IND" : "#4c516d",
    "MDMK" :"#950606",
    "MNM" : "#d6204e",
    "IND" : "#4c516d",
    "PT"  :  "#66bd63",
    "CPI" : "#f04545",
    "CPIM" : "#ad4040",
    "INC" : "#5fb2d9",
    "IUML" : "#19d776",
    "DMDK":"#FDDA0D",
    "AMMK": "#234735"
}

COLORS = [
    "ca_graph_component_pink_bg",
    "ca_graph_component_blue_bg",
    "ca_graph_component_green_bg",
    "ca_graph_component_indigo_bg",
]


class COMPARE_TYPE:
    AC = "ac"
    LOCAL_BODY = "local_body"
    BOOTH = "booth"
    LOCALITY = "locality"
    WARD = "ward_vp"

class WARD_VP_TYPE:
    WARD = "ward"
    VP = "vp"

COMPARE_TYPE_VALUES = [
    {"label": "AC", "value": COMPARE_TYPE.AC},
    {"label": "Local body", "value": COMPARE_TYPE.LOCAL_BODY},
    {"label": "Booth", "value": COMPARE_TYPE.BOOTH},
    {"label": "Locality", "value": COMPARE_TYPE.LOCALITY},
    {"label": "Ward/Village panchayat", "value": COMPARE_TYPE.WARD},
]

class DIFFERENTIATION_TYPE:
    AND = "and"
    OR = "or"