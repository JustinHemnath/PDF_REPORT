from .extra_utils import time_it
import math
import json
import os
import json
import os
import math
import time
from typing import Dict, List, Union
from .report_pdf_constants import (
    COLORS,
    PARTY_WISE_COLORS,
    dmk_red_color,
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
from .index_page_util import (
    group_table_pages_data,
    apply_index_page_numbers,
    apply_appendix_page_numbers,
    get_parent_index_data,
)
from .graph_page_util import (
    group_graph_data,
    get_page_obj,
    get_trends_from_subtrends_header,
    is_satisfies_flag,
    get_modifed_hierarchy_item,
)

with open(
    "utils/ac_number_to_name.json",
    "r",
    encoding="utf-8",
) as f:
    ac_number_to_name = json.load(f)

with open("utils/extra_pages_translation.json", "r", encoding="utf-8") as f:
    extra_pages_translation_data = json.load(f)



@time_it
def model_data(flags_list, response_data={}, payload={}, translation_data={}, total_lb_list=[]):
    logging.info("Modelling response from server into PDF data")

    AC_NO = payload.get("ac_no", None)
    YEARS_LIST = payload.get("year", [])
    LANG = payload.get("lang")
    TREND = payload.get("trend", False)
    compare_type = payload.get("compare_type")
    flag = payload.get("flag")
    flags=flags_list
    
    SUMMARY_ITEMS_PER_PAGE = 5 if compare_type in [COMPARE_TYPE.WARD] else 12
    INDEX_ITEMS_PER_PAGE = 13
    APPENDIX_ITEMS_PER_PAGE = 13
    CANDIDATES_ITEMS_PER_PAGE = 18 if len(YEARS_LIST) == 2 else 13

    BOOTH_COUNT_KEY = "booth_count"

    if compare_type in [COMPARE_TYPE.BOOTH, COMPARE_TYPE.LOCALITY, COMPARE_TYPE.WARD]:
        HEADER_ITEM_CHECK_KEY = "trend_booth_list" if TREND else "lb_booth_list"
        TABLE_KEY_TO_LOOKUP = BOOTH_COUNT_KEY
        should_set_style_for_index = True
        should_add_booths_per_lb = True
        is_get_total_hierarchy_item_count = True
    elif compare_type == COMPARE_TYPE.LOCAL_BODY:
        HEADER_ITEM_CHECK_KEY = "local_body"
        TABLE_KEY_TO_LOOKUP = "lb_count"
        should_set_style_for_index = False
        should_add_booths_per_lb = False
        is_get_total_hierarchy_item_count = True
    elif compare_type == COMPARE_TYPE.AC:
        HEADER_ITEM_CHECK_KEY = "ac_name"
        TABLE_KEY_TO_LOOKUP = "ac_count"
        should_set_style_for_index = False
        should_add_booths_per_lb = False
        is_get_total_hierarchy_item_count = True
    else:
        HEADER_ITEM_CHECK_KEY = "trend_booth_list" if TREND else "lb_booth_list"
        TABLE_KEY_TO_LOOKUP = BOOTH_COUNT_KEY
        should_set_style_for_index = True
        should_add_booths_per_lb = True
        is_get_total_hierarchy_item_count = True

    extra_metadata = {
        "AC_NO": AC_NO,
        "AC_NAME": ac_number_to_name[LANG][str(AC_NO)],
        "YEARS_LIST": YEARS_LIST,
        "LANG": LANG,
        "COLORS": COLORS,
        "COMPARE_TYPE": compare_type,
        "HEADER_ITEM_CHECK_KEY": HEADER_ITEM_CHECK_KEY,
        "TRENDS": TREND,
    }

    summary_data_pages = []
    appendix_data_pages = []
    candidates_data_pages = []
    total_pages = 0

    ## get candidates list pages only for ward type
    if compare_type == COMPARE_TYPE.WARD:
        candidates_data_pages = group_table_pages_data(
            response_data=response_data["candidates_data"],
            ITEMS_PER_PAGE=CANDIDATES_ITEMS_PER_PAGE,
            should_set_row_style=False,
            should_add_booths_per_lb=False,
            is_get_total_hierarchy_item_count=False,
            TABLE_KEY_TO_LOOKUP=TABLE_KEY_TO_LOOKUP,
            should_sort=False,
            is_index_table=True,
            compare_type=compare_type,
            translation_data=translation_data
        )

    # GET GRAPH PAGE DATA
    modified_response_header_data = response_data["header_data"]

    # get trends accumulated booth list from given header which has only subtrends wise booth list
    trends_grouped_data = get_trends_from_subtrends_header(
        modified_response_header_data,
        compare_type,
    )

    # GET SUMMARY PAGE DATA
    summary_data_pages = group_table_pages_data(
        response_data=response_data["summary_data"],
        ITEMS_PER_PAGE=SUMMARY_ITEMS_PER_PAGE,
        should_set_row_style=True,
        should_add_booths_per_lb=should_add_booths_per_lb,
        is_get_total_hierarchy_item_count=is_get_total_hierarchy_item_count,
        TABLE_KEY_TO_LOOKUP=BOOTH_COUNT_KEY,
        should_sort=False,
        is_index_table=False,
        compare_type=compare_type,
        translation_data=translation_data
    )


    # get graph and index pages for all three chapters
    flag_items = get_flag_items(flags, YEARS_LIST)

    def process_graph_data(flag_item):
        graph_data_pages, filtered_index_data_pages = group_graph_data(
            payload=payload,
            graph_main_data=response_data["graph_data"],
            extra_metadata=extra_metadata,
            translation_data=translation_data,
            modified_response_header_data=modified_response_header_data,
            compare_type=compare_type,
            lang=LANG,
            index_data_pages=response_data["index_data"],
            trends_grouped_data=trends_grouped_data,
            flag=flag_item["flag"],
            differentiation_type=flag_item["diff"],
            year_for_or_filter=flag_item["year"],
            ac_number_to_name=ac_number_to_name
        )

        # Process the index_data_pages for each flag item
        grouped_index_data_pages = group_table_pages_data(
            response_data=filtered_index_data_pages,
            ITEMS_PER_PAGE=INDEX_ITEMS_PER_PAGE,
            should_set_row_style=should_set_style_for_index,
            should_add_booths_per_lb=should_add_booths_per_lb,
            is_get_total_hierarchy_item_count=is_get_total_hierarchy_item_count,
            TABLE_KEY_TO_LOOKUP=TABLE_KEY_TO_LOOKUP,
            should_sort=False,
            is_index_table=True,
            compare_type=compare_type,
            translation_data=translation_data
        )

        # create dummy chapter separation page obj for adding page number for chapter separation page
        chapter_separation_pages = [get_page_obj("", None)]

        # adds individual lb wise index data to each lb wise graph data 
        graph_data_pages = add_lb_index_data_to_graph_data(index_data_pages=filtered_index_data_pages, graph_data_pages=graph_data_pages, compare_type=compare_type, INDEX_ITEMS_PER_PAGE=INDEX_ITEMS_PER_PAGE, translation_data=translation_data)

        return [
            chapter_separation_pages,
            grouped_index_data_pages,
            graph_data_pages,
            flag_item["flag"],
            flag_item["diff"],
            flag_item["year"],
        ]

    # Multithread 
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(process_graph_data, flag_item): index for index, flag_item in enumerate(flag_items)}
        graph_data_pages_list = [None] * len(flag_items)

        for future in concurrent.futures.as_completed(futures):
            index = futures[future]
            try:
                result = future.result()
                graph_data_pages_list[index] = result
            except Exception as exc:
                print(f'Generated an exception: {exc}')

    # graph_data_pages_list = []
    # for flag_item in flag_items:
    #     new = process_graph_data(flag_item)
    #     graph_data_pages_list.append(new)
    
    # # GET APPENDIX PAGE DATA
    if compare_type in [COMPARE_TYPE.BOOTH, COMPARE_TYPE.WARD]:
        appendix_data_pages = group_table_pages_data(
            response_data=response_data["appendix"],
            ITEMS_PER_PAGE=APPENDIX_ITEMS_PER_PAGE,
            should_set_row_style=False,
            should_add_booths_per_lb=False,
            is_get_total_hierarchy_item_count=False,
            TABLE_KEY_TO_LOOKUP=TABLE_KEY_TO_LOOKUP,
            should_sort=True,
            is_index_table=False,
            compare_type=compare_type,
            translation_data=translation_data
        )

    # 
    # 
    # GET PARENT INDEX DATA 
    parent_index_data, total_booths = get_parent_index_data(flag_items=flag_items, translation_data=translation_data, graph_data_pages_list=graph_data_pages_list, appendix_data_pages=appendix_data_pages)

            
    # metadata that contains extra metadata
    METADATA = get_metadata(
            lang=LANG,
            payload=payload,
            response_data=response_data,
            extra_metadata=extra_metadata,
            translation_data=translation_data,
            total_booths=response_data["header_data"][0]["total_booth"]
        )

    summary_data_pages, parent_index_data, graph_data_pages_list, appendix_data_pages, candidates_data_pages, total_pages = apply_page_numbers(
            summary_data=summary_data_pages,
            parent_index_data=parent_index_data,
            graph_data_pages_list=graph_data_pages_list,
            appendix_data=appendix_data_pages,
            candidates_data_pages=candidates_data_pages
        )

    # applies page numbers to index and appendix items from the positions of graph page items
    graph_data_pages_list = apply_index_page_numbers(
        graph_data_pages_list, compare_type
    )


    if compare_type in [COMPARE_TYPE.BOOTH, COMPARE_TYPE.WARD]:
        appendix_data_pages = apply_appendix_page_numbers(
            appendix_data_pages, graph_data_pages_list[0][2]
        )
    else:
        appendix_data_pages = []
        
    ## adds total booths per chapter to graph pages list to show in their respective page headers
    graph_data_pages_list = append_total_booths_per_chapter(parent_index_data, graph_data_pages_list)

    return {
        "summary_data_pages": summary_data_pages,
        "candidates_data_pages": candidates_data_pages,
        "parent_index_data": parent_index_data,
        "graph_data_pages_list": graph_data_pages_list,
        "appendix_data_pages": appendix_data_pages,
        "total_pages": total_pages,
        "METADATA": METADATA,
        "DEFICIT_BOOTHS_INFO": get_missing_booth_info(booths_in_db=total_booths, ac_total_booths=response_data["header_data"][0]["total_booth"], total_lb_list=total_lb_list, payload=payload),
        "CONSOLIDATED_GENDER_STATS": response_data["consolidated_gender_stats"]
    }


