from .extra_utils import time_it
import math
import json
import os
import json
import os
import math
import time
from typing import Dict, List, Union
from .extra_utils import time_it
from .report_pdf_constants import (
    COLORS,
    PARTY_WISE_COLORS,
    dmk_red_color,
)
import plotly.express as px
import pandas as pd
from .extra_utils import indian_number_format
from .report_pdf_constants import COMPARE_TYPE, DIFFERENTIATION_TYPE, WARD_VP_TYPE
from itertools import groupby
import logging
import concurrent.futures


def group_graph_data(
    payload: Dict,
    graph_main_data,
    extra_metadata,
    translation_data,
    modified_response_header_data,
    compare_type,
    lang,
    index_data_pages,
    trends_grouped_data,
    flag: int,
    differentiation_type: str,
    year_for_or_filter: Union[str, None],
    ac_number_to_name
):
    TREND = extra_metadata["TRENDS"]
    YEARS_LIST = extra_metadata["YEARS_LIST"]

    flattened_graph_main_data = []

    if compare_type == COMPARE_TYPE.BOOTH:
        for item_key in graph_main_data:
            for key, value in graph_main_data[item_key].items():
                satisfies_flag = is_satisfies_flag(
                    flag, value, payload, differentiation_type, year_for_or_filter
                )

                if satisfies_flag:
                    flattened_graph_main_data.append(
                            {
                                **value,
                                "hierarchy_item_value": key,
                                "parent_hierarchy_name": item_key,
                            }
                        )
                else:
                    continue

    elif compare_type == COMPARE_TYPE.LOCAL_BODY:
        for key, value in graph_main_data.items():
            flattened_graph_main_data.append(
                {
                    **value,
                    "hierarchy_item_value": key,
                    "parent_hierarchy_name": None,
                }
            )
    elif compare_type == COMPARE_TYPE.AC:  ## compare type is AC
        flattened_graph_main_data = [
            {
                **graph_main_data,
                "hierarchy_item_value": ac_number_to_name[lang][
                    str(extra_metadata["AC_NO"])
                ],
                "parent_hierarchy_name": None,
            }
        ]
    else:  ## compare type is locality or ward_vp
        for lb_item_key in graph_main_data:
            localities_map = graph_main_data[lb_item_key].items()
            for locality_key, booth_value in localities_map:
                for booth_key, booth_item in booth_value.items():

                    satisfies_flag = is_satisfies_flag(
                        flag, booth_item, payload, differentiation_type, year_for_or_filter
                    )

                    if satisfies_flag:
                        flattened_graph_main_data.append(
                                {
                                    **booth_item,
                                    "hierarchy_item_value": booth_key,
                                    "parent_hierarchy_name": lb_item_key,
                                    "parent_locality": locality_key,
                                }
                            )
                    else:
                        continue

    ## filter index items by booths present
    filtered_index_data_pages = remove_index_items_by_booths_present(
        flag=flag,
        compare_type=compare_type,
        index_data=index_data_pages,
        flattened_graph_main_data=flattened_graph_main_data,
    )

    # gets total booths per subtrend dict to display in each booth's header
    booths_per_subtrend_dict = get_subtrendwise_total_booth_count_from_index_data(filtered_index_data_pages, compare_type)
    

    parent_data_length = len(flattened_graph_main_data)
    MAIN_GRAPH_DATA = [get_new_lb_graph_data_item(lb_name=flattened_graph_main_data[0]["parent_hierarchy_name"])] if len(flattened_graph_main_data) != 0 else []
    lb_wise_graph_data = []
    hierarchy_pair_list = []

    for idx, value in enumerate(flattened_graph_main_data):
        hierarchy_list_is_empty = len(hierarchy_pair_list) == 0
        current_hierarchy_item = get_modifed_hierarchy_item(
            value,
            extra_metadata,
            modified_response_header_data,
            compare_type,
            translation_data,
            TREND,
            YEARS_LIST,
            add_sub_trend_data=True if hierarchy_list_is_empty else False,
            trends_grouped_data=trends_grouped_data,
            filtered_index_data_pages=filtered_index_data_pages,
            flag=flag,
            booths_per_subtrend_dict=booths_per_subtrend_dict
        )

        if hierarchy_list_is_empty:
            if MAIN_GRAPH_DATA[-1]["lb_name"] != current_hierarchy_item["parent_hierarchy_name"]:
                MAIN_GRAPH_DATA.append(get_new_lb_graph_data_item(lb_name=current_hierarchy_item["parent_hierarchy_name"]))
                hierarchy_pair_list.append(current_hierarchy_item)

            else:
                hierarchy_pair_list.append(current_hierarchy_item)

            # if last hierarchy item
            if parent_data_length == idx + 1:
                MAIN_GRAPH_DATA[-1]["lb_wise_graph_data"].append(get_page_obj("", hierarchy_pair_list))
        else:
            if compare_type in [COMPARE_TYPE.LOCALITY, COMPARE_TYPE.WARD]:
                ## check for local body equality if compare type is local body
                if hierarchy_pair_list[0]["parent_hierarchy_name"] != current_hierarchy_item["parent_hierarchy_name"]:
                    MAIN_GRAPH_DATA[-1]["lb_wise_graph_data"].append(get_page_obj("", hierarchy_pair_list))
                    MAIN_GRAPH_DATA.append(get_new_lb_graph_data_item(lb_name=current_hierarchy_item["parent_hierarchy_name"]))
                    hierarchy_pair_list = []
                    hierarchy_pair_list.append(current_hierarchy_item)

                    if parent_data_length == idx + 1:
                        MAIN_GRAPH_DATA[-1]["lb_wise_graph_data"].append(get_page_obj("", hierarchy_pair_list))
                        hierarchy_pair_list = []
                
                else:
                    ## check for locality/wardvp equality if compare type is locality or ward_vp
                    if hierarchy_pair_list[0]["parent_locality"] != current_hierarchy_item["parent_locality"]:
                        MAIN_GRAPH_DATA[-1]["lb_wise_graph_data"].append(get_page_obj("", hierarchy_pair_list))
                        hierarchy_pair_list = []
                        hierarchy_pair_list.append(current_hierarchy_item)

                        if parent_data_length == idx + 1:
                            MAIN_GRAPH_DATA[-1]["lb_wise_graph_data"].append(get_page_obj("", hierarchy_pair_list))
                            hierarchy_pair_list = []
                        continue
                    else:
                        ### check for trend equality
                        if hierarchy_pair_list[0]["trend"] != current_hierarchy_item["trend"]:
                            MAIN_GRAPH_DATA[-1]["lb_wise_graph_data"].append(get_page_obj("", hierarchy_pair_list))
                            hierarchy_pair_list = []
                            hierarchy_pair_list.append(current_hierarchy_item)
                            
                            if parent_data_length == idx + 1:
                                MAIN_GRAPH_DATA[-1]["lb_wise_graph_data"].append(get_page_obj("", hierarchy_pair_list))
                                hierarchy_pair_list = []
                            continue
                        else:
                            ### check for sub trend equality
                            if hierarchy_pair_list[0]["sub_trend"] != current_hierarchy_item["sub_trend"]:
                                MAIN_GRAPH_DATA[-1]["lb_wise_graph_data"].append(get_page_obj("", hierarchy_pair_list))
                                hierarchy_pair_list = []
                                hierarchy_pair_list.append(current_hierarchy_item)
                                
                                if parent_data_length == idx + 1:
                                    MAIN_GRAPH_DATA[-1]["lb_wise_graph_data"].append(get_page_obj("", hierarchy_pair_list))
                                    hierarchy_pair_list = []
                                continue
                            else:
                                hierarchy_pair_list.append(current_hierarchy_item)
                                MAIN_GRAPH_DATA[-1]["lb_wise_graph_data"].append(get_page_obj("", hierarchy_pair_list))
                                hierarchy_pair_list = []
                                continue

            else:
                if hierarchy_pair_list[0]["parent_hierarchy_name"] != current_hierarchy_item["parent_hierarchy_name"]:
                    lb_wise_graph_data.append(get_page_obj("", hierarchy_pair_list))
                    hierarchy_pair_list = []
                    hierarchy_pair_list.append(current_hierarchy_item)
                    lb_wise_graph_data.append(get_page_obj("", hierarchy_pair_list))
                    hierarchy_pair_list = []
                    continue
                ## check for trend equality
                elif hierarchy_pair_list[0]["trend"] == current_hierarchy_item["trend"]:

                    ## check for subtrend equality
                    if (
                        hierarchy_pair_list[0]["sub_trend"]
                        == current_hierarchy_item["sub_trend"]
                    ):
                        hierarchy_pair_list.append(current_hierarchy_item)
                        lb_wise_graph_data.append(get_page_obj("", hierarchy_pair_list))
                        hierarchy_pair_list = []
                    else:
                        ## subtrends are different so add the current item to a new page
                        lb_wise_graph_data.append(get_page_obj("", hierarchy_pair_list))
                        hierarchy_pair_list = []
                        hierarchy_pair_list.append(current_hierarchy_item)

                        if idx + 1 == parent_data_length:
                            lb_wise_graph_data.append(get_page_obj("", hierarchy_pair_list))
                            break
                else:
                    lb_wise_graph_data.append(get_page_obj("", hierarchy_pair_list))
                    hierarchy_pair_list = []
                    hierarchy_pair_list.append(current_hierarchy_item)

                    # if the current hierarchy item is the last item of graph data, append it to lb_wise_graph_data and break the loop
                    # as there are no more items to iterate over
                    if idx + 1 == parent_data_length:
                        lb_wise_graph_data.append(get_page_obj("", hierarchy_pair_list))
                        break

    return MAIN_GRAPH_DATA, filtered_index_data_pages


