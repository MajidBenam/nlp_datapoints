from lxml import etree, html
from bs4 import BeautifulSoup
import requests
import csv
import re
import bs4
import json
import time
import pandas as pd
import os

def read_unique_variables():
    """
    - From Equinox data, extarct all unique section/subsection/variables
    - return unique general variables
    """

    df = pd.read_excel('Equinox_2020_packaged_xls.xls', sheet_name="Equinox2020_CanonDat")

    unique_general_variables = []
    for row in df.iterrows():
        if row[1]['Section'] == "General variables":
            if row[1]['Variable'] not in unique_general_variables:
                unique_general_variables.append(row[1]['Variable'])
    return unique_general_variables

def ref_span_replacer(my_str, polity_name, html_files_root_dir):
    if html_files_root_dir == "seshat_browser_Jan_30_2023":
        RefRegex = re.compile('<sup class="reference" id="cite_ref-(\d{1,4})"><a href="#cite_note-(\d{1,4})">\[(\d{1,4})\]</a></sup>')
    elif html_files_root_dir == 'seshat_info_Jul_22':
        RefRegex = re.compile('<sup id="cite_ref-(\d{1,4})" class="reference"><a href="#cite_note-(\d{1,4})">\[(\d{1,4})\]</a></sup>')
    catches_all = RefRegex.finditer(my_str)
    #print(catches_all)
    if catches_all:
        for index, catches in enumerate(catches_all):
            if catches.group(1) == catches.group(2) and catches.group(1) == catches.group(3):
                my_str = my_str.replace(catches.group(0), f"[MAJIDBENAM_REF_{catches.group(1)}_{polity_name}]")
                if "_" in polity_name:
                    print(f"underlined polity name: {polity_name}")
            else:
                print(f"MIsMatch at index: {index+1}")
    return my_str



def image_remover(my_str):
    RefRegex = re.compile(r'(<p)>(.*?) src="/w/images(.*?)(</p)>')
    catches_all = RefRegex.finditer(my_str)
    if catches_all:
        for index, catches in enumerate(catches_all):
            my_str = my_str.replace(catches.group(0), "")
    RefRegex_2 = re.compile(r'<div><a href=(.*?) src="/w/images(.*?)">(.*?)</a>(.*?)</div>')
    catches_all_2 = RefRegex_2.finditer(my_str)
    if catches_all_2:
        for index, catches_2 in enumerate(catches_all_2):
            my_str = my_str.replace(catches_2.group(0), "")
    return my_str
    

def edit_tag_remover(my_str):
    RefRegex = re.compile(r'(<h4|<h2)>(.*?) class="mw-editsection-bracket">\[</span><a href(.*?) class="mw-editsection-bracket">\]</span>(.*?)(</h4|</h2)>')
    catches_all = RefRegex.finditer(my_str)
    if catches_all:
        for index, catches in enumerate(catches_all):
            my_str = my_str.replace(catches.group(0), "")
    return my_str

def linguistic_decider(my_str):
    RefRegex = re.compile(r'(<b>♠ Linguistic family)(.*?)</b>(.*?)(</div>)')
    catches_all = RefRegex.finditer(my_str)
    #print(catches_all)
    if catches_all:
        for index, catches in enumerate(catches_all):
            my_str = my_str.replace(catches.group(1), "</div><div class='meatypart'><b>♠ Linguistic family")

    return my_str

def inner_div_decider(my_str):
    new_str = my_str.replace("♥</b></div><div>", '♥</b>')
    new_str = new_str.replace("</div><div>", '[MAJIDBENAM_BR]')
    return new_str