def get_metadata(
    lang: str = "en",
    payload: Dict = {},
    response_data: Dict = {},
    extra_metadata={},
    translation_data: Dict = {},
    total_booths: int = 0, 
):

    TRENDS = extra_metadata["TRENDS"]
    compare_type = payload.get("compare_type")
    flag = payload.get("flag")

    COMMON_HEADER = {
        COMPARE_TYPE.BOOTH: translation_data["booth_common_header"],
        COMPARE_TYPE.LOCAL_BODY: translation_data["lb_common_header"],
        COMPARE_TYPE.AC: translation_data["ac_common_header"],
        COMPARE_TYPE.LOCALITY: translation_data["locality_common_header"],
        COMPARE_TYPE.WARD: translation_data["ward_vp_common_header"],
    }

    header = "{}. {} - {} - {}".format(
        extra_metadata["AC_NO"],
        extra_metadata["AC_NAME"],
        COMMON_HEADER[compare_type],
        ", ".join(extra_metadata["YEARS_LIST"]),
    )

    chapter_header_list = [
        translation_data["all_party_vote_split"],
        translation_data["index_title_3_party"],
        translation_data["index_title_3_and_4_party"],
    ]

    # summary_text
    extra_pages_translation = extra_pages_translation_data[lang]

    # summary header
    summary_header = {
        COMPARE_TYPE.BOOTH: translation_data["summary_booth"],
        COMPARE_TYPE.LOCAL_BODY: translation_data["summary_booth"],
        COMPARE_TYPE.AC: translation_data["summary_booth"],
        COMPARE_TYPE.LOCALITY: translation_data["summary_booth"],
        COMPARE_TYPE.WARD: translation_data["summary_booth"],
    }

    return {
        **extra_metadata,
        "TOTAL_BOOTHS": total_booths,
        "header": header,
        "T": translation_data,
        "compare_type": compare_type,
        "chapter_header_list": chapter_header_list,
        "lang": lang,
        "preface_text": extra_pages_translation["preface"],
        "summary_header": summary_header[compare_type]
    }