def remove_index_items_by_booths_present(
    flag: int, compare_type, index_data: List, flattened_graph_main_data: List
) -> List:

    if flag == 0:
        return index_data
    else:
        filtered_index_data = list()
        
        for index_item in index_data:
            new_index_booth_count = []

            for booth in index_item["booth_list_expanded"]:
                # loop through each graph item and check if the booth is there
                for graph_item in flattened_graph_main_data:
                    if int(graph_item["hierarchy_item_value"]) == booth:
                        new_index_booth_count.append(str(booth))
                        break
                
            if len(new_index_booth_count) != 0:
                new_index_item = {**index_item}
                new_index_item["booth_list_expanded"] = new_index_booth_count
                new_index_item["booth_count"] = len(new_index_booth_count)
                filtered_index_data.append(new_index_item)
 
        # add s no to index items after filtering
        for idx, index_item in enumerate(filtered_index_data):
            index_item["s_no"] = idx + 1

        return filtered_index_data

def get_subtrendwise_total_booth_count_from_index_data(index_data: List, compare_type: str) -> Dict:
    if compare_type in [COMPARE_TYPE.LOCALITY, COMPARE_TYPE.WARD]:
        
        final_dict = dict()
        for index_item in index_data:
            current_local_body = index_item["lb_name"]
            current_locality = index_item[compare_type]
            current_trend = index_item["trend"]
            current_sub_trend = index_item["sub_trend"]
            current_booth_count = index_item["booth_count"]
            current_booth_list = index_item["booth_list_expanded"]

            if not final_dict.get(current_local_body, None):
                final_dict[current_local_body] = {
                    current_locality: {
                        current_trend: {
                            "count": current_booth_count,
                            "items": {
                                current_sub_trend: {
                                "count": current_booth_count,
                                "items": current_booth_list,
                                }
                            }
                        }
                    }
                }
            else:
                if not final_dict[current_local_body].get(current_locality, None):
                    final_dict[current_local_body] = {
                        **final_dict[current_local_body],
                        current_locality: {
                            current_trend: {
                                "count": current_booth_count,
                                "items": {
                                    current_sub_trend: {
                                    "count": current_booth_count,
                                    "items": current_booth_list,
                                    }
                                }
                            }
                        }
                    }
                else:
                    if not final_dict[current_local_body][current_locality].get(current_trend, None):
                        final_dict[current_local_body] = {
                            **final_dict[current_local_body],
                            current_locality: {
                                **final_dict[current_local_body][current_locality],
                                current_trend: {
                                    "count": current_booth_count,
                                    "items": {
                                        current_sub_trend: {
                                        "count": current_booth_count,
                                        "items": current_booth_list,
                                        }
                                    }
                                }
                            }
                        }
                    else:
                        if not final_dict[current_local_body][current_locality][current_trend].get(current_sub_trend, None):
                            final_dict[current_local_body] = {
                                **final_dict[current_local_body],
                                current_locality: {
                                    **final_dict[current_local_body][current_locality],
                                    current_trend: {
                                        "count": current_booth_count + final_dict[current_local_body][current_locality][current_trend]["count"],
                                        "items": {
                                            **final_dict[current_local_body][current_locality][current_trend]["items"],
                                                current_sub_trend: {
                                                "count": current_booth_count,
                                                "items": current_booth_list,
                                                }
                                            }
                                    }
                                }
                            }
                        else:
                            final_dict[current_local_body] = {
                                **final_dict[current_local_body],
                                current_locality: {
                                    **final_dict[current_local_body][current_locality],
                                    current_trend: {
                                        "count": current_booth_count + final_dict[current_local_body][current_locality][current_trend]["count"],
                                        "items": {
                                            **final_dict[current_local_body][current_locality][current_trend]["items"],
                                                current_sub_trend: {
                                                "count": current_booth_count + final_dict[current_local_body][current_locality][current_trend][current_sub_trend]["count"],
                                                "items": current_booth_list + final_dict[current_local_body][current_locality][current_trend][current_sub_trend]["items"],
                                                }
                                            }
                                    }
                                }
                            }

        return final_dict

    else:
        lb_wise_grouped = groupby(index_data, lambda x: x["lb_name"])

        final_grouped_dict = dict()
        for lb_key, lb_value in lb_wise_grouped:
            lb_wise_grouped_list = list(lb_value)
            trend_wise_grouped = groupby(lb_wise_grouped_list, lambda x: x["trend"])

            trend_wise_grouped_dict = dict()
            for trend_key, trend_value in trend_wise_grouped:
                trend_value_list = list(trend_value)
                subtrend_wise_grouped = groupby(trend_value_list, lambda x: x["sub_trend"])

                subtrend_wise_grouped_dict = dict()
                total_booths_per_trend = 0
                for subtrend_key, subtrend_value in subtrend_wise_grouped:
                    subtrend_value_list = list(subtrend_value)
                    subtrend_wise_grouped_dict[subtrend_key] = {
                            "count": subtrend_value_list[0]["booth_count"],
                            "items": subtrend_value_list[0]["booth_list_expanded"]
                        }

                    total_booths_per_trend += subtrend_value_list[0]["booth_count"]
                        
                trend_wise_grouped_dict[trend_key] = {
                    "count": total_booths_per_trend, 
                    "items": subtrend_wise_grouped_dict
                }


            final_grouped_dict[lb_key] = trend_wise_grouped_dict

        return final_grouped_dict



