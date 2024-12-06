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
    STATUS
)
import plotly.express as px
import pandas as pd
from .extra_utils import indian_number_format
from .report_pdf_constants import (
    COMPARE_TYPE,
    DIFFERENTIATION_TYPE,
)
from itertools import groupby
import logging
import concurrent.futures
from .graph_page_util import get_page_obj


def group_table_pages_data(
    response_data: Dict,
    ITEMS_PER_PAGE: int,
    should_set_row_style: bool,
    should_add_booths_per_lb: bool,
    is_get_total_hierarchy_item_count: bool,
    TABLE_KEY_TO_LOOKUP: str,
    should_sort: bool,
    is_index_table: bool,
    compare_type: str,
    translation_data: Dict
):
    if len(response_data) == 0:
        return []

    if should_sort:
        response_data = sorted(response_data, key=lambda x: x["booth_no"])

    ## set alternating row style based on the local body name
    if should_set_row_style:
        if is_index_table:
            # for index data, set status for each index row based on trend
            page_data = list(map(lambda item: ({ **item, "status": translation_data[get_status(item["trend"])] }), response_data))
            
            # adds styling for index data 
            page_data = add_index_row_style(page_data, should_add_booths_per_lb, compare_type)
        else:
            page_data = add_other_table_row_style(
                response_data, should_add_booths_per_lb
            )
    else:
        page_data = response_data

    page_item_count = len(page_data)
    final_page_data = []

    if page_item_count < ITEMS_PER_PAGE:
        final_page_data.append(
            get_page_obj(
                "",
                {
                    "total_count_per_table": (
                        get_total_hierarchy_item_count(
                            data_to_loop=page_data, KEY_TO_LOOKUP=TABLE_KEY_TO_LOOKUP
                        )
                        if is_get_total_hierarchy_item_count
                        else None
                    ),
                    "page_data": page_data,
                },
            )
        )
    else:
        number_of_iterations = math.ceil(page_item_count / ITEMS_PER_PAGE)
        slice_from = 0
        slice_till = 0 + ITEMS_PER_PAGE

        for x in range(number_of_iterations):
            sliced_page_data = page_data[slice_from:slice_till]

            final_page_data.append(
                get_page_obj(
                    "",
                    {
                        "total_count_per_table": (
                            get_total_hierarchy_item_count(
                                data_to_loop=sliced_page_data,
                                KEY_TO_LOOKUP=TABLE_KEY_TO_LOOKUP,
                            )
                            if is_get_total_hierarchy_item_count
                            else None
                        ),
                        "page_data": sliced_page_data,
                    },
                )
            )
            slice_from = slice_from + ITEMS_PER_PAGE
            slice_till = slice_till + ITEMS_PER_PAGE

    # does grouping of the index data items in order to group and merge the rows as per lb, locality/ward_vp wise
    # should do only for the index table, not for summary or appendix table
    if is_index_table and should_set_row_style:
        final_page_data = merge_index_table_rows(final_page_data, compare_type, translation_data)

    return final_page_data