def apply_page_numbers(summary_data, parent_index_data, graph_data_pages_list, appendix_data, candidates_data_pages) -> Dict:
    PAGE_NO = 3

    for item in summary_data:
        item["page_number"] = PAGE_NO
        PAGE_NO += 1
    
    for parent_item in parent_index_data:
        parent_item["page_number"] = PAGE_NO
        PAGE_NO += 1

    for item in candidates_data_pages:
            item["page_number"] = PAGE_NO
            PAGE_NO += 1

    for graph_item_tuple in graph_data_pages_list:
        # for chapter separation page
        for item in graph_item_tuple[0]:
            item["page_number"] = PAGE_NO
            PAGE_NO += 1
        
        # for index page
        for item in graph_item_tuple[1]:
            item["page_number"] = PAGE_NO
            PAGE_NO += 1

        # for graph pages where each object is an lb 
        for lb_wise_obj in graph_item_tuple[2]:
            # for lb separation page
            lb_wise_obj["lb_separation_page"]["page_number"] = PAGE_NO
            PAGE_NO += 1
            
            # for lb index pages
            for index_item in lb_wise_obj["lb_index_data"]:
                index_item["page_number"] = PAGE_NO
                PAGE_NO += 1

            # for lb graph pages
            for graph_item in lb_wise_obj["lb_wise_graph_data"]:
                graph_item["page_number"] = PAGE_NO
                PAGE_NO += 1

    for item in appendix_data:
        item["page_number"] = PAGE_NO
        PAGE_NO += 1

    total_pages = PAGE_NO - 1

    # add page number to page index items 
    for idx, graph_item in enumerate(graph_data_pages_list):
        parent_index_data[0]["page_data"][idx]["page_number"] = graph_item[0][0]["page_number"]
    
    if len(appendix_data) != 0:
        parent_index_data[0]["page_data"][-1]["page_number"] = appendix_data[0]["page_number"]

    return summary_data, parent_index_data, graph_data_pages_list, appendix_data, candidates_data_pages, total_pages