def convert_graph_data_into_fig(graph_data, translation_data: Dict):
    graph_color = "#e3e2e1"

    x_axis = graph_data["x"]
    y_axis = graph_data["y"]

    parties = translation_data["parties"]
    votes = translation_data["votes"]

    df = pd.DataFrame({parties: x_axis, votes: y_axis})
    figure = px.bar(df, x=parties, y=votes, text_auto=True)

    figure.update_layout(
        {
            "paper_bgcolor": graph_color,
            "plot_bgcolor": graph_color,
            "font": {
                "size": 9,
                "family": "'Inter', 'sans serif'",
            },
            "showlegend": False,
            "height": 160,
            "width": 245,
            "margin": {
                "b": 0,
                "l": 0,
                "r": 0,
                "t": 10,
            },
        },
    )

    if x_axis == None:
        marker_color = [dmk_red_color]
    else:
        marker_color = [PARTY_WISE_COLORS.get(party, dmk_red_color) if len(party.split(" ")) == 1 else PARTY_WISE_COLORS.get("IND") for party in x_axis]

    figure.update_traces(marker_color=marker_color, textposition="auto")

    return figure.to_html(
        full_html=False, config={"displayModeBar": False}, include_plotlyjs=False
    )


def get_page_obj(pg_no, page_data) -> Dict:
    return {"page_number": str(pg_no), "page_data": page_data}


