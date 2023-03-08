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
        my_politys = ["AfKidar",]
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
                    if last_match.group(1).strip() == "Expert" and 'Description of the Normative Ideology' in var_part:
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





def nlp_full_datapoint_extarctor(html_files_root_dir, ALL_POLITIES=False):
    """
    Goes through the augmented html files and maps each ref to a corresponding variable inside the card game symbols and all.
    """
    with open(f"all_citations_with_duplicates_indicated_for_{html_files_root_dir}.json", "r") as my_file:
        dupl_info_dic = json.load(my_file)
    with open(f"a_dic_with_info_on_children_for_{html_files_root_dir}.json", "r") as my_file:
        full_info_dic = json.load(my_file)
    
    #make a simple REF_123_AfdUrrn --- > Coady Bads and goodss of life 23-24:
    ref_number_ref_text_mapper = {}
    for k_all, v_all in dupl_info_dic.items():
        if "IS_DUPLICATE_" in v_all:
            # extract the mother of this
            mother_ref = v_all[13:]
            for index1, a_ref in enumerate(full_info_dic[mother_ref]):
                if a_ref["originalText"] == "SAME_AS_TRIMMED":
                    ref_number_ref_text_mapper[k_all + "_" + str(index1+1)] = [ a_ref["trimmedText"], a_ref["trimmedText"]]
                else:
                    ref_number_ref_text_mapper[k_all+ "_" + str(index1+1)] = [ a_ref["originalText"], a_ref["trimmedText"]]
        # if it is not a duplicate, still go and get the data from the other dic
        else:
            for index2, a_ref in enumerate(full_info_dic[k_all]):
                if a_ref["originalText"] == "SAME_AS_TRIMMED":
                    ref_number_ref_text_mapper[k_all + "_" + str(index2+1)] = [ a_ref["trimmedText"], a_ref["trimmedText"]]
                else:
                    ref_number_ref_text_mapper[k_all+ "_" + str(index2+1)] = [ a_ref["originalText"], a_ref["trimmedText"]]

    if not ALL_POLITIES:
        my_politys = ["AfKidar",]
    else:
        my_politys = []
        with open("csv_files/polity_ngas.csv", 'r') as pol_csv:
            csv_reader = csv.reader(pol_csv, delimiter=',')
            for row in csv_reader:
                my_politys.append(row[1])
    mappings = {}
    #candidates = []
    for polity in my_politys:
        with open(f"html_files/{html_files_root_dir}_augmented/full_nlp_{polity}.html", "r", encoding='utf-8') as f:
            source= f.read()
            #print(source)
            #var_regex = re.compile("♠(.*)♣")
            ref_regex = re.compile("\[MAJIDBENAM_REF_(\d{1,4})_")
            catches_all_0 = ref_regex.finditer(source)

            # make the source better
            if catches_all_0:
                for index, catches in enumerate(catches_all_0):
                    source = source.replace(f"[MAJIDBENAM_REF_{catches.group(1)}_{polity}]", f"[JIDBEN_REF_{catches.group(1)}_{polity}_JIDBEN]")
            
            # fix the spaces (etc.) between consecutive refs:
            for in_between in [' , ', ',', ', ', '"', '. ', '.', ' .', ')', '; ', ' ']:
                source = source.replace("JIDBEN]" + in_between + "[JIDBEN", "JIDBEN][JIDBEN")

            ref_regex = re.compile("\[JIDBEN_REF_(\d{1,4})_")
            catches_all = ref_regex.finditer(source)
            #print(source)
            if catches_all:
                for index, catches in enumerate(catches_all):
                    # text to be used for splitting
                    text_for_split = f"[JIDBEN_REF_{catches.group(1)}_"
                    var_part = source.split(text_for_split)[0]
                    #print(var_part)
                    var_regex = re.compile("♠(.*?)♣")
                    # ♣ missing in ♠ Largest fielded army {670,000; 1,133,800} ♥"Th ... in CnSui**
                    #  ♣ missing : 'Total army  125,000: 1667 CE; 200,000: 1677 C in FrBurbL
                    last_match = None
                    for match in re.finditer(var_regex, var_part):
                        last_match = match



                    if last_match.group(1).strip() == "Language" and '<span class="mw-headline" id="General_Description">General Description</span>' in var_part:
                        continue
                    if last_match.group(1).strip() == "Expert" and 'Description of the Normative Ideology' in var_part:
                        continue

                    # make the key
                    good_key = text_for_split[8:] + polity
                    # sometimes there is an unnecessary hashhtag: 'Alternate Religion Family#2'

                    with_potential_hashtag = last_match.group(1).strip()
                    without_pot_hshtag = with_potential_hashtag.split("#")[0]
                    # without_pot_hashtag gives the variable name,
                    # we want the value and the description as well.
                    
                    # we still have the var_part:
                    desc_part = var_part.split("♥")[-1]
                    value_part = var_part.split("♥")[-2]

                    my_value = value_part.split("♣")[1]
                    # check if the ref just smaller than our ref is on the way:
                    disturbing_ref = f"[JIDBEN_REF_{int(catches.group(1))-1}_{polity}_JIDBEN]"
                    # if there is no other occurrence of "JIDBEN_REF_xyz_" report:
                    if disturbing_ref not in desc_part:
                        desc_part_good = desc_part
                        #print(text_for_split[11:] + polity, f": {without_pot_hshtag} --> {my_value}) ::::", desc_part_good)
                        #print("________")
                        # all good, report the desc
                    else:
                        # a better desc_part is the cut-off from the last to this ref:
                        desc_part_good = desc_part.split(disturbing_ref)[1]

                        #print(text_for_split[11:] + polity, f":{without_pot_hshtag} --> {my_value}) ::::", desc_part_good)
                        #print("________")

                    # clean up the desc_part_good
                    desc_part_best = desc_part_good.replace("<i>", "").replace("</i>", "").replace("<b>", "").replace("</b>", "").replace("</div>", "").replace("<div>", "").replace("[MAJIDBENAM_BR]", "[MJD_BR]").strip()
                    
                    # two refs after each other
                    # if without_pot_hshtag != "Moralizing enforcement is agentic" and f"[JIDBEN_REF_{int(catches.group(1))-1}_{polity}][JIDBEN_REF_{int(catches.group(1))}_{polity}]" in desc_part+f"[JIDBEN_REF_{int(catches.group(1))}_{polity}]":
                    #     print(f"WARNING: TWO Refs after each other: {good_key}" )

                    # refs after each other
                    if without_pot_hshtag != "Moralizing enforcement is agentic" and f"[JIDBEN_REF_{int(catches.group(1))-1}_{polity}_JIDBEN][JIDBEN_REF_{int(catches.group(1))}_{polity}_JIDBEN]" in desc_part+f"[JIDBEN_REF_{int(catches.group(1))}_{polity}_JIDBEN]":
                        # then treat this as if the description is from the previous shit.
                        prev_text_for_split = f"[JIDBEN_REF_{int(catches.group(1)) -1}_"
                        previous_key = prev_text_for_split[8:] + polity + "_1"
                        try:
                            desc_part_best = mappings[previous_key]["description"]
                        except:
                            desc_part_best = "BAD_SECTOR_EXAMPLE"
                            print(f"{previous_key} ---> not found.")
                        #print(f"WARNING: Three Refs after each other: {good_key}" )
                    
                    #if len(desc_part_best) > 5000:
                    #    print(f"WARNING: Tooooo long of a Description. {good_key}" )
                    #    print(desc_part_best)
                    
                    # if len(desc_part_best) < 3 and without_pot_hshtag != "Moralizing enforcement is agentic":
                    #     print(f"WARNING: Very Short Description. {good_key}" )
                    # if "meatypart" in desc_part_best:
                    #     print(f"WARNING: Meaty Part Div in Description. {good_key}" )

                    #print(good_key, f": {without_pot_hshtag} -->{my_value}::::", desc_part_best)
                    #print("________")

                    # There are some bad sectors:
                    for i in [1,2,3]:
                        new_key = good_key+ "_" + str(i)
                        if new_key in ref_number_ref_text_mapper.keys():
                            #print(new_key)
                            mappings[new_key] = {
                                "variable": without_pot_hshtag.strip(),
                                "value": my_value.strip(),
                                "polity": polity,
                                "description": desc_part_best,
                                "citation_text": ref_number_ref_text_mapper[new_key][0], 
                                "citation_text_trimmed": ref_number_ref_text_mapper[new_key][1],
                                }
                    #print(f"{catches}")

    with open(f"nlp_full_mappings_{html_files_root_dir}.json", "w") as outfile:
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