def merge_index_table_rows(index_table_data: list, compare_type, translation_data: Dict) -> List:
    if compare_type in [COMPARE_TYPE.WARD]:
        for index_page_obj in index_table_data:
            new_page_data = dict() 
            for index_item in index_page_obj["page_data"]["page_data"]:

                new_page_data = {
                    **new_page_data,
                    index_item["lb_name"]: {
                        "meta": {
                            "lb_type": index_item["lb_type"],
                            "total_booths": index_item["lb_wise_booth_count"],
                            "s_no": index_item["s_no"],
                        },
                        "data": {
                            **new_page_data.get(index_item["lb_name"], {}).get("data", {}),
                            index_item[compare_type]: {
                                "meta": {
                                    "total_booths": index_item["ward_wise_booth_count"],
                                    "ward_type": index_item["ward_vp_type"],
                                },
                                "data": {
                                    **new_page_data.get(index_item["lb_name"], {}).get("data", {}).get(index_item[compare_type], {}).get("data", {}),
                                    index_item["status"]: {
                                        "data": {
                                            **new_page_data.get(index_item["lb_name"], {}).get("data", {}).get(index_item[compare_type], {}).get("data", {}).get(index_item["status"], {}).get("data", {}),
                                            index_item["trend"]: {
                                                "meta": {
                                                    "total_booths": index_item["trend_wise_booth_count"],
                                                    "status": translation_data[get_status(trend=index_item["trend"])]
                                                },
                                                "data": [
                                                    *new_page_data.get(index_item["lb_name"], {}).get("data", {}).get(index_item[compare_type], {}).get("data", {}).get(index_item["status"], {}).get("data", {}).get(index_item["trend"], {}).get("data", []),
                                                    index_item,
                                                ]
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            index_page_obj["page_data"]["grouped_page_data"] = new_page_data
        
        return index_table_data
    else:
        return index_table_data

## calculates the page numbers of items for the index page and does it in multithreading
def apply_index_page_numbers(graph_data_pages_list: List, compare_type):
    INDEX_LB_KEY = {
        COMPARE_TYPE.BOOTH: "lb_name",
        COMPARE_TYPE.LOCAL_BODY: "local_body",
        COMPARE_TYPE.AC: "ac_name",
        COMPARE_TYPE.LOCALITY:  COMPARE_TYPE.LOCALITY,
        COMPARE_TYPE.WARD: COMPARE_TYPE.WARD,
    }

    def process_chapter_item(chapter_item, compare_type, INDEX_LB_KEY):
        # check if index data is present or empty, if empty, page nums cant be calculated hence return the original chapter back 
        if len(chapter_item[1]) == 0:
            return chapter_item
        else:
            current_trend = None
            current_index_item_value = None
            current_subtrend = None

            # set page num for lb wise index data
            for lb_obj in chapter_item[2]:
                for table_page_obj in lb_obj["lb_index_data"]:
                    for lb_name in table_page_obj["page_data"]["grouped_page_data"]:
                        lb_data = table_page_obj["page_data"]["grouped_page_data"][lb_name]["data"]
                        for ward in lb_data:
                            ward_data = lb_data[ward]["data"]

                            for status in ward_data:
                                status_data = ward_data[status]["data"]

                                for trend in status_data:
                                    for index_item in status_data[trend]["data"]:
                                        last_page_found = False
                                        initial_page_num = 0
                                        last_page_num = 0

                                    if not current_trend or not current_index_item_value or not current_subtrend:
                                        current_trend = index_item["trend"]
                                        current_index_item_value = index_item[INDEX_LB_KEY[compare_type]]
                                        current_subtrend = index_item["sub_trend"]

                                    for lb_wise_object in chapter_item[2]:
                                            if not last_page_found:
                                                
                                                total_items = len(lb_wise_object["lb_wise_graph_data"])
                                                
                                                for idx, graph_page_obj in enumerate(lb_wise_object["lb_wise_graph_data"]):
                                                    if not last_page_found:
                                                        
                                                        # if it is the last lb item, then take the last page's page number
                                                        if initial_page_num and idx + 1 == total_items:
                                                            last_page_found = True
                                                            last_page_num = int(graph_page_obj["page_number"])
                                                        else:
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
                                                            else:
                                                                if hierarchy_item["trend"] != current_trend:
                                                                    if not initial_page_num:
                                                                        continue
                                                                    else:
                                                                        last_page_num = int(graph_page_obj["page_number"]) - 1
                                                                        last_page_found = True
                                                                else:
                                                                    if hierarchy_item["sub_trend"] != current_subtrend:
                                                                        if not initial_page_num:
                                                                            continue
                                                                        else:
                                                                            last_page_num = int(graph_page_obj["page_number"]) - 1
                                                                            last_page_found = True
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
            
            # set page num for main index data
            for lb_obj in chapter_item[1]:
                for lb_name in lb_obj["page_data"]["grouped_page_data"]:
                    lb_data = lb_obj["page_data"]["grouped_page_data"][lb_name]["data"]
                    for ward in lb_data:
                        ward_data = lb_data[ward]["data"]

                        for status in ward_data:
                            status_data = ward_data[status]["data"]
                            
                            for trend in status_data:
                                for index_item in status_data[trend]["data"]:
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
                                                        else:
                                                            if hierarchy_item["trend"] != current_trend:
                                                                if not initial_page_num:
                                                                    continue
                                                                else:
                                                                    last_page_num = int(graph_page_obj["page_number"]) - 1
                                                                    last_page_found = True
                                                            else:
                                                                if hierarchy_item["sub_trend"] != current_subtrend:
                                                                    if not initial_page_num:
                                                                        continue
                                                                    else:
                                                                        last_page_num = int(graph_page_obj["page_number"]) - 1
                                                                        last_page_found = True
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
    
    ### perform the multithreading using the above function for the graph_data_pages_list 
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Run process_chapter_item in multiple threads
        results = list(executor.map(lambda chapter_item: process_chapter_item(chapter_item, compare_type, INDEX_LB_KEY), graph_data_pages_list))

    return results




def apply_appendix_page_numbers(table_data, graph_data):
    for table_page_obj in table_data:
        for appendix_item in table_page_obj["page_data"]["page_data"]:
            appendix_hierarchy_num = appendix_item["booth_no"]

            for lb_wise_obj in graph_data:
                for graph_page_obj in lb_wise_obj["lb_wise_graph_data"]:
                    graph_hierarchy_item_page_num = graph_page_obj["page_number"]
                    graph_hierarchy_item_pair_list = graph_page_obj["page_data"]
                    graph_hierarchy_item_one = graph_hierarchy_item_pair_list[0]
                    graph_hierarchy_item_two = (
                        graph_hierarchy_item_pair_list[1]
                        if len(graph_hierarchy_item_pair_list) > 1
                        else None
                    )

                    if (
                        str(graph_hierarchy_item_one["hierarchy_item_value"])
                        == str(appendix_hierarchy_num)
                    ) or (
                        graph_hierarchy_item_two
                        and str(graph_hierarchy_item_two["hierarchy_item_value"])
                        == str(appendix_hierarchy_num)
                    ):
                        appendix_item["page_no"] = graph_hierarchy_item_page_num
                        break

    return table_data



def get_total_hierarchy_item_count(data_to_loop: List, KEY_TO_LOOKUP: str):
    count = 0
    for item in data_to_loop:
        count += item[KEY_TO_LOOKUP]
    return count



## only used for index table.
## based on the local body name, each row is styled accordingly between dark and light color scheme
## to differentiate between the local bodies
def add_index_row_style(source_row_data: List, should_add_booths_per_lb: bool, compare_type):
    modified_row_data: List = []

    if compare_type in [COMPARE_TYPE.LOCALITY, COMPARE_TYPE.WARD]:
        sub_group_key = compare_type # compare_type would be "locality" or "ward_vp"
        df = pd.DataFrame(source_row_data)
        lb_list = df["lb_name"].unique().tolist()
        
        ## set sl no based on lb names
        lb_dict_with_sl_no = { lb_name : idx+1 for idx, lb_name in enumerate(lb_list) }
        for index_item in source_row_data:
            index_item["s_no"] = lb_dict_with_sl_no[index_item["lb_name"]]

        ## lb wise total booth count
        for lb_name in lb_list:
            matching_records_df = df[(df["lb_name"] == lb_name)]
            booths_list = matching_records_df["booth_list_expanded"].to_list()
            unique_booths_list = []
            for arr in booths_list:
                unique_booths_list.extend(arr)

            total = len(set(unique_booths_list))
            index_list = matching_records_df.index.tolist()

            for idx in index_list:
                source_row_data[idx]["lb_wise_booth_count"] = int(total)

        ## ward_vp/locality wise total booth count
        ward_list = df[["lb_name", sub_group_key]]
        new_ward_list = set(ward_list.to_records(index=None).tolist())
        
        for lb_name, ward_vp in new_ward_list:
            matching_records_df = df[(df["lb_name"] == lb_name) & (df[sub_group_key] == ward_vp)]
            total = matching_records_df["booth_count"].sum()
            index_list = matching_records_df.index.tolist()

            for idx in index_list:
                source_row_data[idx]["ward_wise_booth_count"] = int(total)
        
        ## trend wise total booth count
        trend_list_mapping = df[["lb_name", "ward_vp", "trend"]]
        new_trend_list_mapping = set(trend_list_mapping.to_records(index=None).tolist())

        for lb_name, ward_vp, trend in new_trend_list_mapping:
            matching_records_df = df[(df["lb_name"] == lb_name) & (df[sub_group_key] == ward_vp) & (df["trend"] == trend)]
            total = matching_records_df["booth_count"].sum()
            index_list = matching_records_df.index.tolist()

            for idx in index_list:
                source_row_data[idx]["trend_wise_booth_count"] = int(total)
        
        return source_row_data

    else:
        is_dark_theme: bool = True

        grouped_data = groupby(source_row_data, lambda x: x["lb_name"])

        current_trend = None
        current_parent_name = None

        for key, value in grouped_data:
            is_dark_theme = not is_dark_theme

            list_value = list(value)
            length = len(list_value)

            total_booth_count = 0
            for idx, item in enumerate(list_value):
                if idx == 0 :
                    item["add_thick_border"] = True

                if current_trend == None and current_parent_name == None:
                    item["has_top_line"] = True
                    current_trend = item["trend"]
                    current_parent_name = item["lb_name"]
                elif item["lb_name"] == current_parent_name and item["trend"] == current_trend:
                    item["has_top_line"] = False
                else:
                    item["has_top_line"] = True
                    current_trend = item["trend"]
                    current_parent_name = item["lb_name"]

                item["row_theme"] = is_dark_theme

                if should_add_booths_per_lb:
                    total_booth_count += item["booth_count"]

                # if last item, add the total booth count value for it to be displayed in the index data
                if idx + 1 == length:
                    item["total_booth_count"] = total_booth_count

                modified_row_data.append(item)
        
        # get total booth count per local body and trend 
        current_lb = None 
        current_trend = None 
        first_trendwise_idx = None 
        booth_count_per_trend = 0

        total_length = len(modified_row_data)

        for current_idx, current_row in enumerate(modified_row_data):
            # initial set up even before the first row is iterated
            if (current_lb and current_trend and first_trendwise_idx) == None:
                current_lb = current_row["lb_name"]
                current_trend = current_row["trend"]
                first_trendwise_idx = current_idx

            # if lb and trend match, get the booth count from the row and add to the total booth count 
            belongs_to_lb_trend_bucket = (current_lb == current_row["lb_name"] and current_trend == current_row["trend"])

            if belongs_to_lb_trend_bucket:
                booth_count_per_trend += current_row["booth_count"]

                # if row is the last item and doesnt match the previous bucket
                if total_length == current_idx + 1:
                    prev_first_row = modified_row_data[first_trendwise_idx]
                    prev_first_row["total_booth_count_per_trend"] = booth_count_per_trend
            else:
                prev_first_row = modified_row_data[first_trendwise_idx]
                prev_first_row["total_booth_count_per_trend"] = booth_count_per_trend

                booth_count_per_trend = current_row["booth_count"]
                current_lb = current_row["lb_name"]
                current_trend = current_row["trend"]
                first_trendwise_idx = current_idx

                # if row is the last item and doesnt match the previous bucket
                if total_length == current_idx + 1:
                    current_row["total_booth_count_per_trend"] = booth_count_per_trend
        
    # 
    # 
    # 

    return modified_row_data


def add_other_table_row_style(source_row_data: List, should_add_booths_per_lb: bool):
    is_dark_theme: bool = True
    modified_row_data: List = []

    grouped_data = groupby(source_row_data, lambda x: x["lb_name"])

    for key, value in grouped_data:
        is_dark_theme = not is_dark_theme

        list_value = list(value)
        length = len(list_value)

        total_booth_count = 0
        for idx, item in enumerate(list_value):
            item["row_theme"] = is_dark_theme

            if should_add_booths_per_lb:
                total_booth_count += item["booth_count"]

            # if last item, add the total booth count value for it to be displayed in the index data
            if idx + 1 == length:
                item["total_booth_count"] = total_booth_count

            modified_row_data.append(item)

    return modified_row_data



def get_parent_index_data(flag_items: List, translation_data: Dict, graph_data_pages_list: List, appendix_data_pages: List) -> List:
    is_appendix_present = len(appendix_data_pages) != 0
    parent_index_data = []

    # Titles used for different flag types
    TITLES = {
        "0": translation_data["all_party_vote_split"],
        "3": translation_data["index_title_3_party"],
        "4": translation_data["index_title_3_and_4_party"],
    }

    # Lambda function for creating parent index items
    get_parent_index_item = lambda s_no, title, year, flag: {
        "s_no": s_no,
        "lb_name": (f"{year} - " if year else "") + title,
        "booth_count": "",
        "booth_no": "",
        "page_number": "",
        "flag": flag,
    }

    # Create dynamic parent index items based on flag and year
    for idx, flag_item in enumerate(flag_items):
        parent_index_item = get_parent_index_item(idx + 1, TITLES[str(flag_item["flag"])], flag_item["year"], flag_item["flag"])
        parent_index_data.append(parent_index_item)

    # Add parent index item for appendix if present
    if is_appendix_present:
        s_no = parent_index_data[-1]["s_no"]
        parent_index_data.append(get_parent_index_item(s_no + 1, translation_data["appendix"], "", None))

    # Function to process each party list
    def process_party_list(index_data: List[Dict], format_ranges: callable):
        party_list = [int(booth_num) for index_pages in index_data for index_item in index_pages["page_data"]["page_data"] for booth_num in index_item["booth_list_expanded"]]
        party_list = sorted(set(party_list))  # Remove duplicates and sort
        return party_list, len(party_list), format_ranges(party_list, False)

    # Use ThreadPoolExecutor to handle concurrent processing dynamically
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for idx in range(len(flag_items)):
            future = executor.submit(process_party_list, graph_data_pages_list[idx][1], format_ranges)
            futures.append(future)

        # Collect results and populate parent_index_data
        for idx, future in enumerate(futures):
            party_list, party_list_len, party_list_concatenated = future.result()
            parent_index_data[idx]["booth_no"] = party_list_concatenated
            parent_index_data[idx]["booth_count"] = party_list_len

        # Handle appendix data if present
        if is_appendix_present:
            parent_index_data[-1]["booth_no"] = parent_index_data[0]["booth_no"]
            parent_index_data[-1]["booth_count"] = parent_index_data[0]["booth_count"]

    return [get_page_obj("", parent_index_data)], parent_index_data[0]["booth_count"]

def format_ranges(nums, should_sort: bool):
    if not nums:
        return []
    
    if should_sort:
            nums.sort() 
    ranges = []
    start = end = nums[0]
 
    for num in nums[1:]:
        if num == end + 1:
            end = num
        else:
            if start == end:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{end}" if end > start+1 else f"{start},{end}")
            start = end = num  # Start a new range
 
    # Append the last range
    if start == end:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}-{end}" if end > start+1 else f"{start},{end}")
 
    return ranges

def get_status(trend) -> str:
    status = None
    NUM_OF_YEARS = len(trend)

    loss_count = 0

    for i in trend:
        if i == "L":
            loss_count += 1

    if NUM_OF_YEARS == 2:
    # if years selected is 2
        if loss_count == 0:
            status = STATUS.WIN
        elif loss_count == 1:
            status = STATUS.GAVANAM_THEVAI
        else:
            status = STATUS.LOSS
    else:
        # if years selected are 3 or 4
        if loss_count == 0:
            status = STATUS.WIN
        elif loss_count == 1:
            status = STATUS.GAVANAM_THEVAI
        elif loss_count > 1 and loss_count < NUM_OF_YEARS:
            status = STATUS.ATHIGA_GAVANAM_THEVAI
        else:
            status = STATUS.LOSS

    return status


def add_status_to_index_rows(index_data: List) -> List:
    return map(lambda item: ({ **item, "status": get_status(item["trend"]) }), index_data)