def get_modifed_hierarchy_item(
    value,
    extra_metadata,
    modified_response_header_data,
    compare_type,
    translation_data,
    TREND,
    YEARS_LIST,
    add_sub_trend_data: bool,
    trends_grouped_data: Dict,
    filtered_index_data_pages: List,
    flag: int,
    booths_per_subtrend_dict: Dict,
):
    # get booth's header data
    created_header_items = get_graph_item_headers(
        compare_type,
        trend=TREND,
        translation_data=translation_data,
        hierarchy_item_data=value,
        extra_metadata=extra_metadata,
        modified_response_header_data=modified_response_header_data,
        trends_grouped_data=trends_grouped_data,
    )

    YEAR_WISE_DATA = []

    # pushes yearwise data
    for index, year in enumerate(YEARS_LIST):
        year_value = value.get(year)
        TREND_LIST = list(created_header_items["header_data"]["trend"])
        new_year_data = {
            **year_value,
            "fig": convert_graph_data_into_fig(graph_data=year_value["graph_data"], translation_data=translation_data),
            "year": year,
            "trend": TREND_LIST[index],
        }

        YEAR_WISE_DATA.append(new_year_data)

    ## add subtrend list and trends list to hierarchy item
    sub_trend_booth_list = None
    trend_booth_list = None

    # trends

    # subtrends total trends data
    if compare_type == COMPARE_TYPE.BOOTH:
        subtrends_booth_count_data = booths_per_subtrend_dict[value["parent_hierarchy_name"]][value["trend"]]
    elif compare_type in [COMPARE_TYPE.LOCALITY, COMPARE_TYPE.WARD]:
        subtrends_booth_count_data = booths_per_subtrend_dict[value["parent_hierarchy_name"]][value["parent_locality"]][value["trend"]]
    else:
        subtrends_booth_count_data = booths_per_subtrend_dict[value["parent_hierarchy_name"]][value["trend"]]
    
    if flag == 0:
        # trends
        if compare_type == COMPARE_TYPE.BOOTH:
            trend_booth_list = trends_grouped_data[value["parent_hierarchy_name"]][
                    value["trend"]
                ]
        elif compare_type in [COMPARE_TYPE.LOCALITY, COMPARE_TYPE.WARD]:
             trend_booth_list = trends_grouped_data[value["parent_hierarchy_name"]][value["parent_locality"]][
                    value["trend"]
                ]
        else:
            trend_booth_list = trends_grouped_data[value["parent_hierarchy_name"]][
                    value["trend"]
                ]
            
        # subtrends
        for item in modified_response_header_data:
            if int(value["hierarchy_item_value"]) in item["sub_trend_booth_list_expanded"]:
                sub_trend_booth_list = item["sub_trend_booth_list_expanded"]
                break
    else:
        # if flag is 3 or 4, get subtrend list from filtered index data: 
        # # trends
        matching_trend_rows_list = []
        for filt_index_row in filtered_index_data_pages:
            if compare_type == COMPARE_TYPE.BOOTH:
                satifies_condition =  (filt_index_row["lb_name"] == value["parent_hierarchy_name"]) and (filt_index_row["trend"] == value["trend"])
            elif compare_type in [COMPARE_TYPE.LOCALITY, COMPARE_TYPE.WARD]:
                satifies_condition =  (filt_index_row["lb_name"] == value["parent_hierarchy_name"] and filt_index_row[compare_type] == value["parent_locality"]) and (filt_index_row["trend"] == value["trend"])
            else:    
                satifies_condition =  (filt_index_row["lb_name"] == value["parent_hierarchy_name"]) and (filt_index_row["trend"] == value["trend"])

            if satifies_condition:
                matching_trend_rows_list.append(filt_index_row)

        new_trend_booth_list = []
        for matching_idx_row in matching_trend_rows_list:
            new_trend_booth_list.extend(matching_idx_row["booth_list_expanded"])

            # subtrends 
            if matching_idx_row["sub_trend"] == value["sub_trend"]:
                sub_trend_booth_list = matching_idx_row["booth_list_expanded"]

        # trends 
        new_trend_booth_list = list(set(new_trend_booth_list))
        trend_booth_list = new_trend_booth_list

    return {
        **value,
        "hierarchy_item_value": value["hierarchy_item_value"],
        "year_wise_data": YEAR_WISE_DATA,
        "header": created_header_items["header"],
        "header_data": created_header_items["header_data"],
        "label_value_title": created_header_items["label_value_title"],
        "parent_item_label": value["parent_hierarchy_name"],
        "sub_trend_booth_list": {
            "count": len(sub_trend_booth_list) if sub_trend_booth_list else 0,
            "items": sub_trend_booth_list,
        },
        "trend_booth_list": {
            "count": len(trend_booth_list) if trend_booth_list else 0,
            "items": trend_booth_list
        },
        "subtrends_booth_count_data" : subtrends_booth_count_data
    }