## adds total booths per chapter to graph pages list to show in their respective page headers
def append_total_booths_per_chapter(parent_index_data: List, graph_data_pages_list: List) -> List:
    new_list = list()

    for idx, graph_data_page_tuple in enumerate(graph_data_pages_list):
        graph_data_page_tuple.append(parent_index_data[0]["page_data"][idx]["booth_count"])
        new_list.append(graph_data_page_tuple)
    
    return new_list

# gets flag items payload 
def get_flag_items(flags: List, YEARS_LIST: List) -> List:
    get_flag_struct = (lambda flag, diff, year: { "flag": flag, "diff": diff, "year": year })
    flag_items = list()

    for flag in flags:
        if flag == 0:
        # for flag 0
            flag_items.append(get_flag_struct(flag, None, None))
        else:
        # for flag 3 and 4
            flag_items.append(get_flag_struct(flag, DIFFERENTIATION_TYPE.AND, None))

            for year in YEARS_LIST:
                flag_items.append(get_flag_struct(flag, DIFFERENTIATION_TYPE.OR, year))

    return flag_items


def get_missing_booth_info(booths_in_db, ac_total_booths, total_lb_list, payload) -> Dict:
    difference = ac_total_booths - booths_in_db
    payload_lb_list = payload.get("local_body")
    all_lbs_selected = len(payload_lb_list) == len(total_lb_list) 

    return {
        "should_display_info": all_lbs_selected and difference != 0,
        "deficit_booths": difference,
        "booths_in_db": booths_in_db,
        "ac_total_booths": ac_total_booths
    }


## adds individual lb wise index data to each lb wise graph data 
def add_lb_index_data_to_graph_data(index_data_pages, graph_data_pages, compare_type, INDEX_ITEMS_PER_PAGE, translation_data) -> Dict:
    df = pd.DataFrame(index_data_pages)

    for graph_item in graph_data_pages:
        lb_df = df[df["lb_name"] == graph_item["lb_name"]]
        lbwise_filtered_index_data = lb_df.to_dict(orient="records")

        lb_index_data_pages = group_table_pages_data(
            response_data=lbwise_filtered_index_data,
            ITEMS_PER_PAGE=INDEX_ITEMS_PER_PAGE,
            should_set_row_style=True,
            should_add_booths_per_lb=True,
            is_get_total_hierarchy_item_count=True,
            TABLE_KEY_TO_LOOKUP="booth_count",
            should_sort=False,
            is_index_table=True,
            compare_type=compare_type,
            translation_data=translation_data
        )

        graph_item["lb_index_data"] = lb_index_data_pages

    return graph_data_pages