def seshat_ref_to_zotero_id_fixer(ref_dics_list, augnmented_zotro_dic):
    """
    updates (populates) ref_zot_id_dic with matches
    """
    for ref_dic in ref_dics_list:
        if not ref_dic['hasVisibleZotero']:
            cross_check_string_ref = ref_dic["trimmedText"].lower()
            # go through all zotero files:
            for zot_id, a_ref in augnmented_zotro_dic.items():
                # we KNOW that everything has a title.
                a_title =  a_ref.get("title")
                authors_list = a_ref.get("authors")
                a_year = a_ref.get("year")

                # Let's go through all the authors
                if authors_list and a_year:
                    for an_author in authors_list:
                        # even if one author is in we are happy 100 %
                        # we are also 100% happy if the title is longer than 15
                        if len(an_author) > 4 and an_author in cross_check_string_ref and len(a_title) > 15 and a_title in cross_check_string_ref and a_year in cross_check_string_ref:
                            print("100%", end=", ")
                            return zot_id

def seshat_ref_to_zotero_id_fixer_second_third_chance(reppecharge_dic_item, augnmented_zotro_dic):
    """
    updates (populates) ref_zot_id_dic with matches (second and third chance)
    """
    if "second_chance" in reppecharge_dic_item.keys():
        cross_check_string_ref = reppecharge_dic_item["second_chance"][0].lower()
    elif "third_chance" in reppecharge_dic_item.keys():
        cross_check_string_ref = reppecharge_dic_item["third_chance"][0].lower()
    else:
        return
    # go through all zotero files:
    for zot_id, a_ref in augnmented_zotro_dic.items():
        # we KNOW that everything has a title.
        a_title =  a_ref.get("title")
        authors_list = a_ref.get("authors")
        a_year = a_ref.get("year")

        # Let's go through all the authors
        if authors_list and a_year:
            for an_author in authors_list:
                # even if one author is in we are happy 100 %
                # we are also 100% happy if the title is longer than 15
                if len(an_author) > 4 and an_author in cross_check_string_ref and len(a_title) > 15 and a_title in cross_check_string_ref and a_year in cross_check_string_ref:
                    print("(100%)", end=", ")
                    return zot_id