def get_graph_item_headers(
    compare_type,
    trend: bool,
    translation_data: Dict,
    hierarchy_item_data: Dict,
    extra_metadata: Dict,
    modified_response_header_data: List,
    trends_grouped_data: Dict,
) -> Dict:
    top_headers = list()
    bottom_headers = list()
    AC_NO = extra_metadata["AC_NO"]
    AC_NAME = extra_metadata["AC_NAME"]

    header_data = get_matching_header_data(
        compare_type,
        modified_response_header_data,
        hierarchy_item_data,
        trend,
    )

    ##
    total_votes_count = str(indian_number_format(header_data["ac_total_votes"]))

    # trend_count = len(
    #     trends_grouped_data[hierarchy_item_data["parent_hierarchy_name"]][
    #         hierarchy_item_data["trend"]
    #     ]
    # )

    bh_1 = "{} {}: {}".format(
        AC_NAME, translation_data["total_voters_count"], total_votes_count
    )

    if compare_type == COMPARE_TYPE.BOOTH:
        lb_total_votes = str(indian_number_format(header_data["lb_total_votes"]))
        th_1 = "{}. {} - {}".format(
            AC_NO,
            AC_NAME,
            header_data["local_body"],
        )
        # th_2 = "({})".format(trend_count) if trend else ""
        # th_3 = "({})".format(header_data["sub_trend_booth_count"]) if trend else ""
        ## dummy string because header component html needs two index
        bh_2 = "{} {}: {}".format(
            header_data["lb_type"], translation_data["total_parts"], header_data["lb_booth_count"]
        )
        bh_3 = "{} {}: {}".format(
            header_data["lb_type"],
            translation_data["union_total_voters_count"],
            lb_total_votes,
        )
        bottom_headers = [bh_1, bh_2, bh_3]
        label_value_title = [translation_data["booth_no_short"], translation_data["label_value_title"]]
    elif compare_type == COMPARE_TYPE.LOCAL_BODY:
        th_1 = "{}. {} {}".format(
            AC_NO, AC_NAME, translation_data["local_body_structures"]
        )
        # th_2 = "({})".format(trend_count) if trend else ""
        # th_3 = "- ({})".format(header_data["total_lb_count"]) if trend else ""
        bh_2 = "{}: {}".format(
            translation_data["total_lbs"], header_data["total_lb_count"]
        )
        bottom_headers = [bh_1, bh_2]
        label_value_title = [translation_data["local_body"], translation_data["label_value_title"]]
    elif compare_type == COMPARE_TYPE.AC:
        th_1 = "{}. {} {} - ".format(AC_NO, AC_NAME, translation_data["ac"])
        # th_2 = "({})".format(trend_count) if trend else ""
        # th_3 = "- ({})".format(header_data["ac_count"]) if trend else ""
        bh_2 = "{}: {}".format(translation_data["total_acs"], header_data["ac_count"])
        bottom_headers = [bh_1, bh_2]
        label_value_title = [translation_data["ac"], translation_data["label_value_title"]]
    elif compare_type == COMPARE_TYPE.LOCALITY:
        th_1 = "{}. {} - {} {} - {} {}".format(AC_NO, AC_NAME, header_data["local_body"], translation_data["local_body"], header_data["locality"], translation_data["locality"])
        # th_1 = "{}. {} - {} {} - ".format(AC_NO, AC_NAME, header_data["locality"], translation_data["locality"])
        # th_2 = "({})".format(trend_count) if trend else ""
        # th_3 = "- ({})".format(header_data["locality_count"]) if trend else ""
        bh_2 = "{} {}: {}".format(
            translation_data["locality"], translation_data["total_parts"], header_data["booth_count"]
        )
        bottom_headers = [bh_1, bh_2]
        label_value_title = [translation_data["booth_no_short"], translation_data["label_value_title"]]
    else:
        if header_data["ward_vp_type"] == WARD_VP_TYPE.WARD:
            th_1 = "{}. {} - {} {} - {} {}".format(AC_NO, AC_NAME, header_data["local_body"], translation_data["local_body"], translation_data["ward"], header_data["ward_vp"])
        else:
            th_1 = "{}. {} - {} {} - {} {}".format(AC_NO, AC_NAME, header_data["local_body"], translation_data["local_body"], header_data["ward_vp"], translation_data["village_panchayat"])

        # th_1 = "{}. {} - {} {} - ".format(AC_NO, AC_NAME, header_data["ward_vp"], translation_data["ward_vp"])
        # th_2 = "({})".format(trend_count) if trend else ""
        # th_3 = "- ({})".format(header_data["locality_count"]) if trend else ""
        bh_2 = "{} {}: {}".format(
            translation_data["local_body"], translation_data["total_parts"], header_data["booth_count"]
        )
        bottom_headers = [bh_1, bh_2]
        label_value_title = [translation_data["booth_no_short"], translation_data["label_value_title"]]

    top_headers = th_1

    return {
        "header_data": header_data,
        "header": {
            "top_header": top_headers,
            "bottom_header": bottom_headers,
        },
        "label_value_title": label_value_title,
    }



