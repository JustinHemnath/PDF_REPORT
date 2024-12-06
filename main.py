from utils.ca_model import model_data
import json

file = "ward_alangulam.json"
# file = "ward_vik.json"

with open(file, "r", encoding="utf-8") as f:
    response_data = json.load(f)

with open("utils/translation.json", "r", encoding="utf-8") as f:
    translation_data = json.load(f)
    

payload = {
    "lang": "ta",
    "trend": True,
    "party": [],
    "ac_no": 75,
    "pc_no": 38,
    "year": [
        "2024",
        "2021"
    ],
    "local_body": ['காணை தெற்கு', 'காணை மத்திய', 'காணை வடக்கு', 'கோலியனூர் மேற்கு', 'விக்கிரவாண்டி கிழக்கு', 'விக்கிரவாண்டி பேரூர்', 'விக்கிரவாண்டி மத்திய', 'விக்கிரவாண்டி மேற்கு'],
    "compare_type": "ac",
    "flag": None,
}
# payload = {
#     "lang": "ta",
#     "trend": True,
#     "party": [],
#     "ac_no": 223,
#     "pc_no": 38,
#     "year": [
#         "2024",
#         "2021"
#     ],
#     "local_body": [
#         "ஆலங்குளம் தெற்கு",
#         "ஆலங்குளம் பேரூர்",
#         "ஆழ்வார் குறிச்சி பேரூர்",
#         "கடையம் தெற்கு",
#         "கடையம் வடக்கு",
#         "கீழப்பாவூர் கிழக்கு",
#         "கீழப்பாவூர் பேரூர்",
#         "பாப்பாக்குடி",
#         "முக்கூடல் பேரூர்"
#     ],
#     "compare_type": "ward_vp",
#     "flag": None,
# }

# flags_list = [0, 3, 4]
flags_list = [0]

with open("ac_lb_mapping.json", "r", encoding="utf-8") as f:
    ac_lb_map = json.load(f)

lb_val_dict = {}
for key, value in ac_lb_map.items():
    lb_val_dict[key] = list(value.keys())

res = model_data(
    flags_list, response_data, payload, translation_data["ta"], total_lb_list=lb_val_dict[str(payload["ac_no"])]
)

# data = res["graph_data_pages_list"]
data = res["summary_data"]
# data = res

with open("modelled_data.json", "w", encoding="utf-8") as f:
    f.write(json.dumps(data, ensure_ascii=False))