def make_99_percent_zotero_guesses(file_dir, zotero_json_file):
    """
    We will go through all the longer dics where we have all the info and try to augment the 
    Zotero situation
    """

    with open(f"a_dic_with_info_on_children_for_{file_dir}.json", "r") as my_file:
        full_info_dic = json.load(my_file)

    with open(f"citations_of_max_length_50_with_second_and_third_chances_for_{file_dir}.json", "r") as my_file2:
        second_and_third_chance_dic = json.load(my_file2)

    # "Seshat_Databank_jan_23.json"
    with open(zotero_json_file, "r") as my_zotero_file:
        zotero_dic_list = json.load(my_zotero_file)

    augnmented_zotro_dic = {}
    for a_ref in zotero_dic_list:
        # we KNOW that everything has a title.
        an_id = a_ref.get("id").split("/")[-1]
        inner_dic_for_value = {}
        a_title =  a_ref.get("title").lower()
        # Not everything has an author list
        authors_list = a_ref.get("author")
        list_of_authors_family_names = []
        if authors_list:
            for author_dic in authors_list:
                pot_family_name = author_dic.get("family")
                if pot_family_name:
                    list_of_authors_family_names.append(pot_family_name.lower())
        # Not everything has a date
        date_dic = a_ref.get("issued")
        a_year = None     # in case nothing is found
        if date_dic:
            # take date-parts
            date_parts_list = date_dic.get("date-parts")
            if date_parts_list:
                a_date = date_parts_list[0]
                if a_date:
                    a_year = a_date[0]
        
        inner_dic_for_value["title"] = a_title
        inner_dic_for_value["authors"] = list_of_authors_family_names
        inner_dic_for_value["year"] = a_year

        augnmented_zotro_dic[an_id] = inner_dic_for_value
    # create a dic full of ref ----> zot_id matches
    ref_zot_id_dic = {}
    for ref_key, ref_dics_list in full_info_dic.items():
        pot_fix = seshat_ref_to_zotero_id_fixer(ref_dics_list, augnmented_zotro_dic)
        if pot_fix:
            ref_zot_id_dic[ref_key] = pot_fix
    # second and third chances:
    for ref_key, reppecharge_dic_item in second_and_third_chance_dic.items():
        if ref_key in ref_zot_id_dic.keys():
            continue
        pot_fix = seshat_ref_to_zotero_id_fixer_second_third_chance(reppecharge_dic_item, augnmented_zotro_dic)
        if pot_fix:
            ref_zot_id_dic[ref_key] = pot_fix
    
    with open(f"json_files/99_percent_ref_zot_matches_with_second_and_third_chances_{file_dir}.json", "w") as outfile:
        json.dump(ref_zot_id_dic, outfile)
    return ref_zot_id_dic


        