def get_matching_header_data(
    compare_type, modified_response_header_data, hierarchy_item_data, trend
):
    header_data = dict()
    hierarchy_item_value = hierarchy_item_data["hierarchy_item_value"]

    if compare_type in [COMPARE_TYPE.BOOTH, COMPARE_TYPE.LOCALITY, COMPARE_TYPE.WARD]:
        checking_key = "sub_trend_booth_list_expanded" if trend else "lb_booth_list"
        hierarchy_item_value = int(hierarchy_item_value)

        ## for ward type, check if ward_vp matches also because the same booth will be present in two wards
        if compare_type == COMPARE_TYPE.WARD:
            parent_ward = hierarchy_item_data["parent_locality"]

    elif compare_type == COMPARE_TYPE.LOCAL_BODY:
        checking_key = "local_body"
    else:  ## compare type = AC
        checking_key = None

    if not checking_key:
        header_data = modified_response_header_data[0]
    else:
        if compare_type == COMPARE_TYPE.WARD:
            for header_item in modified_response_header_data:
                if ((parent_ward == header_item["ward_vp"]) and (hierarchy_item_value in header_item.get(checking_key))):
                    header_data = header_item
                    break 
                else: 
                    continue

        else:
            for header_item in modified_response_header_data:
                if hierarchy_item_value in header_item.get(checking_key):
                    header_data = header_item
                    break
                else: 
                    continue

    return header_data



