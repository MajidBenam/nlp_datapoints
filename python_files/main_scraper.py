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

def ref_span_replacer(my_str, polity_name):
    RefRegex = re.compile('<sup class="reference" id="cite_ref-(\d{1,4})"><a href="#cite_note-(\d{1,4})">\[(\d{1,4})\]</a></sup>')
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
            final_html_after_ref_replacement = ref_span_replacer(better_html, polity)
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
    Returns all sc variables as seen even once on html pages of the seshatdatabank.info"""
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