def html_maker_nlp(file_dir):
    """
    creates the html files for reports on NLP datapoints
    and fills it up
    """
    #my_mappings = map_ref_to_var(file_dir, ALL_POLITIES=True)
    my_reverse_dic = find_var_occurrences_with_refs(file_dir)


    with open(f"a_dic_with_info_on_children_for_{file_dir}.json", "r") as my_file:
        full_info_dic = json.load(my_file)

    # surprisingly, this is the one that has all the keys
    with open(f"all_citations_with_duplicates_indicated_for_{file_dir}.json", "r") as my_file:
        dupl_info_dic = json.load(my_file)

    with open(f"json_files/99_percent_ref_zot_matches_with_second_and_third_chances_{file_dir}.json") as f1:
        dic_99_percent = json.load(f1)

    # get all the mappings between ZOTERO ID s and the corresponding local repo (if available)
    with open("zotero_ids_to_local_repos_mapping.json", "r") as my_file:
        ids_to_local_dic = json.load(my_file)

    if file_dir == "seshat_browser_Jan_30_2023":
        active_tag_1 = ""
        active_tag_2 = "active"
    elif file_dir == "seshat_info_Jul_22":
        active_tag_1 = "active"
        active_tag_2 = ""
    all_my_rows_dic = {}
    all_my_rows = [f"""
{{% extends "core/seshat-base.html" %}}
{{% load static %}}
{{% load humanize %}}



{{% block content %}}
<div class="container">
<h1 class="pt-3 text-teal"><i class="fa-solid fa-people-group"></i> NLP Project Discussion Room</h1>
<h4 class="pt-3 text-success"><i class="fa-solid fa-chevron-right"></i> &nbsp; NLP DataPoints:</h4>
<h5><i class="fa-solid fa-circle-chevron-right"></i> Here are some examples of DataPoints (as per my understanding).</h5>
<h6>* There are lots of other options for metadata and how we can clean up and organize each unit of information in our project, but that should be a good starting point to start the discussion and fill up the gaps in future.</h6>

<div class="col-md-12">
    <div class="accordion accordion-flush" id="accordionExample">
        <div class="accordion-item" style="background-color:#fefae6;">
          <h2 class="accordion-header" id="headingOne">
            <button class="accordion-button collapsed px-0" type="button" data-bs-toggle="collapse" data-bs-target="#collapseOne" aria-expanded="false" aria-controls="collapseOne" style="background-color:#fefae6;">
              <span class="text-success fw-bold"><i class="fa-solid fa-chevron-right"></i>  &nbsp; NLP DataPoint Examples: (click to see)
              </span> 
            </button>
          </h2>
          <div id="collapseOne" class="accordion-collapse collapse" aria-labelledby="headingOne">
            <div class="accordion-body table-responsive p-0">
                <table id="table_id" class="table align-middle table-hover table-striped table-bordered" style="padding: 0.25 rem !important;">
                    <thead >
                        <tr class="sticky-md-top">
                        <span style="white-space: nowrap;">
                            <th class="fw-bold" scope="col" style="text-align: left"> 
                                Variable
                            <sup>
                    <span type="button"  tabindex="0" data-bs-toggle="popover" title="Variable" data-bs-html="true" data-bs-trigger="focus" data-bs-content='In Seshat, we have collected information on different aspects of past human societies. As the value of the gathered data varies from polity to polity and from time period to time period (even in one polity), we call these Variables.'>&nbsp;<i class="fa-regular fa-circle-question"></i></span>
                            </sup>
                            </span>

                             </th>
                            <th scope="col" style="text-align: center" class="fw-bold">
                                Value (confidence)
                            <sup>
                    <span type="button"  tabindex="0" data-bs-toggle="popover" title="Value (confidence)" data-bs-html="true" data-bs-trigger="focus" data-bs-content='Depending on the type of variable, the collected data can be a numerical range or simply information on the absence or presence of that variable. We also keep the information on whether the concluded value is "Evidenced", "Inferred", or "suspected".'>&nbsp;<i class="fa-regular fa-circle-question"></i></span>
                            </sup>
                            </th>
                            <th scope="col" style="text-align: center" class="fw-bold">
                                Polity
                                          <sup>
                    <span type="button"  tabindex="0" data-bs-toggle="popover" title="Polity" data-bs-html="true" data-bs-trigger="focus" data-bs-content='A polity is defined as an independent political unit. Kinds of polities range from villages (local communities) through simple and complex chiefdoms to states and empires. It's important to note that a polity has a duration and in many cases (if a specific time period is NOT associated with a variable, the full duration of its corresponding polity is assumed in our analyses.)'>&nbsp;<i class="fa-regular fa-circle-question"></i></span>
                            </sup>
                            </th>
                            <th scope="col" style="text-align: left" class="fw-bold col-md-3">Description
                                                                      <sup>
                    <span type="button"  tabindex="0" data-bs-toggle="popover" title="Description" data-bs-html="true" data-bs-trigger="focus" data-bs-content='Description is a the text added by the RA who inserted this particular datapoint into Seshat Website. It can be an exact quote from the reference he/she was referring to, or his/her understandig of the concept based on the text in the reference.'>&nbsp;<i class="fa-regular fa-circle-question"></i></span>
                            </sup>
                            </th>
                            <th scope="col" style="text-align: left" class="fw-bold">Extra Desc 
                                <sup>
                                    <span type="button"  tabindex="0" data-bs-toggle="popover" title="Extra Description" data-bs-html="true" data-bs-trigger="focus" data-bs-content='Some extra information added to the main description by the RA. This is also as per the RA's understanding and can add sentiment to the description. Extra description could have been taken from another part of the refernce that was not included in the main description'>&nbsp;<i class="fa-regular fa-circle-question"></i></span>
                                </sup>
                            </th>
                            <th scope="col" style="text-align: center" class="fw-bold">Exact Quote?
                                <sup>
                                    <span type="button"  tabindex="0" data-bs-toggle="popover" title="Exact Quote?" data-bs-html="true" data-bs-trigger="focus" data-bs-content='
                                    <i class="fa-solid fa-circle-check text-success"></i>: The text in the Description is and exact quote from the Citation it is referring to.
                                    <br>
                                    <i class="fa-solid fa-circle-xmark text-danger"></i>: The text in the Description is <b>NOT</b> an exact quote from the Citation it is referring to.'>&nbsp;<i class="fa-regular fa-circle-question"></i></span>
                                </sup>
                            </th>
                            <th scope="col" style="text-align: center" class="fw-bold">Citation</th>
                            <th scope="col" style="text-align: center" class="fw-bold">Zotero?</th>
                            <th scope="col" style="text-align: center" class="fw-bold">pages?</th>
                            <th scope="col" style="text-align: center" class="fw-bold">PDF?</th>
                            <th scope="col" style="text-align: center" class="fw-bold">TXT?</th>
                        </tr>
                        </thead>
               
                <tbody style="text-align: center">
                        <tr>
                            <td style="text-align: left"> 
                                Enslavement </td>
                            <td style="text-align: center">
                                present (Inferred)
                            </td>
                            <td style="text-align: center">
                                AfGhurd
                            </td>
                            <td style="text-align: left" class="col-md-3">"As many as 60,000 inhabitants of Ghazna were massacred, and according to the Ghurid chronicler, al-Juzjani, the prisoners were forced to carry building materials from Ghazna to Firuzkuh, where the mud was mixed with their blood to build the towers of Ghur."</td>
                            <td style="text-align: center">"At least temporarily."</td>
                            <td style="text-align: center"><i class="fa-solid fa-circle-check text-success"></i></td>
                            <td style="text-align: left"><i>
                                David Thomas. Firuzkuh. The summer capital of the Ghurids. Amira K Bennison. Alison L Gascoigne. eds. 2007. Cities in the Pre-Modern Islamic World: The Urban Impact of Religion, State and Society. Routledge. London.
                            </i> </td>
                            <td style="text-align: center"><i class="fa-solid fa-circle-check text-success"></i></td>
                            <td style="text-align: center"><i class="fa-solid fa-circle-xmark text-danger"></i></td>
                            <td style="text-align: center"><i class="fa-solid fa-circle-xmark text-danger"></i></td>
                            <td style="text-align: center"><i class="fa-solid fa-circle-xmark text-danger"></i></td>
                        </tr>
    
                        <tr>
                            <td style="text-align: left"> 
                                Destruction </td>
                            <td style="text-align: center">
                                present (Evidenced)
                            </td>
                            <td style="text-align: center">
                                AfGhurd
                            </td>
                            <td style="text-align: left" class="col-md-3">"Ala al-Din Husayn attacked Ghazna, capital of the eponymous Ghaznavid dynasty. The city reputedly burned for seven days, earning Ala al-Din the sobriquet 'Jahan-Suz' (World Incendiary)."</td>
                            <td style="text-align: center"><i class="fa-solid fa-circle-xmark text-danger"></i></td>
                            <td style="text-align: center"><i class="fa-solid fa-circle-check text-success"></i></td>
                            <td style="text-align: left"><i>
                                David Thomas. Firuzkuh. The summer capital of the Ghurids. Amira K Bennison. Alison L Gascoigne. eds. 2007. Cities in the Pre-Modern Islamic World: The Urban Impact of Religion, State and Society. Routledge. London.
                            </i> </td>
                            <td style="text-align: center"><i class="fa-solid fa-circle-check text-success"></i></td>
                            <td style="text-align: center"><i class="fa-solid fa-circle-xmark text-danger"></i></td>
                            <td style="text-align: center"><i class="fa-solid fa-circle-xmark text-danger"></i></td>
                            <td style="text-align: center"><i class="fa-solid fa-circle-xmark text-danger"></i></td>
                        </tr>
    
    
                        <tr>
                            <td style="text-align: left"> 
                                Destruction </td>
                            <td style="text-align: center">
                                present (Evidenced)
                            </td>
                            <td style="text-align: center">
                                AfGhurd
                            </td>
                            <td style="text-align: left" class="col-md-3">"In the 1170s the Ghurid ruler appointed his brother, Muhammad, governor of Ghaznah and encouraged him to raid in India. ... in alliance with a Hindu ruler, he reduced Lahore and replaced the last of the Ghaznavid dynasty."</td>
                            <td style="text-align: center"><i class="fa-solid fa-circle-xmark text-danger"></i></td>
                            <td style="text-align: center"><i class="fa-solid fa-circle-check text-success"></i></td>
                            <td style="text-align: left"><i>
                                (Hodgson 1977, 276) Marshall G S Hodgson. 1977. The Venture of Islam, Volume 2: The Expansion of Islam in the Middle Periods. Volume 2. University of Chicago Press. Chicago.
                            </i> </td>
                            <td style="text-align: center"><i class="fa-solid fa-circle-check text-success"></i></td>
                            <td style="text-align: center"><i class="fa-solid fa-circle-check text-success"></i></td>
                            <td style="text-align: center"><i class="fa-solid fa-circle-xmark text-danger"></i></td>
                            <td style="text-align: center"><i class="fa-solid fa-circle-xmark text-danger"></i></td>
                        </tr>
                        
                </tbody>
            </table>
            </div>
          </div>
        </div>

      </div>
  </div>


<h4 class="pt-3 text-success"> <i class="fa-solid fa-chevron-right"></i> &nbsp; Statistics of all the Variables on Seshat Websites</h4>

<h6 class="pt-3">* Note that Seshat has two old websites. One is <a href="https://seshat.info">Seshat.info</a> (aka Wiki) which serves as the place where all the facts go before being reviewed by Seshat Experts. The public Seshat Website is <a href="https://seshatdabank.info/databrowser">Seshatdatabank.info</a> (aka Browser) is where only the expert-reviewed data shows up. From my experince, most of the data on Wiki is also of great quality and can be used (with minimun extra effort) in our research projects, among which the current NLP project. For example, all the examples in the above table are taken from Wiki.</h6>
<h6 class="pt-1">* What you see below is the first draft of my analysis of all Seshat variables. As you can see there are so many gaps to be filled in order to take advantage of the full Seshat potential. Some gaps can (and will) be filled by me and Jakob, and for some other gaps, we need some expert and RA help. By filling the gaps, I mean, the process through which we reduce the difference between the current state of the data and the ideal super-clean database where every citation has a Zotero ID and page number and PDF files and correponding text.</h6>
<ul class="nav nav-pills nav-fill py-4">
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
                <th class="col-md-3 fw-bold" scope="col" style="text-align: left"> 
                    Variable </th>
                <th scope="col" style="text-align: center" class="fw-bold">
                        Citations
                    </th>
                <th scope="col" style="text-align: center" class="fw-bold text-success">
                DataPoints
                <sup>
                    <span type="button"  tabindex="0" data-bs-toggle="popover" title="Why smaller than citations?" data-bs-html="true" data-bs-trigger="focus" data-bs-content='DataPoints are smaller than Citations, because some of our citations are for example Personal Comments, and therefore not really useful for NLP project'>&nbsp;<i class="fa-regular fa-circle-question"></i></span>
                </sup>
                </th>
                <th scope="col" style="text-align: center" class="fw-bold text-success">has Zotero? (visible)</th>
                <th scope="col" style="text-align: center" class="fw-bold">has pages?</th>
                <th scope="col" style="text-align: center" class="fw-bold">1-page / (2-5) / 6+ </th>
                <th scope="col" style="text-align: center" class="fw-bold text-success">has PDF</th>
                <th scope="col" style="text-align: center" class="fw-bold text-success">PDF <i class="fa-solid fa-arrow-right-long"></i> TXT</th>
            </tr>
            </thead>
            <tbody style="text-align: center">
    """,]
    count = 1
    bad_sectors=0
    for kk, vv in my_reverse_dic.items():
        if kk in ["RA", "Expert", "Editor",]:
            continue
        # analyze the data using the other json files
        # check if it is a duplicate
        has_pages_count = 0
        has_pages_1_count = 0
        has_pages_count_2_5 = 0
        has_pages_count_5 = 0

        has_concluded_zotero = 0
        has_vis_zotero_count = 0
        has_PDF = 0
        has_TXT = 0

        has_pers_comm = 0
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
                pdf_avialable_0 = full_info_dic[mother_ref][0].get("zoteroID")
                is_pers_comm =  full_info_dic[mother_ref][0].get("hasPersonalComment") 

                if is_pers_comm:
                    has_pers_comm+=1
                
                if pdf_avialable_0:
                    my_zotero_id = pdf_avialable_0[0]
                    if my_zotero_id in ids_to_local_dic.keys():
                        has_PDF+=1
                        if ids_to_local_dic[my_zotero_id] != "NO_USEABLE_PDF":
                            has_TXT+=1
                 
                if has_vis_zotero:
                    print("****")
                    print(full_info_dic[mother_ref][0])
                    has_vis_zotero_count+=1

                # concluded zotero
                if mother_ref in dic_99_percent.keys():
                    zot_99 = dic_99_percent[mother_ref]
                    has_concluded_zotero+=1
                    if zot_99 in ids_to_local_dic.keys():
                        has_PDF+=1
                        if ids_to_local_dic[zot_99] != "NO_USEABLE_PDF":
                            has_TXT+=1

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
                pdf_avialable_0 = full_info_dic[a_v][0].get("zoteroID")
                is_pers_comm =  full_info_dic[a_v][0].get("hasPersonalComment") 

                if is_pers_comm:
                    has_pers_comm+=1

                if pdf_avialable_0:
                    my_zotero_id = pdf_avialable_0[0]
                    if my_zotero_id in ids_to_local_dic.keys():
                        has_PDF+=1
                        if ids_to_local_dic[my_zotero_id] != "NO_USEABLE_PDF":
                            has_TXT+=1

                if has_vis_zotero:
                    has_vis_zotero_count+=1

                # concluded zotero
                if a_v in dic_99_percent.keys():
                    zot_99 = dic_99_percent[a_v]
                    has_concluded_zotero+=1
                    if zot_99 in ids_to_local_dic.keys():
                        has_PDF+=1
                        if ids_to_local_dic[zot_99] != "NO_USEABLE_PDF":
                            has_TXT+=1

                if has_pages == True:
                    has_pages_count+=1
                    # fix the pages:
                    original_page_from = full_info_dic[a_v][0].get("page_from")
                    original_page_to = full_info_dic[a_v][0].get("page_to")
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
                            print(full_info_dic[a_v][0])

        my_template = f"""
                    <tr>
                        <td class="text-secondary" scope="row">{count}</td>
                        <td class="fw-bold"><h5 class="mt-1 text-teal" style="text-align: left">{kk}</h5></td>
                        <td>{len(vv)}</td>
                        <td class="fw-bold text-success">{len(vv) - has_pers_comm}</td>
                        <td class="fw-bold text-success">{has_vis_zotero_count + has_concluded_zotero} ({has_vis_zotero_count})</td>
                        <td>{has_pages_count}</td>
                        <td>{has_pages_1_count} / {has_pages_count_2_5} / {has_pages_count_5}</td>
                        <td class="fw-bold text-success">{has_PDF}</td>
                        <td class="fw-bold text-success">{has_TXT}</td>
                    </tr>"""
        count+=1
        all_my_rows.append(my_template)
        # update the dictionary:
        all_my_rows_dic[kk] = {
            "citations": len(vv),
            "datapoints": len(vv) - has_pers_comm,
            "has_zotero": has_vis_zotero_count + has_concluded_zotero,
            "has_pages": has_pages_count,
            "has_1_page": has_pages_1_count,
            "has_2_5_pages": has_pages_count_2_5,
            "has_6_plus_pages": has_pages_count_5,
            "has_PDF": has_PDF,
            "has_TXT": has_TXT,
        }

        
    all_my_rows.append("""
                </tbody>
            </table>
        </div>
    
    </div>
    <script>
        var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'))
        var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
          return new bootstrap.Popover(popoverTriggerEl)
        })
    </script>
    {% endblock %}
    """)
    full_string = "".join(all_my_rows)
    with open(f"to_be_transported_to_django_{file_dir}.html", "w", encoding='utf-8') as fw:
        fw.write(full_string)
    
    with open(f"json_files/nlp_statistics_for_{file_dir}.json", "w") as my_file:
        json.dump(all_my_rows_dic, my_file)
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