def modify_header_item(header_item: Dict):
    trend_bl = header_item["sub_trend_booth_list"]
    new_trend_bl = []

    for bl_number_string in trend_bl:
        if "-" in bl_number_string:
            split_bl_list = bl_number_string.split("-")

            for num in range(int(split_bl_list[0]), int(split_bl_list[1]) + 1):
                new_trend_bl.append(num)
        else:
            new_trend_bl.append(int(bl_number_string))

    header_item["sub_trend_booth_list"] = new_trend_bl

    return header_item

def get_trends_from_subtrends_header(header_list, compare_type: str) -> Dict:
    if compare_type in [COMPARE_TYPE.LOCALITY, COMPARE_TYPE.WARD]:
        grp_local_body = groupby(header_list, lambda x: x["local_body"])

        final_dict = dict()
        for lb_key, lb_value in grp_local_body:
            lb_value_list = list(lb_value)

            grp_locality = groupby(lb_value_list, lambda x: x[compare_type])
            
            for locality_key, locality_value in grp_locality:
                locality_value_list = list(locality_value)

                grp_trends = groupby(locality_value_list, lambda x: x["trend"])

                for trend_key, trend_value in grp_trends:
                    trend_value_list = list(trend_value)

                    total_booths_list = []
                    for x in trend_value_list:
                        total_booths_list.extend(x["sub_trend_booth_list_expanded"])

                    total_booths_list = list(set(total_booths_list))
                    total_booths_list.sort()

                    final_dict[lb_key] = {
                        **final_dict.get(lb_key, {}),
                        locality_key: {
                            **final_dict.get(lb_key, {}).get(locality_key, {}),
                            trend_key: total_booths_list,
                        }
                    }
        return final_dict
    
    else:
        initial_groupby_key = "local_body"

        grp_local_body = groupby(header_list, lambda x: x[initial_groupby_key])

        new_grp_local_body = dict()
        for key, value in grp_local_body:
            try:
                new_grp_local_body[key].extend(list(value))
            except Exception as e:
                new_grp_local_body[key] = list(value)

        new_grp_trend = dict()

        for item_key in new_grp_local_body:
            trendwise_lb_grped = groupby(new_grp_local_body[item_key], lambda x: x["trend"])

            for key, value in trendwise_lb_grped:
                subtrend_wise_list = list(value)

                total_booths_list = []

                for x in subtrend_wise_list:
                    total_booths_list.extend(x["sub_trend_booth_list_expanded"])

                total_booths_list = list(set(total_booths_list))
                total_booths_list.sort()

                try:
                    new_grp_trend[item_key][key].extend(total_booths_list)

                except Exception as e:
                    key_present = new_grp_trend.get(item_key, None)
                    if key_present:
                        new_grp_trend[item_key] = {**new_grp_trend[item_key], key: []}
                    else:
                        new_grp_trend[item_key] = {key: []}

                    new_grp_trend[item_key][key] = total_booths_list

        return new_grp_trend