def nlp_vars_html_extractor(html_files_root_dir, ALL_POLITIES=False):
    """
    This function takes:
    * html_files_relative_dir : the address where a bunch of raw HTML files reside:
     1) ../html_files/seshat_browser_Jan_30_2023/
     2) ../html_files/seshat_info_Jul_22/

     it also returns the extra p tags at the end that could be potential representatives for short ref texts
    """
    if not ALL_POLITIES:
        my_politys = ["AfGrBct", "CnNWei*"]
    else:
        my_politys = []
        with open("csv_files/polity_ngas.csv", 'r') as pol_csv:
            csv_reader = csv.reader(pol_csv, delimiter=',')
            for row in csv_reader:
                my_politys.append(row[1])
    all_extra_ps_dic = {}
    for polity in my_politys:
        #top_html = "<!DOCTYPE html><html><body><h2>"
        #bottom_html = "</body></html>"
        with open(f"html_files/{html_files_root_dir}/full_{polity}.html", "r", encoding='utf-8') as f:
            source= f.read()
            # take out the social complexity section
            # split_general = source.split('<span class="mw-headline" id="Social_Complexity_variables">Social Complexity variables</span>')[1]
            # split_source = split_general.split('<span class="mw-headline" id="Warfare_variables">Warfare variables</span>')[0]

            # Do shenanigans to make clean card game thingies
            better_source = source.replace("  ♣", " ♣").replace(" ♠", "♠").replace("♥ ", "♥")
            best_source = better_source.replace("<dl>", "").replace("</dl>", "").replace("<dd>", "<p>").replace("</dd>", "</p>").replace("\n", "")
            great_source = best_source.replace("<p><br><b>", "<p><b>").replace("<p><br></p>", "").replace("</p><p> <b>♠", "</p><p><b>♠")
            perfect_source = great_source.replace("</p><p><b>♠", "</div><p><b>♠").replace("</p><h4>", "</div><h4>")
            perfect_100 = perfect_source.replace("<p><b>♠", "<div class='meatypart'><b>♠")
            perfect_1000 = perfect_100.replace("</a></div><h4>", "</a></p><h4>").replace("</b></p>", "</b></div>")
            perfect_2000 = perfect_1000.replace("<p>", "<div>").replace("</p>", "</div>").replace("<p ", "<div ")
            # better_html_0 = top_html + perfect_2000 +  bottom_html
            better_html_0 = perfect_2000
            better_html = better_html_0 #.replace("<h2></body>", "</body>")
            
            # Extra careful for not skipping: Routledg, 78 )


            if better_html.count('<div') != better_html.count('</div'):
                print(f"{polity}: Number of divs: {better_html.count('<div')} and number of /divs: {better_html.count('</div')}.")
            if better_html.count('<p') != better_html.count('</p'):
                print(f"{polity}: Number of ps: {better_html.count('<p')} and number of /ps: {better_html.count('</p')}.")

            # save a shorter version of each html file
            final_html_after_ref_replacement = ref_span_replacer(better_html, polity, html_files_root_dir)
            final_html_after_image_removal = image_remover(final_html_after_ref_replacement)
            final_html_after_edit_removal = edit_tag_remover(final_html_after_image_removal)
            final_html_after_inner_par = inner_div_decider(final_html_after_edit_removal)

            # make some final modifications:
            final_html_after_inner_par = final_html_after_inner_par.replace("[present;absent]", "uncertain_present_absent")
            final_html_after_inner_par = final_html_after_inner_par.replace("[absent; present]", "uncertain_absent_present")
            final_html_after_inner_par = final_html_after_inner_par.replace("{absent; present}", "disputed_absent_present")

            final_html_after_inner_par = final_html_after_inner_par.replace("[present; absent]", "uncertain_present_absent")
            final_html_after_inner_par = final_html_after_inner_par.replace("{present; absent}", "disputed_present_absent")
            final_html_after_inner_par = final_html_after_inner_par.replace("[absent; inferred present]", "uncertain_absent_and_inferred_present")
            final_html_after_inner_par = final_html_after_inner_par.replace("{inferred absent; inferred present}", "disputed_inferred_absent_and_inferred_present")
            final_html_after_inner_par = final_html_after_inner_par.replace("{inferred absent; present}", "disputed_inferred_absent_and_present")

            print(polity, ":")

            # get the extra p's at the end as references
            if html_files_root_dir == "seshat_browser_Jan_30_2023":
                #split_based_on_refs_location = final_html_after_inner_par.split('<div class="mw-references-wrap mw-references-columns"')[1]
                split_based_on_refs_location = final_html_after_inner_par.split('<ol class="references"')[1]

                second_split = split_based_on_refs_location.split("</ol>")[1]
                third_split = second_split.split("</div>")[0]
                list_of_ps_at_the_end = third_split.split("[MAJIDBENAM_BR]")
            elif html_files_root_dir == "seshat_info_Jul_22":
                split_based_on_refs_location = final_html_after_inner_par.split('<ol class="references"')[1]
                #split_based_on_refs_location = final_html_after_inner_par.split('<span class="mw-headline" id="References">References</span>')[1] 
                second_split = split_based_on_refs_location.split("</ol>")[1]
                third_split = second_split.split("</div>")[0]
                list_of_ps_at_the_end = third_split.split("[MAJIDBENAM_BR]")
            #for pp in list_of_ps_at_the_end:
            #    print(f"- {pp}")
            all_extra_ps_dic[f"{polity}"] = list_of_ps_at_the_end


            with open(f"html_files/{html_files_root_dir}_augmented/full_nlp_{polity}.html", "w", encoding='utf-8') as fw:
                fw.write(final_html_after_inner_par)
    with open(f"json_files/extra_ps_at_the_end_for_{html_files_root_dir}.json", "w") as outfile:
        json.dump(all_extra_ps_dic, outfile)

