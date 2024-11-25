import json 
import pandas as pd

with open("modelled_data2.json", "r", encoding="utf-8") as f:
    res = json.load(f)


class COMPARE_TYPE:
    AC = "ac"
    LOCAL_BODY = "local_body"
    BOOTH = "booth"
    LOCALITY = "locality"
    WARD = "ward_vp"


def apply_page_numbers(chapter_item, compare_type):
    INDEX_LB_KEY = {
        COMPARE_TYPE.BOOTH: "lb_name",
        COMPARE_TYPE.LOCAL_BODY: "local_body",
        COMPARE_TYPE.AC: "ac_name",
        COMPARE_TYPE.LOCALITY:  COMPARE_TYPE.LOCALITY,
        COMPARE_TYPE.WARD: COMPARE_TYPE.WARD,
    }
     
    # check if index data is present or empty, if empty, page nums cant be calculated hence return the original chapter back 
    if len(chapter_item[1]) == 0:
        return chapter_item
    else:
        current_trend = None
        current_index_item_value = None
        current_subtrend = None

        for lb_obj in chapter_item[2]:
            for table_page_obj in lb_obj["lb_index_data"]:
                for lb_name in table_page_obj["page_data"]["grouped_page_data"]:
                    lb_data = table_page_obj["page_data"]["grouped_page_data"][lb_name]["data"]
                    for ward in lb_data:
                        ward_data = lb_data[ward]["data"]
                        for trend in ward_data:
                            for index_item in ward_data[trend]["data"]:
                                last_page_found = False
                                initial_page_num = 0
                                last_page_num = 0

                                if not current_trend or not current_index_item_value or not current_subtrend:
                                    current_trend = index_item["trend"]
                                    current_index_item_value = index_item[INDEX_LB_KEY[compare_type]]
                                    current_subtrend = index_item["sub_trend"]

                                for lb_wise_object in chapter_item[2]:
                                        if not last_page_found:
                                            for graph_page_obj in lb_wise_object["lb_wise_graph_data"]:
                                                if not last_page_found:
                                                    hierarchy_pair_list = graph_page_obj["page_data"]
                                                    hierarchy_item = (
                                                        hierarchy_pair_list[1]
                                                        if len(hierarchy_pair_list) > 1
                                                        else hierarchy_pair_list[0]
                                                    )

                                                    if compare_type == COMPARE_TYPE.BOOTH:
                                                        belongs_to_index_item = (
                                                            hierarchy_item["parent_item_label"]
                                                            == current_index_item_value
                                                        )
                                                    elif compare_type == COMPARE_TYPE.LOCAL_BODY:
                                                        belongs_to_index_item = (
                                                            hierarchy_item["hierarchy_item_value"]
                                                            in current_index_item_value
                                                        )
                                                    elif compare_type == COMPARE_TYPE.AC:
                                                        belongs_to_index_item = (
                                                            hierarchy_item["hierarchy_item_value"]
                                                            == current_index_item_value
                                                        )
                                                    elif compare_type in [COMPARE_TYPE.WARD, COMPARE_TYPE.LOCALITY]:
                                                        belongs_to_index_item = (
                                                            (hierarchy_item["parent_hierarchy_name"] == index_item["lb_name"]) and
                                                            (hierarchy_item["parent_locality"] == current_index_item_value)
                                                        )
                                                    else:
                                                        belongs_to_index_item = (
                                                            hierarchy_item["hierarchy_item_value"]
                                                            in current_index_item_value
                                                        )

                                                    if not belongs_to_index_item:
                                                        if not initial_page_num:
                                                            continue
                                                        else:
                                                            last_page_num = int(graph_page_obj["page_number"]) - 1
                                                            last_page_found = True
                                                            # break
                                                    else:
                                                        if hierarchy_item["trend"] != current_trend:
                                                            if not initial_page_num:
                                                                continue
                                                            else:
                                                                last_page_num = int(graph_page_obj["page_number"]) - 1
                                                                last_page_found = True
                                                                # break
                                                        else:
                                                            if hierarchy_item["sub_trend"] != current_subtrend:
                                                                if not initial_page_num:
                                                                    continue
                                                                else:
                                                                    last_page_num = int(graph_page_obj["page_number"]) - 1
                                                                    last_page_found = True
                                                                    # break
                                                            else:
                                                                if not initial_page_num:
                                                                    initial_page_num = int(graph_page_obj["page_number"])
                                                                else:
                                                                    last_page_num = int(graph_page_obj["page_number"])
                                                                continue

                                page_no_list = ""
                                is_same_page = True if last_page_num - initial_page_num == 0 else False

                                if is_same_page:
                                    page_no_list = f"{last_page_num}"
                                else:
                                    if last_page_num == 0:
                                        page_no_list = f"{initial_page_num}"
                                    else:
                                        page_no_list = f"{initial_page_num} - {last_page_num}"

                                index_item["page_no_list"] = page_no_list
                                current_trend = None
                                current_index_item_value = None
                                current_subtrend = None
                                last_page_found = False

        return chapter_item


result = apply_page_numbers(res[0], COMPARE_TYPE.WARD)


with open("FINAL.json", "w", encoding="utf-8") as f:
    f.write(json.dumps(result[2][0]["lb_index_data"], ensure_ascii=False))