def is_satisfies_flag(
    flag: int, value, payload: Dict, differentiation_type: str, matching_year: str
) -> bool:
    ## if flag is 0, that is display all booths so no need to check the flags of years
    if flag == 0:
        return True

    ## if flag is not 0, it will be either 3 or 4, in that case, filter the booths based on the
    # flags of years that have either flag 3 or 4, based on the flag value passed
    else:
        year_list = payload.get("year")

        # if differentiation type is AND logic
        if differentiation_type == DIFFERENTIATION_TYPE.AND:
            flags = list()

            for year in year_list:
                flags.append(value[year]["flag"])

            duplicates_flags_removed = set(flags)

            if len(duplicates_flags_removed) == 1 and (
                int(flag) in duplicates_flags_removed
            ):
                satisfies = True
            else:
                satisfies = False

        # if differentiation type is OR logic
        else:
            try:    
                if value[matching_year]["flag"] == flag:
                    non_years_list = [] 

                    ## check only for the other years not the OR condition matching year
                    for year in year_list:
                        if year != matching_year:
                            is_not_matching_flag = value[year]["flag"] != flag
                            non_years_list.append(is_not_matching_flag) 

                    satisfies = all(non_years_list)
                else:
                    satisfies = False
            except Exception as e:
                raise

    return satisfies


def get_new_lb_graph_data_item(lb_name) -> Dict:
    return {
        "lb_index_data": None, 
        "lb_name": lb_name, 
        "lb_wise_graph_data": [], 
        "lb_separation_page": get_page_obj("", None),
        }