def return_all_sc_vars():
    """
    Returns all sc variables as seen even once on html pages of the seshatdatabank.info
    """
    my_politys = []
    all_sc_vars = []
    with open("polity_ngas.csv", 'r') as pol_csv:
        csv_reader = csv.reader(pol_csv, delimiter=',')
        for row in csv_reader:
            my_politys.append(row[1])
    for polity in my_politys:
        with open(f"html_files_sc/full_sc_{polity}.html", "r", encoding='utf-8') as fr:
            source= fr.read()
            #VarRegex = re.compile(r'♠ (.*?) ♣(.*?)♥')
            catches = re.findall(r'♠ (.*?) ♣(.*?)♥',source)
            for catch in catches:
                if catch[0] not in all_sc_vars:
                    all_sc_vars.append(catch[0])
                #print(f"{catch[0]} : {catch[1]}")
    return all_sc_vars


def map_ref_to_var(html_files_root_dir, ALL_POLITIES=False):
    """
    Goes through the augmented html files and maps each ref to a corresponding variable inside the card game symbols and all.
    """
    if not ALL_POLITIES:
        my_politys = ["AfKidar", "CnNWei*", "AfGrBct"]
    else:
        my_politys = []
        with open("csv_files/polity_ngas.csv", 'r') as pol_csv:
            csv_reader = csv.reader(pol_csv, delimiter=',')
            for row in csv_reader:
                my_politys.append(row[1])
    mappings = {}
    for polity in my_politys:
        with open(f"html_files/{html_files_root_dir}_augmented/full_nlp_{polity}.html", "r", encoding='utf-8') as f:
            source= f.read()
            #var_regex = re.compile("♠(.*)♣")
            ref_regex = re.compile("MAJIDBENAM_REF_(\d{1,4})_")
            catches_all = ref_regex.finditer(source)
            #print(catches_all)
            if catches_all:
                for index, catches in enumerate(catches_all):
                    # text to be used for splitting
                    text_for_split = f"MAJIDBENAM_REF_{catches.group(1)}_"
                    var_part = source.split(text_for_split)[0]
                    var_regex = re.compile("♠(.*?)♣")
                    # ♣ missing in ♠ Largest fielded army {670,000; 1,133,800} ♥"Th ... in CnSui**
                    #  ♣ missing : 'Total army  125,000: 1667 CE; 200,000: 1677 C in FrBurbL
                    last_match = None
                    for match in re.finditer(var_regex, var_part):
                        last_match = match

                    if last_match.group(1).strip() == "Language" and '<span class="mw-headline" id="General_Description">General Description</span>' in var_part:
                        continue
                    good_key = text_for_split[11:] + polity
                    # som,etimes there is an unnecessary hashhtag: 'Alternate Religion Family#2'


                    with_potential_hashtag = last_match.group(1).strip()
                    without_pot_hshtag = with_potential_hashtag.split("#")[0]
                    mappings[good_key] = without_pot_hshtag
                    #print(f"{catches}")

    with open(f"ref_var_mappings_for_{html_files_root_dir}.json", "w") as outfile:
        json.dump(mappings, outfile)

    return mappings


def find_var_occurrences_with_refs(html_files_root_dir):
    """
    for each variable, go through all polities and find out how many references have been used for this var
    """
    with open(f"ref_var_mappings_for_{html_files_root_dir}.json", "r") as f:
        mappings = json.load(f)

    reverse_dic = {}
    for ref, var in mappings.items():
        if var in reverse_dic.keys():
            reverse_dic[var].append(ref)
        else:
            reverse_dic[var] = [ref,]

    # sort the dic 
    sorted_dict = dict(sorted(reverse_dic.items(), key=lambda item: len(item[1]), reverse=True))

    
    with open(f"var_ref_mappings_for_{html_files_root_dir}.json", "w") as outfile:
        json.dump(sorted_dict, outfile)

    return sorted_dict
    


def html_maker_nlp(file_dir):
    """
    creates the html files for reports on NLP datapoints
    and fills it up
    """
    #my_mappings = map_ref_to_var(file_dir, ALL_POLITIES=True)
    my_reverse_dic = find_var_occurrences_with_refs(file_dir)


    with open("a_dic_with_info_on_children_for_seshat_info_Jul_22.json", "r") as my_file:
        full_info_dic = json.load(my_file)

    # surprisingly, this is the one that has all the keys
    with open("all_citations_with_duplicates_indicated_for_seshat_info_Jul_22.json", "r") as my_file:
        dupl_info_dic = json.load(my_file)

    if file_dir == "seshat_browser_Jan_30_2023":
        active_tag_1 = ""
        active_tag_2 = "active"
    elif file_dir == "seshat_info_Jul_22":
        active_tag_1 = "active"
        active_tag_2 = ""
    all_my_rows = [f"""
{{% extends "core/seshat-base.html" %}}
{{% load static %}}
{{% load humanize %}}

{{% block content %}}
<div class="container">
<h1 class="pt-3 "> NLP Datapoints</h1>
<h3 class="pt-1"> This is the room for our more discussions on NLP.</h3>

<ul class="nav nav-pills nav-fill py-3">
    <li class="nav-item">
     </li>
     <li class="nav-item text-success">
        <a class="nav-link {active_tag_1}" href="{{% url 'nlp_datapoints'%}}"><h5>Wiki</h5>  (seshat.info)</a>
      </li>
      <li class="nav-item">
            <a class="nav-link {active_tag_2}"  href="{{% url 'nlp_datapoints_2'%}}"> <h5>Browser</h5>     (seshatdatabank.info)</a>
      </li>
    <li class="nav-item">
    </li>
  </ul>
<div class="row">
    <div class="table-responsive col-md-12">
        <table id="table_id" class="table align-middle table-hover table-striped table-bordered" style="padding: 0.25 rem !important;">
            <thead>
            <tr>
                <th scope="col" class="text-secondary" style="text-align: center">#</th>
                <th class="col-md-2 fw-light" scope="col" style="text-align: left"> 
                    Variable </th>
                <th scope="col" style="text-align: center" class="fw-light">
                        Citations
                    </th>
                <th scope="col" style="text-align: center" class="fw-light">
                DataPoints
                </th>
                <th scope="col" style="text-align: center" class="fw-light">has Zotero? (visible)</th>
                <th scope="col" style="text-align: center" class="fw-light">has pages?</th>
                <th scope="col" style="text-align: center" class="fw-light">1-page</th>
                <th scope="col" style="text-align: center" class="fw-light">(2-5) pages</th>
                <th scope="col" style="text-align: center" class="fw-light">6+ pages</th>
                <th scope="col" style="text-align: center" class="fw-light">has PDF</th>
                <th scope="col" style="text-align: center" class="fw-light">PDF <i class="fa-solid fa-arrow-right-long"></i> TXT</th>
            </tr>
            </thead>
            <tbody style="text-align: center">
    """,]
    count = 1
    bad_sectors=0
    for kk, vv in my_reverse_dic.items():
        # analyze the data using the other json files
        # check if it is a duplicate
        has_pages_count = 0
        has_pages_1_count = 0
        has_pages_count_2_5 = 0
        has_pages_count_5 = 0

        has_vis_zotero_count = 0
        for a_v in vv:
            # if file_dir=="seshat_info_Jul_22" and a_v == "REF_36_IrAwanE" or a_v == "REF_37_IrAwanE" or a_v == "REF_16_FrCaptL" or a_v == "REF_79_TrBrzMD" or a_v == "REF_80_TrBrzMD" or a_v == "REF_16_UzSogdi" or a_v == "REF_554_TrOttm2" or a_v == "REF_555_TrOttm2" or a_v == "REF_24_IrSasn1":
            #     continue
            the_v = dupl_info_dic.get(a_v)
            if the_v is None:
                # Important to check why we have those badies
                bad_sectors+=1
                continue
            if "IS_DUPLICATE_" in the_v:
                # extract the mother of this
                mother_ref = the_v[13:]
                has_pages = full_info_dic[mother_ref][0].get("hasVisiblePages")
                has_vis_zotero = full_info_dic[mother_ref][0].get("hasVisibleZotero")
                if has_vis_zotero:
                    print("****")
                    print(full_info_dic[mother_ref][0])
                    has_vis_zotero_count+=1

                if has_pages == True:
                    has_pages_count+=1
                    # fix the pages:
                    original_page_from = full_info_dic[mother_ref][0].get("page_from")
                    original_page_to = full_info_dic[mother_ref][0].get("page_to")
                    if original_page_from:
                        if len(original_page_from) - len(original_page_to) == 1:
                            original_page_to = original_page_from[0] + original_page_to
                        elif len(original_page_from) - len(original_page_to) == 2:
                            original_page_to = original_page_from[0:2] + original_page_to
                        elif len(original_page_from) - len(original_page_to) == 3:
                            original_page_to = original_page_from[0:3] + original_page_to
                        page_dif = int(original_page_to) - int(original_page_from)
                        if page_dif == 0:
                            has_pages_1_count+=1
                        elif page_dif >=1 and page_dif <= 4:
                            has_pages_count_2_5+=1
                        elif page_dif >= 5:
                            has_pages_count_5+=1
                        elif page_dif <0:
                            print("__PROBLEMATIC__")
                            print(full_info_dic[mother_ref][0])
            else:
                has_pages = full_info_dic[a_v][0].get("hasVisiblePages")
                has_vis_zotero = full_info_dic[a_v][0].get("hasVisibleZotero")
                if has_vis_zotero:
                    has_vis_zotero_count+=1
                if has_pages == True:
                    has_pages_count+=1
                    # fix the pages:
                    original_page_from = full_info_dic[mother_ref][0].get("page_from")
                    original_page_to = full_info_dic[mother_ref][0].get("page_to")
                    if original_page_from:
                        if len(original_page_from) - len(original_page_to) == 1:
                            original_page_to = original_page_from[0] + original_page_to
                        elif len(original_page_from) - len(original_page_to) == 2:
                            original_page_to = original_page_from[0:2] + original_page_to
                        elif len(original_page_from) - len(original_page_to) == 3:
                            original_page_to = original_page_from[0:3] + original_page_to
                        page_dif = int(original_page_to) - int(original_page_from)
                        if page_dif == 0:
                            has_pages_1_count+=1
                        elif page_dif >=1 and page_dif <= 4:
                            has_pages_count_2_5+=1
                        elif page_dif >= 5:
                            has_pages_count_5+=1
                        elif page_dif <0:
                            print("__PROBLEMATIC__")
                            print(full_info_dic[mother_ref][0])

        my_template = f"""
                    <tr>
                        <td class="text-secondary" scope="row">{count}</td>
                        <td class="fw-bold"><h5 class="mt-1 text-teal" style="text-align: left">{kk}</h5></td>
                        <td class="fw-bold">{len(vv)}</td>
                        <td></td>
                        <td>X ({has_vis_zotero_count})</td>
                        <td>{has_pages_count}</td>
                        <td>{has_pages_1_count}</td>
                        <td>{has_pages_count_2_5}</td>
                        <td>{has_pages_count_5}</td>
                        <td></td>
                        <td></td>
                    </tr>"""
        count+=1
        all_my_rows.append(my_template)
        
    all_my_rows.append("""
                </tbody>
            </table>
        </div>
    
    </div>

    {% endblock %}
    """)
    full_string = "".join(all_my_rows)
    with open(f"to_be_transported_to_django_{file_dir}.html", "w", encoding='utf-8') as fw:
        fw.write(full_string)
    print(f"Bad Sectors: {bad_sectors}")


def html_nlp_table_filler():
    """
    Let's fill up the tables
    """
    with open("a_dic_with_info_on_children_for_seshat_info_Jul_22.json", "r") as my_file:
        full_info_dic = json.load(my_file)

    # surprisingly, this is the one that has all the keys
    with open("all_citations_with_duplicates_indicated_for_seshat_info_Jul_22.json", "r") as my_file:
        dupl_info_dic = json.load(my_file)



def sc_variables_extractor():
    """
    - Goes through all the Wiki pages
    - Finds all the General Variable Sections
    - Puts all the Unique Variables in a list
    - returns the list of unique genearl description variables
    """
    READ_FROM_LOCAL = True

    UNIQUE_SC_VARS = ['RA', 'Polity territory', 'Polity Population', 'Population of the largest settlement', 'Settlement hierarchy', 'Administrative levels', 'Religious levels', 'Military levels', 'Professional military officers', 'Professional soldiers', 'Professional priesthood', 'Full-time bureaucrats', 'Examination system', 'Merit promotion', 'Specialized government buildings', 'Formal legal code', 'Judges', 'Courts', 'Professional Lawyers', 'irrigation systems', 'drinking water supply systems', 'markets', 'food storage sites', 'Roads', 'Bridges', 'Canals', 'Ports', 'Mines or quarries', 'Mnemonic devices', 'Nonwritten records', 'Written records', 'Script', 'Non-phonetic writing', 'Phonetic alphabetic writing', 'Lists, tables, and classifications', 'Calendar', 'Sacred Texts', 'Religious literature', 'Practical literature', 'History', 'Philosophy', 'Scientific literature', 'Fiction', 'Articles', 'Tokens', 'Precious metals', 'Foreign coins', 'Indigenous coins', 'Paper currency', 'Couriers', 'Postal stations', 'General postal service']

    unique_vars_underlined = [my_var.replace(" ", "_").lower() for my_var in UNIQUE_SC_VARS]

    # UNIQUE_GEN_VARS = ['RA', 'UTM zone', 'Original name ', 'Alternative names ', 'Peak Date ', 'Duration ', 'Degree of centralization', 'Supra-polity relations', 'Capital ', 'Language ', 'Linguistic family ', 'Religion Genus', 'Religion Family', 'Religion', 'preceding (quasi)polity ', 'relationship to preceding (quasi)polity', 'succeeding (quasi)polity ', 'Supracultural entity', 'scale of supra-cultural interaction', 'Alternate Religion Genus', 'Expert', 'Alternate Religion Family', 'Alternate Religion Genus2', 'Editor', 'Alternate Religion Family2', 'Alternate Religion Genus3', 'Alternate Religion', 'Linguistic Family', 'Language Genus', 'Religious Tradition', 'Alternate Religion Family3', 'Alternate Religion2']

    #UNIQUE_GEN_VARS = ['Language Genus']
    my_politys = []
    with open("polity_ngas.csv", 'r') as pol_csv:
        csv_reader = csv.reader(pol_csv, delimiter=',')
        for row in csv_reader:
            my_politys.append(row[1])
    
    # the dic with all the dataframes for variables and values
    big_dic ={}

    for var in UNIQUE_SC_VARS:
        var_name = var.replace(" ", "_").lower()
        values_df = pd.DataFrame(columns = [var_name, 'polity', 'wiki_value', 'wiki_desc'])
        refs_df = pd.DataFrame(columns = [var_name, 'polity', 'wiki_ref_raw', 'wiki_ref_augmented'])
        big_dic[var_name] = {
            "values_df": values_df,
            "refs_df": refs_df
        }

    for polity in my_politys:
        #print(polity)

        if READ_FROM_LOCAL:
            with open(f"html_files_sc/full_sc_{polity}.html", "r", encoding='utf-8') as f:
                source= f.read()
            soup = BeautifulSoup(source, 'lxml')
            soup_new = soup.find_all('div' , class_ = 'meatypart')

        else:
            source_url_seshatdb = 'http://seshatdatabank.info/browser/' 
            source_url = source_url_seshatdb + polity

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:55.0) Gecko/20100101 Firefox/55.0',
            }
            #source = requests.get(source_url, headers=headers).text
            source = requests.get(source_url, headers=headers)
            soup = BeautifulSoup(source.content.decode('utf-8'), 'lxml')

        #print(polity, end=",")
        for soup_section in soup_new:
            VarRegex = re.compile(r'♠ (.*?) ♣(.*?)♥')
            full_text = str(soup_section.text)
            catch = VarRegex.search(full_text)
            if catch:
                var_name_scraped = catch.group(1).strip().replace(" ", "_").lower()
                if var_name_scraped in unique_vars_underlined:
                    pot_desc_split = full_text.split('♥')
                    if len(pot_desc_split) > 1 and pot_desc_split[1].strip():
                        wiki_desc = pot_desc_split[1].strip()
                    else:
                        wiki_desc = "NO_DESCRIPTION_ON_WIKI"

                    if catch.group(2).strip():
                        wiki_value = catch.group(2).strip()
                    else:
                        wiki_value = "NO_VALUE_ON_WIKI"
                    
                    if wiki_value != "NO_VALUE_ON_WIKI" or wiki_desc != "NO_DESCRIPTION_ON_WIKI":
                        #print("Yooop")
                        big_dic[var_name_scraped]["values_df"] = big_dic[var_name_scraped]["values_df"].append({
                                var_name_scraped : var_name_scraped,
                                'polity': polity,
                                'wiki_value': wiki_value,
                                'wiki_desc': wiki_desc
                                }, ignore_index = True)


            #print("_____")

            
        # END OF FILE  
    return big_dic

###########################################



def polity_mapper_maker(csv_file, local=True):
    """
    This function assumes an updated CSV file for both local and AWS versions of the databse. 
    """
    root_dir = os.getcwd()
    if local:
        polity_csv_df = pd.read_csv(root_dir + "/" + csv_file)
    else:
        polity_csv_df = pd.read_csv(root_dir + "/CSV_AWS" +csv_file)
    polity_mapper_dic = {}
    for index, row in enumerate(polity_csv_df.iterrows()):
        polity_mapper_dic[row[1]['name']] = row[1]['id']
    return polity_mapper_dic



