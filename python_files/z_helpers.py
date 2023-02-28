import requests
import csv
import re
import json
import time
import pandas as pd
import copy
import os

#TODO : Make sure that all combinations of disputed_x_y, uncertain_inferred_x_and_y  are captured
# TODO: TrByzM3 and IrPart1---> Polity_population regarding the detection of dispute when { appears

# TODO: population_of_the_largest_settlement: ---> EgOldK1, GhAshnL, ItPapM2, TrByzM2, UsIroqE, UsIroqL

def polity_mapper_maker(csv_file, local=True):
    """
    This function assumes an updated CSV file for both local and AWS versions of the databse. 
    """
    root_dir = os.getcwd()
    if local:
        polity_csv_df = pd.read_csv(root_dir + "/" + csv_file)
    else:
        polity_csv_df = pd.read_csv(root_dir + "/CSV_AWS/" +csv_file)
    polity_mapper_dic = {}
    for index, row in enumerate(polity_csv_df.iterrows()):
        polity_mapper_dic[row[1]['name']] = row[1]['id']
    return polity_mapper_dic

# 
def var_col_dic_nmaker(ALL_GENERAL_VARS_LIST, ALL_GENERAL_COLS_LIST):
    mother_dic = {}
    for var_dic in ALL_GENERAL_VARS_LIST:
        new_entries = []
        for col_dic in ALL_GENERAL_COLS_LIST:
            if var_dic["varname"] == col_dic["varname"] and col_dic["colname"] not in new_entries:
                new_entries.append(col_dic["colname"])
        mother_dic[var_dic["varname"]] = new_entries
    return mother_dic


def dispute_finder_curly_bracket(pretty_ultimate_dic_with_conf_disp):
    """
    checks to see if there are dipsutred values as expressed by the use of {
    this happens here in social com variables:
    polity_population ----> TrByzM3 and IrPart1
    population_of_the_largest_settlement: ---> EgOldK1, GhAshnL, ItPapM2, TrByzM2, UsIroqE, UsIroqL

    ONCE detetcted they can probably be taken care of manually as well.
    """
    df = pretty_ultimate_dic_with_conf_disp["population_of_the_largest_settlement"]
    cond = df["raw"].str.contains("{")
    filtered_df = df[cond]
    return filtered_df
    
def gen_vars_mapper(ultimate_dic):
    gen_var_mapper = {}
    for var_old in ultimate_dic.keys():
        if var_old == 'peak_date':
            gen_var_mapper[var_old] = 'politypeakyears'
            continue
        elif var_old == 'ra':
            gen_var_mapper[var_old] = 'polityresearchassistant'
            continue
        elif var_old == 'alternative_names':
            gen_var_mapper[var_old] = 'polityalternativename'
            continue
        elif var_old == 'succeeding_(quasi)polity':
            gen_var_mapper[var_old] = 'politysucceedingentity'
            continue
        elif var_old == 'preceeding_(quasi)polity':
            gen_var_mapper[var_old] = 'politypreceedingentity'
            continue
        var_new = "polity" + var_old.replace("_", "").replace("(", "").replace(")", "").replace("-", "")
        gen_var_mapper[var_old] = var_new
    return gen_var_mapper


def value_in_col_finder(pretty_ultimate_dic, col_name, search_str):
    """
    Function to use to see if a column in a df contains a particular string
    """
    for index, row in pretty_ultimate_dic[col_name]["values_df"].iterrows():
        if search_str in row.wiki_raw:
            print(str(row.polity), "---->", row.wiki_raw) 

### Define functions that go through scraped dfs and decide on what they are and how they should be put in the database

 ###### yearRegEx finder:

def is_there_years_here(my_str):
    """"
    INPUT: Receives a_str and decided on the BCE and Ce information inside it and returns a [-123, 498] list of values for year_from and year_to vals
    """
    #print("______")
    #print(my_str)
    stripped_str = my_str.strip()
    my_catches = re.findall('(-?\d{1,5})[ ]{0,1}([B|b]*[C|c][E|e]*)*[ ]{0,1}[-|_| ][ ]{0,1}(\d{1,5})[ ]{0,1}([B|b]*[C|c][E|e]*)*', stripped_str)
    if len(my_catches) > 1:
        print(f"Catches are more than 1: {len(my_catches)}")
        return None
    elif len(my_catches) == 0:
        # try the single year option:
        my_catches_single  = re.findall('(-?\d{1,5})[ ]{0,1}([B|b]*[C|c][E|e]*)', stripped_str)
        if len(my_catches_single) == 1:
            year_from = my_catches_single[0][0]
            year_from_tag = my_catches_single[0][1]
            if year_from_tag == "BCE":
                #print(f"YEAR_FROM: {-int(year_from)}, SINGLE!!!")
                return [-int(year_from), -int(year_from)]
            elif year_from_tag in ["CE", "ce"] or year_from_tag in ["", " "]:
                #print(f"YEAR_FROM: {int(year_from)}, SINGLE!!!")
                return [int(year_from), int(year_from)]
            else:
                print(my_str)
                print(f"\x1b[31m Weird TAg for year_from: {year_from_tag} \x1b[0m")
                return [None, None]
        else:
            #print(f"\x1b[31m Bad number of matches: {len(my_catches)} \x1b[0m")
            return [None, None]
    else:
        # year_from
        year_from = my_catches[0][0]
        year_from_tag = my_catches[0][1]
        year_to = my_catches[0][2]
        year_to_tag = my_catches[0][3]
        if "-" in year_from:
            print(f"Attention. the value year_from has a negative value: {year_from}")
        if "-" in year_to:
            print(f"Attention. the value year_to has a negative value: {year_to}")
        if year_from_tag not in ["CE", "BCE", "", "ce", "bce"]:
            print(f"Attention. the value year_from_tag has a weird value: {year_from_tag}")
        if year_to_tag not in ["CE", "BCE", "", "ce", "bce"]:
            print(f"Attention. the value year_to_tag has a weird value: {year_to_tag}")
        if year_from_tag in ["CE", "ce", "", " "] and year_to_tag in ["CE", "ce", "", " "]:
            # curious case of Hallstatt B2-3:
            if year_from == "2" and year_to == "3":
                return [None, None]
            else:
                #print(f"YEAR_FROM: {int(year_from)}, YEAR_TO: {int(year_to)}")
                return [int(year_from), int(year_to)]
        if year_from_tag in ["BCE", "", " ", "bce"] and year_to_tag in ["BCE", "bce"]:
            #print(f"YEAR_FROM: {-int(year_from)}, YEAR_TO: {-int(year_to)}")
            return [-int(year_from), -int(year_to)]
        if year_from_tag in ["", " "] and year_to_tag in ["BCE", "bce"]:
            #print(f"YEAR_FROM: {-int(year_from)}, YEAR_TO: {-int(year_to)}")
            return [-int(year_from), -int(year_to)]
        if year_from_tag in ["BCE", "bce"] and year_to_tag in ["CE", "", " ", "ce"]:
            #print(f"YEAR_FROM: {-int(year_from)}, YEAR_TO: {int(year_to)}")
            return [-int(year_from), int(year_to)]

    return [None, None]


### Define functions that go through scraped dfs and decide on what they are and how they should be put in the database

def range_finder(a_str, a_polity):
    stripped_str = a_str.replace(",", "").strip()
    my_catches = re.findall('\[[ ]{0,1}(\d{1,15})[ ]{0,1}[-|_| ][ ]{0,1}(\d{1,15})[ ]{0,1}\]', stripped_str)
    if len(my_catches) == 0:
        return [None, None]
    elif len(my_catches) == 1:
        return [my_catches[0][0], my_catches[0][1]]
    else:
        print(f"BAD_VALUE_GIVEN: {a_str} for: {a_polity}")
        return [None, None]

def range_finder_plus(a_str, a_polity):
    stripped_str = a_str.replace(",", "").strip()
    my_catches = re.findall('\[[ ]{0,1}(\d{1,15})[ ]{0,1}[-|_| ][ ]{0,1}(\d{1,15})[ ]{0,1}\]', stripped_str)
    if len(my_catches) == 0:
        # try finding a normal number:
        my_cathes_with_time = re.findall('\[[ ]{0,1}(\d{1,15})[ ]{0,1}[-|_| ][ ]{0,1}(\d{1,15})[ ]{0,1}\]:(.*)', stripped_str)
        # catch the years as well:
        if len(my_cathes_with_time) == 1:
            years_potential = my_catches_single[0][2]
            extracted_years = is_there_years_here(years_potential)
            if extracted_years != [None, None]:
                return [my_catches_single[0][0], my_catches_single[0][1], extracted_years[0], extracted_years[1]]

        my_catches_single_with_time = re.findall('(\d{1,15}):(.*)', stripped_str)
        if len(my_catches_single_with_time) == 1:
            years_potential = my_catches_single[0][2]
            extracted_years = is_there_years_here(years_potential)
            if extracted_years != [None, None]:
                return [my_catches_single_with_time[0][0], my_catches_single_with_time[0][1], extracted_years[0], extracted_years[1]]
        my_catches_single = re.findall('(\d{1,15})', stripped_str)
        if len(my_catches_single) == 1:
            return [my_catches_single[0][0], my_catches_single[0][0], None, None]
        return [None, None]
    elif len(my_catches) == 1:
        return [my_catches[0][0], my_catches[0][1], None, None]
    else:
        print(f"BAD_VALUE_GIVEN: {a_str} for: {a_polity}")
        return [None, None, None, None]

def range_finder_plus_plus(input_str, a_str, a_polity):
    """
    This will catch:
    123-165: 54-56 BCE
    1234
    [1,234-4,856]: 546 CE
    """
    stripped_str = input_str.replace(",", "").strip()
    my_catches = re.findall(fr'[\[]{{0,1}}[ ]{{0,1}}(\d+)[ ]{{0,1}}[-|_| ]{{0,1}}[ ]{{0,1}}([\d+]*)[ ]{{0,1}}[\]]{{0,1}}[ ]{{0,1}}[{a_str}]{{0,1}}(.*)', stripped_str)
    if len(my_catches) == 1:
        years_potential = my_catches[0][2]
        extracted_years = is_there_years_here(years_potential)
        range_low = my_catches[0][0]
        range_high = my_catches[0][1]
        if extracted_years != [None, None]:
            if range_low and range_high:
                return [range_low, range_high, extracted_years[0], extracted_years[1]]
            elif range_low and not range_high:
                return [range_low, range_low, extracted_years[0], extracted_years[1]]
            else:
                print(f"WARNING: **** {a_polity} ***  BOTH RANGES ARE ONE!!!!!!!!!!!")
        else:
            if range_low and range_high:
                return [range_low, range_high, None, None]
            elif range_low and not range_high:
                return [range_low, range_low, None, None]
            else:
                print(f"WARNING: **** {a_polity} *** BOTH RANGES ARE ONE BOTH TIME RANGES ARE also NONE!!!!!!!!!!!")
    else:
        if input_str not in ["suspected unknown", "NO_VALUE_ON_WIKI"]:
            print(f"WARNING: ** {a_polity} * PROBLEMATIC: {input_str}!!!!")
        return [None, None, None, None]


def range_finder_plus_plus_non_numeric(input_str, a_polity):
    """
    This will catch:
    - absent: 54-56 BCE
    - disputed_present_absent
    - uncertain_absent_present: 546 CE
    """
    stripped_str = input_str.replace(",", "").strip()
    #my_catches = re.findall(r'(\w+)\s*:{0,1}\s*(.*)', stripped_str)
    my_catches = re.findall(r'(present|suspected unknown|NO_VALUE_ON_WIKI|inferred present|absent|inferred absent|unknown|uncertain_present_absent|disputed_present_absent|uncertain_absent_present|disputed_absent_present|disputed_inferred_absent_and_present|disputed_inferred_absent_and_inferred_present|uncertain_absent_and_inferred_present)\s*:{0,1}\s*(.*)', stripped_str)
    
    if len(my_catches) == 1:
        years_potential = my_catches[0][1]
        extracted_years = is_there_years_here(years_potential)
        range_low = my_catches[0][0]

        if extracted_years != [None, None] and range_low:
            return [range_low, extracted_years[0], extracted_years[1],]
        elif range_low:
            return [range_low, None, None]
        else:
            print(f"WARNING: **** {a_polity} ***  PROBLEMATIC!!!!!!!!!!!")
    else:
        print(f"WARNING: **** {a_polity} ***  PROBLEMATIC All NONE!!!!!!!!!!!")
        return [None, None, None]

def utc_zone_finder(a_str, a_polity):
    stripped_str = a_str.replace(",", "").strip()
    letter_part_obj = re.search('([A-Z])', stripped_str)
    num_part_obj = re.search('(\d{1,2})', stripped_str)
    if num_part_obj and letter_part_obj:
        num_part = num_part_obj.group(0)
        letter_part = letter_part_obj.group(0)
        output = f"{num_part} {letter_part}"
    else:
        output = "NO_VALID_VALUE"
        print(f"BAD_VALUE_GIVEN: {a_str} for: {a_polity}")
    return output




def remove_year_range(a_str):
    """
    INPUT:  A string that potentially contans some year info
    RETURNS: the same input with the year values stripped off of it.
    """
    my_new_str = re.sub('(-?\d{1,5})[ ]{0,1}([B|b]*[C|c][E|e]*)*[ ]{0,1}[-|_| ][ ]{0,1}(\d{1,5})[ ]{0,1}([B|b]*[C|c][E|e]*)*', "", a_str)
    my_new_str = re.sub('(-?\d{1,5})[ ]{0,1}([B|b]*[C|c][E|e]*)', "", my_new_str)
    while "  " in my_new_str:
        my_new_str  = my_new_str.replace("  ", " ").strip()
    return my_new_str




# def year_range_detector(input_string):
#     """
#     searches for the occurrence of a year range.
#     RETURNS True if found.
#     """

# def year_range_extractor(input_string):
#     """
#     if there is a year_range (True for the year_range_fdetector) finds the year range.
#     RETURNS (year_from, year_to).
#     """

def tag_detector(my_str):
    """
    Is there a suspected unknown or inferred or disputed none or somrthing similar in the string
    """
    underlined_str = my_str.lower()
    if "suspected unknown" in underlined_str:
        return "SUSPECTED_UNKNOWN"
    elif "suspected" in underlined_str:
        return "SUSPECTED"
    elif "none" ==  underlined_str:
        return "NONE_VALUE"
    elif "unknown" in underlined_str:
        return "UNKNOWN_VALUE"
    elif "disputed" in underlined_str:
        return "DISPUTED"
    elif "inferred" in underlined_str:
        return "INFERRED"
    else:
        return None






def value_semi_colon_splitter(my_df):
    """
    finds the unique values of a column in a df, considering the presence of ";"
    returns unique values
    """
    unique_values = []
    for row, values in my_df.iterrows():
        if len(values[2].split(';')) > 1:
            for item in values[2].split(';'):
                if ":" in item.strip():
                    double_stripped = item.split(":")[0].strip()
                else:
                    double_stripped = item.strip()
                if double_stripped not in unique_values:
                    unique_values.append(double_stripped)
        else:
            if values[2].strip() not in unique_values:
                if ":" in values[2].strip():
                    double_stripped = values[2].strip().split(":")[0]
                else:
                    double_stripped = values[2].strip().strip()
                if double_stripped not in unique_values:
                    unique_values.append(double_stripped.strip())
    return unique_values


def split_a_string_on_colon(item, gen_var):
    if gen_var in ["polity_territory",
            "polity_population", "population_of_the_largest_settlement", 
            "administrative_levels", "settlement_hierarchy", "religious_levels", "military_levels", ]:
        comma_replaced_value = item.replace(",", "")
    else:
        comma_replaced_value = item.replace(",", ";")
    item_better = comma_replaced_value.replace("[", "").replace("]", "").replace("{", "").replace("}", "")
    if ":" in item_better.strip():
        double_stripped = item_better.split(":")[0].strip()
    else:
        double_stripped = item_better.strip()
    return double_stripped


def value_semi_colon_splitter_plus(my_df):
    """
    ONLY TO BE USED AFTER the RESULTS of value_semi_colon_splitter() are analyzed.
    finds the unique values of a column in a df, considering the presence of ";"
    returns unique values
    """
    unique_values = []
    for row, values in my_df.iterrows():
        if values[0] in ["polity_territory",
            "polity_population", "population_of_the_largest_settlement", 
            "administrative_levels", "settlement_hierarchy", "religious_levels", "military_levels", ]:
            comma_replaced_value = values[2].replace(",", "")
        else:
            comma_replaced_value = values[2].replace(",", ";")
        item_better = comma_replaced_value.replace("[", "").replace("]", "").replace("{", "").replace("}", "")
        if len(item_better.split(';')) > 1:
            for item in item_better.split(';'):                
                if ":" in item.strip():
                    double_stripped = item.split(":")[0].strip()
                else:
                    double_stripped = item.strip()
                if double_stripped not in unique_values:
                    unique_values.append(double_stripped)
        else:
            if item_better.strip() not in unique_values:
                if ":" in item_better.strip():
                    double_stripped = item_better.strip().split(":")[0]
                else:
                    double_stripped = item_better.strip().strip()
                if double_stripped not in unique_values:
                    unique_values.append(double_stripped.strip())
    return unique_values


def value_semi_colon_expander(wide_df):
    """
    if there is a semicolon (or comma) inside the value column, splits it and creates multiple lines in the df.
    RETURNS a long df.
    """
    #print(f"Input DF has {len(wide_df.index)} rows.")
    tag_dic = {}
    wide_columns = list(wide_df.columns)
    long_df = pd.DataFrame(columns = wide_columns)
    for row, values in wide_df.iterrows():
        if values[0] in ["polity_territory",
            "polity_population", "population_of_the_largest_settlement", 
            "administrative_levels", "settlement_hierarchy", "religious_levels", "military_levels", ]:
            comma_replaced_value = values[2].replace(",", "")
        else:
            comma_replaced_value = values[2].replace(",", ";")
        if len(comma_replaced_value.split(';')) > 1:
            for item in comma_replaced_value.split(';'):
                if item.strip():
                    pot_tag = tag_detector(item)
                    if pot_tag and pot_tag not in tag_dic.keys():
                        tag_dic[pot_tag] = 1
                    elif pot_tag:
                        tag_dic[pot_tag] = tag_dic[pot_tag] + 1
                        #tag_count = tag_count + 1
                    # write a new row
                    new_values_dic = {
                       wide_columns[0]:  values[0],
                       wide_columns[1]:  values[1],
                       wide_columns[2]:  item.strip(),
                       wide_columns[3]:  values[3],
                    }
                    long_df = long_df.append(new_values_dic, ignore_index = True)

        else:
            long_df = long_df.append(values)
            pot_tag = tag_detector(comma_replaced_value)
            if pot_tag and pot_tag not in tag_dic.keys():
                tag_dic[pot_tag] = 1
            elif pot_tag:
                tag_dic[pot_tag] = tag_dic[pot_tag] + 1

    #print(f"Output DF has {len(long_df.index)} rows")
    return (long_df, tag_dic)

def describe_set_of_value_dfs(my_ultimate_dic):
    """
    Gets a dic containing potentially many dfs. stored in inner values_df keys
    returns a description of everything we might need.

    Analyzes a dictionary containing dataframes, and provides a summary of the data in each dataframe.
    
    Args:
    my_ultimate_dic (dict): A dictionary containing dataframes as values, stored under the "values_df" key.
    
    Returns:
    None: The function prints out a summary of each dataframe contained in the dictionary, including the number of unique values, and any unique values with low frequency.
    """

    for variable, dfs in my_ultimate_dic.items():
        print(variable)
        longer_df, my_tag_dic = value_semi_colon_expander(dfs["values_df"])
        #print("ROWS: ", len(dfs["values_df"].index))
        #print("ROWS: ", len(dfs["values_df"].index))
        unique_values = len(value_semi_colon_splitter(dfs["values_df"]))
        #print("TAGS in DF: ", my_tag_dic)
        #print("Unique: ", unique_values)
        if unique_values <=15:
            for value in value_semi_colon_splitter(dfs["values_df"]):
                if value not in ["present", "suspected unknown", "NO_VALUE_ON_WIKI", "inferred present", "absent", "inferred absent", "unknown", "uncertain_present_absent", "disputed_present_absent", "uncertain_absent_present", "disputed_absent_present", "disputed_inferred_absent_and_present", "disputed_inferred_absent_and_inferred_present",
                "uncertain_absent_and_inferred_present"]:
                    print(f"*{value}")
            print()
        print("_________________")


def jaccard_similarity(str1, str2):
    """
    Calculates the Jaccard similarity between two strings.
    
    Args:
    str1 (str): The first string to compare.
    str2 (str): The second string to compare.
    
    Returns:
    float: A value between 0 and 1 representing the Jaccard similarity between the two strings.
    """
    str1 = re.sub(r'\W+', ' ', str1).lower()
    str2 = re.sub(r'\W+', ' ', str2).lower()
    a = set(str1.split())
    b = set(str2.split())
    c = a.intersection(b)
    print(str1)
    print(str2)
    return float(len(c)) / (len(a) + len(b) - len(c))

def describe_set_of_values_after_pretty(my_ultimate_dic):
    """
    for the after_pretty case
    """
    for key_variable, df_full in my_ultimate_dic.items():
        print(f"*********{key_variable}")
        for inner_var in list(df_full.columns):
            if "XYZ_" in inner_var:
                unique_values = len(df_full[inner_var].unique())
                if unique_values <=50:
                    for value in df_full[inner_var]:
                        if value not in ["present", "absent", "unknown", "UNKNOWN", "0", "1", "2", "3","4", "5", "6", "7","8", "9", "10", "11", "12", "13"]:
                            print(f"*{value}*")
                    print()
                print("_________________")




def all_sc_vars_augmenter(ultimate_dic):
    """
    ultimate_dic has alll the dfs we need
    we wanto to make better dfs and spit them out.
    """
    new_ultimate_dic = copy.deepcopy(ultimate_dic)
    for gen_var, gen_df in ultimate_dic.items():
        #if gen_var == "scale_of_supra-cultural_interaction":
        #    continue
        #variable_under_investigation = gen_var
        wide_df = gen_df["values_df"]
        long_df = value_semi_colon_expander(wide_df)[0]
        unique_values = value_semi_colon_splitter_plus(long_df)
        new_df = pd.DataFrame(columns=['polity','raw','year_from', 'year_to',])
        for index, values in long_df.iterrows():
            # vreate a new row
            value_2_better = split_a_string_on_colon(values[2], gen_var)
            if value_2_better not in unique_values:
                print(f"Baaaaaaaaaaaaad Value: {value_2_better}")
            clean_value_str = remove_year_range(value_2_better)
            clean_year_range  = is_there_years_here(value_2_better)

            if gen_var in ["polity_territory",
            "polity_population", "population_of_the_largest_settlement", 
            "administrative_levels", "settlement_hierarchy", "religious_levels", "military_levels", ]:
                clean_value = range_finder_plus_plus(values[2], ":", values[1])
            #elif gen_var == "duration" or gen_var == "peak_date":
            #    clean_value = [clean_year_range[0], clean_year_range[1]]
            elif gen_var == "ra":
                clean_value = [values[2].strip(),]
            else: # "professional_military_officers", "professional_priesthood", 
                # "professional_soldiers"
                clean_value = range_finder_plus_plus_non_numeric(values[2], values[1])
                #clean_value = [clean_value_str,]


            #mother_dic = var_col_dic_nmaker(ALL_GENERAL_VARS_LIST, ALL_GENERAL_COLS_LIST)
            # replace the value of the variable with its proper replacement:
            proper_gen_var = gen_var.replace(",", "").replace("-", "_")
            if proper_gen_var.strip()[-1] == "s":
                proper_gen_var = proper_gen_var.strip()[:-1]

            new_values_dic = {
                       'variable':  proper_gen_var,
                       'polity':  values[1],
                       'raw':   values[2],
                       'year_from': clean_year_range[0],
                        'year_to': clean_year_range[1],
                        #'desc':  values[3],
                    }
            # if len(mother_dic[GEN_VAR_MAPPER[gen_var]]) == 1 and len(clean_value) == 1:
            #     new_values_dic['db_col_name_1'] =  mother_dic[GEN_VAR_MAPPER[gen_var]][0]
            #     new_values_dic['clean_1'] = clean_value[0]
            #     new_values_dic['col_num'] = 1

            # elif len(mother_dic[GEN_VAR_MAPPER[gen_var]]) == 2 and len(clean_value) == 2:
            #     new_values_dic['db_col_name_1'] =  mother_dic[GEN_VAR_MAPPER[gen_var]][0]
            #     new_values_dic['clean_1'] =  clean_value[0]
            #     new_values_dic['db_col_name_2'] =  mother_dic[GEN_VAR_MAPPER[gen_var]][1]
            #     new_values_dic['clean_2'] =   clean_value[1]
            #     new_values_dic['col_num'] = 2
            # elif len(mother_dic[GEN_VAR_MAPPER[gen_var]]) == 2 and len(clean_value) == 4:
            #     new_values_dic['db_col_name_1'] =  mother_dic[GEN_VAR_MAPPER[gen_var]][0]
            #     new_values_dic['clean_1'] =  clean_value[0]
            #     new_values_dic['db_col_name_2'] =  mother_dic[GEN_VAR_MAPPER[gen_var]][1]
            #     new_values_dic['clean_2'] =   clean_value[1]
            #     new_values_dic['col_num'] = 2
            #     new_values_dic['year_from'] = clean_value[2]
            #     new_values_dic['year_to'] = clean_value[3]
            # else:
            #     print(f"MisMatched Values for Double Entries.....{gen_var}....")

            if len(clean_value) == 1:
                new_values_dic['clean_1'] = clean_value[0]
                new_values_dic['col_num'] = 1

            elif len(clean_value) == 2:
                new_values_dic['clean_1'] =  clean_value[0]
                new_values_dic['clean_2'] =   clean_value[1]
                new_values_dic['col_num'] = 2
            elif len(clean_value) == 3:
                new_values_dic['clean_1'] =  clean_value[0]
                new_values_dic['year_from'] =  clean_value[1]
                new_values_dic['year_to'] =   clean_value[2]
                new_values_dic['col_num'] = 1
            elif len(clean_value) == 4:
                new_values_dic['clean_1'] =  clean_value[0]
                new_values_dic['clean_2'] =   clean_value[1]
                new_values_dic['col_num'] = 2
                new_values_dic['year_from'] = clean_value[2]
                new_values_dic['year_to'] = clean_value[3]
            else:
                print(f"MisMatched Values for Double Entries.....{gen_var}....")



            new_df = new_df.append(new_values_dic, ignore_index = True)
        new_ultimate_dic[gen_var]["values_df"] = new_df
        #if len( list(new_ultimate_dic[gen_var]["values_df"]["wiki_clean"].unique())) < 30:
        #    print("weird residue values:", list(new_ultimate_dic[gen_var]["values_df"]["wiki_clean"].unique()))
        print(f"******** {gen_var}   done and saved as : {proper_gen_var}")

    return new_ultimate_dic


def add_confidence_disputed_to_augmentd_sc(pretty_augmentd_dic):
    """
    gets the output of the all_sc_vars_augmenter() and add the two columns to them:
    - confidence:
    - disputed
    """
    #new_ultimate_dic = copy.deepcopy(pretty_augmentd_dic)
    new_ultimate_dic = {}
    a_dic_of_descriptions_template = {}
    import numpy as np
    for sc_var, sc_df in pretty_augmentd_dic.items():
        df = sc_df["values_df"]

        proper_sc_var = sc_var.replace(",", "").replace("-", "_")
        if proper_sc_var == "mines_or_quarries":
            proper_sc_var = "mines_or_quarry"
        elif proper_sc_var.strip()[-1] == "s":
            proper_sc_var = proper_sc_var.strip()[:-1]

        if proper_sc_var in ["polity_territory",
                    "polity_population", "population_of_the_largest_settlement", 
                    "administrative_level", "settlement_hierarchy", "religious_level", "military_level", ]:
            clean_1_better = "XYZ_" + proper_sc_var + "_from"
            clean_2_better = "XYZ_" + proper_sc_var + "_to"
        else:
            clean_1_better =  "XYZ_" + proper_sc_var
            clean_2_better = "USELESS_COL"

        new_df = pd.DataFrame(columns=['polity', 'year_from', 'year_to',])
        for index, values in df.iterrows():
            new_values_dic = {
                        #'variable':  values["variable"],
                        'polity':  values["polity"],
                        clean_1_better: values.get("clean_1"),
                        clean_2_better: values.get("clean_2"),
                        'year_from': values["year_from"],
                        'year_to': values["year_to"],
                        "confidence": "TRS",
                        "disputed": 'false', 
                        "uncertainty": 'false',
                        "raw": values["raw"],
                            #'desc':  values[3],
                        }

            # numerical values most probably do not need change. except for suspected_unknown  or unknown which is in raw column:
            if values.get("raw") == "NO_VALUE_ON_WIKI":
                continue
            if "suspected unknown" in values.get("raw"):
                new_values_dic["confidence"] = "SSP"
                new_values_dic[clean_1_better] = "UNKNOWN"
                new_values_dic[clean_2_better] = "UNKNOWN"
            elif "unknown" in values.get("raw"):
                new_values_dic["confidence"] = "TRS"
                new_values_dic[clean_1_better] = "UNKNOWN"
                new_values_dic[clean_2_better] = "UNKNOWN"

            # something can be changed for present/absent thingies:
            if values.get("clean_1") == "inferred absent":
                new_values_dic["confidence"] = "IFR"
                new_values_dic[clean_1_better] = "absent"
            if values.get("clean_1") == "inferred present":
                new_values_dic["confidence"] = "IFR"
                new_values_dic[clean_1_better] = "present"

            if values.get("clean_1") in ["disputed_present_absent", "disputed_absent_present"]:
                # add the first disputed value 
                new_values_dic["disputed"] = "true"
                new_values_dic[clean_1_better] = "present"
                new_df = new_df.append(new_values_dic, ignore_index = True)
                # add the second
                new_values_dic["disputed"] = "true"
                new_values_dic[clean_1_better] = "absent"
                new_df = new_df.append(new_values_dic, ignore_index = True)
                continue
            if values.get("clean_1") == "disputed_inferred_absent_and_present":
                # add the first disputed value 
                new_values_dic["disputed"] = "true"
                new_values_dic[clean_1_better] = "present"
                new_df = new_df.append(new_values_dic, ignore_index = True)
                # add the second
                new_values_dic["disputed"] = "true"
                new_values_dic["confidence"] = "IFR"
                new_values_dic[clean_1_better] = "absent"
                new_df = new_df.append(new_values_dic, ignore_index = True)
                continue
            if values.get("clean_1") == "disputed_inferred_absent_and_inferred_present":
                # add the first disputed value 
                new_values_dic["disputed"] = "true"
                new_values_dic["confidence"] = "IFR"
                new_values_dic[clean_1_better] = "present"
                new_df = new_df.append(new_values_dic, ignore_index = True)
                # add the second
                new_values_dic["disputed"] = "true"
                new_values_dic["confidence"] = "IFR"
                new_values_dic[clean_1_better] = "absent"
                new_df = new_df.append(new_values_dic, ignore_index = True)
                continue
            if values.get("clean_1") in ["uncertain_absent_present", "uncertain_present_absent"]:
                # add the first disputed value 
                new_values_dic["uncertainty"] = 'true'
                new_values_dic[clean_1_better] = "present"
                new_df = new_df.append(new_values_dic, ignore_index = True)
                # add the second
                new_values_dic["uncertainty"] = 'true'
                new_values_dic[clean_1_better] = "absent"
                new_df = new_df.append(new_values_dic, ignore_index = True)
                continue
            if values.get("clean_1") == "uncertain_absent_and_inferred_present":
                # add the first disputed value 
                new_values_dic["uncertainty"] = 'true'
                new_values_dic[clean_1_better] = "absent"
                new_df = new_df.append(new_values_dic, ignore_index = True)
                # add the second
                new_values_dic["uncertainty"] = 'true'
                new_values_dic["confidence"] = "IFR"
                new_values_dic[clean_1_better] = "present"
                new_df = new_df.append(new_values_dic, ignore_index = True)
                continue

            new_df = new_df.append(new_values_dic, ignore_index = True)
        new_df.drop('USELESS_COL', axis=1, inplace=True, errors='ignore')
        new_ultimate_dic[proper_sc_var] = new_df
        
        print(f"***** {sc_var}   done ---> : {proper_sc_var}")
        a_dic_of_descriptions_template[proper_sc_var] = "NO_DESCRIPTIONS_IN_CODEBOOK"
    print(a_dic_of_descriptions_template)
    return new_ultimate_dic





def get_all_users_experts(ultimate_dic_clean, current_id_of_last_user):
    # CREATE the PeOLPE (USER and EXPERTS) tables:
    expert_mapper_list = []
    name_duplicates = {
        "Liibert": 'Katheriin Liibert',
        'Rudy Cesaretti': 'Rudolf Cesaretti',
        'Cesaretti': 'Rudolf Cesaretti',
        'RC': 'Rudolf Cesaretti',
        "DH": "Dan Hoyer",
        "PT": "Peter Turchin",
        "PF": "Peter Francois",
        "JGM": "J. G. Manning",
        "PRG": "Peter Rudiack-Gould",
        "WalkerV": "Veronica Walker",
        'Will Farrell': 'William Farrell',
        'Farrell': 'William Farrell',
        'Dan Mullins': 'Daniel Mullins',
        'Agathe Dupreyon': 'Agathe Dupeyron',
        'Edward Turner': "Edward A L Turner",
        "Brachmanska": "Malwina Brachmańska"
    }
    for var_name, var_df in ultimate_dic_clean.items():
        if var_name in ["ra", "editor", "expert"]: 
            for index, item in var_df["values_df"].iterrows():
                if item[2] not in expert_mapper_list and item[2] not in name_duplicates:
                    expert_mapper_list.append(item[2])
                elif item[2] not in expert_mapper_list and item[2] in name_duplicates:
                    if name_duplicates[item[2]] not in expert_mapper_list:
                        expert_mapper_list.append(name_duplicates[item[2]])
    expert_mapper_dic = {}
    root_dir = os.getcwd()
    with open(root_dir + "/USERS_EXPERTS/users_experts.sql", "w") as gen_var_sql_file:
        all_rows_with_var_sql = []
        for index, expert in enumerate(expert_mapper_list):
            user_id = index + 1 + current_id_of_last_user
            expert_mapper_dic[expert] = user_id
            expert_splitted = expert.split(" ")
            if len(expert_splitted) > 1:
                first_name = expert_splitted[0]
                last_name = " ".join(expert_splitted[1:])
            else:
                first_name = expert_splitted[0][0]
                last_name = expert_splitted[0][1:]


            a_row = f"INSERT INTO auth_user (id, first_name, last_name, username, email, password, is_superuser, is_staff, is_active, date_joined) VALUES ({user_id}, '{first_name}', '{last_name}', '{first_name}_{last_name}', '{first_name}@{last_name}.com', 'aliyaret_khoda_behamrahet', 'false', 'true', 'false', '2022-10-31 19:10:20.735+01');"
            all_rows_with_var_sql.append(a_row)

        gen_var_sql_file.write("\n".join(all_rows_with_var_sql))
        print(f"{len(all_rows_with_var_sql)} sql insertion rows added to: users_experts.sql")


    for index, expert in enumerate(expert_mapper_list):
        expert_mapper_dic[expert] = index + 1 + current_id_of_last_user
    return expert_mapper_dic


# Lets start creating sql files:
def get_it_done_sql(vars_dic_df, local):
    root_dir = os.getcwd()
    my_polity_mapper = polity_mapper_maker("my_politys.csv", local)
    all_together_rows = []
    #pwd_here = "/home/majid/dev/old_wiki_scraper_for_social_complexity/SC_SQL_LOCAL"
    for var_name, var_df in vars_dic_df.items():
        all_rows_with_var_sql = []
        for item in var_df.iterrows():
            polity = item[1]["polity"]
            role_mapper = {
                "ra": "RA",
            }
            if var_name in ["ra",]:
                pass
                # col_1 = item[1]["wiki_clean_1"]
                # db_col_name_1 = item[1]["db_col_name_1"]
                # person = PERSONNEL_MAPPER[NAME_DUPLICATE_FIXER[col_1]]
                # role_mapped = role_mapper[var_name]
                # a_expert_row = f"INSERT INTO accounts_seshat_expert (id, user_id, role) VALUES ({person}, {person}, '{role_mapped}');"
                # # only write a new expert if it does not exist (user_id check)
                # if a_expert_row not in all_rows_with_var_sql:
                #     all_rows_with_var_sql.append(a_expert_row)
                # a_row = f"INSERT INTO general_{GEN_VAR_MAPPER[var_name]} (polity_id, {db_col_name_1}_id, tag, finalized, name) VALUES ({my_polity_mapper[polity]}, {person}, 'TRS', 'true', '{var_name}');"
                # all_rows_with_var_sql.append(a_row)
            elif var_name in ["polity_territory",
                    "polity_population", "population_of_the_largest_settlement", 
                    "administrative_level", "settlement_hierarchy", "religious_level", "military_level", ]:
                df_col_from = "XYZ_" + var_name + "_from"
                df_col_to = "XYZ_" + var_name + "_to"
                value_from = item[1][df_col_from]
                value_to = item[1][df_col_to]
                db_col_1 = var_name + "_from"
                db_col_2 =  var_name + "_to"
                year_from = item[1]["year_from"]
                year_to = item[1]["year_to"]
                confidence = item[1]["confidence"]
                disputed = item[1]["disputed"]
                uncertainty = item[1]["uncertainty"]

                if year_from and year_to:
                    a_row = f"INSERT INTO sc_{var_name} (polity_id, {db_col_1}, {db_col_2}, year_from, year_to, tag, is_disputed, is_uncertain, expert_reviewed, finalized, name) VALUES ({my_polity_mapper[polity]}, {value_from}, {value_to}, {year_from}, {year_to}, '{confidence}', '{disputed}',  '{uncertainty}', 'true', 'true', '{var_name}');"
                else:
                    a_row = f"INSERT INTO sc_{var_name} (polity_id, {db_col_1}, {db_col_2}, tag, is_disputed, is_uncertain, expert_reviewed, finalized, name) VALUES ({my_polity_mapper[polity]}, {value_from}, {value_to}, '{confidence}', '{disputed}',  '{uncertainty}', 'true', 'true', '{var_name}');"
                all_rows_with_var_sql.append(a_row)
                all_together_rows.append(a_row)
            else:
                df_col_from = "XYZ_" + var_name
                value_from = item[1][df_col_from].lower()
                db_col_1 = var_name
                year_from = item[1]["year_from"]
                year_to = item[1]["year_to"]
                confidence = item[1]["confidence"]
                disputed = item[1]["disputed"]
                uncertainty = item[1]["uncertainty"]

                if year_from and year_to:
                    a_row = f"INSERT INTO sc_{var_name} (polity_id, {db_col_1}, year_from, year_to, tag, is_disputed, is_uncertain, expert_reviewed, finalized, name) VALUES ({my_polity_mapper[polity]}, '{value_from}', {year_from}, {year_to}, '{confidence}', '{disputed}',  '{uncertainty}', 'true', 'true', '{var_name}');"
                else:
                    a_row = f"INSERT INTO sc_{var_name} (polity_id, {db_col_1}, tag, is_disputed, is_uncertain, expert_reviewed, finalized, name) VALUES ({my_polity_mapper[polity]}, '{value_from}', '{confidence}', '{disputed}',  '{uncertainty}', 'true', 'true', '{var_name}');"
                all_rows_with_var_sql.append(a_row)
                all_together_rows.append(a_row)
        output_file = root_dir + f"/SC_SQL_AWS/{var_name}.sql"
        with open(output_file, "w") as sc_var_sql_file:
            sc_var_sql_file.write("\n".join(all_rows_with_var_sql))
    output_file_all = root_dir + f"/SC_SQL_AWS/aaaaall_all_all.sql"
    with open(output_file_all, "w") as sc_var_sql_file_all:
        sc_var_sql_file_all.write("\n".join(all_together_rows))
    print(f"{len(all_rows_with_var_sql)} sql insertion rows added to: {output_file_all}")


    

def general_vars_sql_maker(unclean_dic, saving_dir, control_file, local=True):
    """
    INPUTS: 
    unclean_dic: the dictionary that contains the data for sql files after several rounds of cleaning. We will use the avialable functions to ceate a pretty_dic out of it.
    saving_dir: where the sql files will reside
    control_file: decides on which varuables have already been taken care of should bes skipped
    
    OUTPUT:
    the updated_control_file
    """
    #my_personnel_mapper = get_all_users_experts(ultimate_dic_clean, 100)
    root_dir = os.getcwd()
    # read the json file inside control_file
    remiaining_vars = []
    with open(root_dir + control_file, "r") as my_file:
        control_data = json.load(my_file)
        for var_name, var_stage in control_data.items():
            if var_stage == "Done":
                continue
            else:
                remiaining_vars.append(var_name)
    # thiner vars_dic 
    thin_dic = {}
    for key, value in unclean_dic.items():
        if key in remiaining_vars:
            continue
        else:
            thin_dic[key] = value

    output_dic = {}
    print(f"Remaining Vars are: {remiaining_vars}")
    print(f"Thin_dic keys are: {thin_dic.keys()}")
    # Go on with thin_dic
    #var_col_dic = var_col_dic_nmaker(ALL_GENERAL_VARS_LIST, ALL_GENERAL_COLS_LIST)
    pretty_thin_dic = all_general_vars_augmenter(thin_dic)
    for var_name, var_df in pretty_thin_dic.items():
        if True:
            #print(expanded_df.coulmns())
            #expanded_df.head()
            expanded_df = var_df["values_df"]
            # find proper dfs to finalize
            if expanded_df["wiki_year_from"].isnull().all() and expanded_df["wiki_year_to"].isnull().all():
                problematic_value = False
                problematic_value_count = 0 
                for index, row in expanded_df.iterrows():
                    if ":" in str(row.wiki_clean) or ";" in str(row.wiki_clean):
                        problematic_value = True
                        problematic_value_count = problematic_value_count + 1
                        print(f"VALUE: {str(row.wiki_clean)} in POLITY: {row.polity}.")
                if not problematic_value:
                    print(f"SEEMS to be GOOD: {var_name}")
                    output_file = root_dir + f"/GEN_VAR_SQL/{var_name}.sql"
                    get_it_done_sql(var_name, expanded_df, output_file, local)
                    output_dic[var_name] = "Done"
                else:
                    print(f"SEEMS to be BAAAAAAAD: {var_name}, {problematic_value_count} Bad values.")
            else:
                if var_name in ["duration", 'scale_of_supra-cultural_interaction',"peak_date"]:
                    output_file = root_dir + f"/GEN_VAR_SQL/{var_name}.sql"
                    get_it_done_sql(var_name, expanded_df, output_file, local)
                    output_dic[var_name] = "Done"
                else:
                    output_dic[var_name] = "XXXXXXXXDone"
    with open(root_dir + control_file, "w") as my_file:
        json.dump(output_dic, my_file)

    return output_dic, control_data


def convert_two_dfs_to_python_vars_dic(df_vars, df_cols, my_db_name="general"):
    df_vars = df_vars.where(pd.notnull(df_vars), None)
    df_cols = df_cols.where(pd.notnull(df_cols), None)
    vars_dic = df_vars.to_dict('index')
    cols_dic = df_cols.to_dict('index')
    final_vars_dic = {}
    for index, main_var_dic in vars_dic.items():
        if main_var_dic["varname"] not in final_vars_dic.keys():
            final_vars_dic[main_var_dic["varname"]] = copy.deepcopy(main_var_dic)
            final_vars_dic[main_var_dic["varname"]]["db_name"] = my_db_name
            del final_vars_dic[main_var_dic["varname"]]["varname"]

            done_cols = []
            hits = 0
            for col_index, col_dic in cols_dic.items():
                if col_dic['colname'] in done_cols:
                    break
                if col_dic['varname'] == main_var_dic['varname']:
                    hits = hits + 1 
                    column_key = "col" + str(hits)
                    final_vars_dic[main_var_dic["varname"]][column_key] = {}
                    for col_key, col_val in col_dic.items():
                        if col_val:
                            final_vars_dic[main_var_dic["varname"]][column_key][col_key] = col_val
                    done_cols.append(col_dic['colname'])
                    #print(done_cols)

    return final_vars_dic


def convert_two_python_dics_to_python_vars_dic(list_of_dic_vars, list_of_dic_cols, my_db_name="sc"):
    vars_dic_output = {}
    for v_name in list_of_dic_vars:
        # create a ,ain_ dic with all the avialable var items:
        v_top_dic = {}
        col_counter = 1
        for v_top_key, v_top_val in v_name.items():
            v_top_dic[v_top_key] = v_top_val
        for c_name in list_of_dic_cols:
            if v_name["varname"] == c_name["varname"]:
                good_key = "col" + str(col_counter)
                v_top_dic[good_key] = c_name
                col_counter = col_counter + 1
        vars_dic_output[v_name["varname"]] = v_top_dic

    return vars_dic_output


def convert_general_vars_dic_to_two_dfs(my_pretty_dic):
    # let's create the mother meta_dfs we need for taking care of the data read from almost anywhere 
    from sc_definitions import SC_VAR_DEFINITIONS, SC_VAR_SUBSECTIONS
    # meta_cols_in_variables = [
    #     "colname", "dtype", "varname", "units", "min", "max", "scale", 
    #     "decimal_places", "max_digits", "choices", "foreign_key", "foreign_key_related_name", "null_meaning", 
    # ]

    # meta_variables = [
    #     "varname", "db_name", "main_desc", "main_desc_source", "notes", "cols", "section", "subsection", "needsSeshatCommon",
    # ]

    my_vars_dic = {}

    for variable, inner_data in my_pretty_dic.items():
        variable_spaced = variable.replace("_", " ")
        if variable in ["ra"]:
            inner_dic = {
            'col1': {'colname': 'sc_ra',
                'dtype': ['ForeignKey', 'Select'],
                'varname': 'sc_research_assistant',
                'col_exp': 'The RA of Social Complexity Variables',
                'foreign_key': 'Seshat_Expert',
                'foreign_key_related_name': 'sc_research_assistant'}
            }
        elif variable in ["polity_territory", ]:
            my_cols = 2
            inner_dic = {
            'col1': {
                'colname': variable + "_from",
                'dtype': ['IntegerField', 'NumberInput'],
                'varname': variable,
                'col_exp': f'The lower range of {variable_spaced} for a polity.',
                'max_digits': 20,
                'units': 'km squared',},
            'col2': {
                'colname': variable + "_to",
                'dtype': ['IntegerField', 'NumberInput'],
                'varname': variable,
                'col_exp': f'The lower range of {variable_spaced} for a polity.',
                'max_digits': 20,
                'units': 'km squared',
                }
            }
        elif variable in ["polity_population", "population_of_the_largest_settlement", ]:
            my_cols = 2
            inner_dic = {
            'col1': {
                'colname': variable + "_from",
                'dtype': ['IntegerField', 'NumberInput'],
                'varname': variable,
                'col_exp': f'The lower range of {variable_spaced} for a polity.',
                'max_digits': 20},
            'col2': {
                'colname': variable + "_to",
                'dtype': ['IntegerField', 'NumberInput'],
                'varname': variable,
                'col_exp': f'The lower range of {variable_spaced} for a polity.',
                'max_digits': 20,
                }
            }
        elif variable in ["administrative_levels", "settlement_hierarchy", "religious_levels", "military_levels", ]:
            my_cols = 2
            inner_dic = {
            'col1': {
                'colname': variable + "_from",
                'dtype': ['IntegerField', 'NumberInput'],
                'varname': variable,
                'col_exp': f'The lower range of {variable_spaced} for a polity.',
                'max_digits': 2,
                'min': 0
                },
            'col2': {
                'colname': variable + "_to",
                'dtype': ['IntegerField', 'NumberInput'],
                'varname': variable,
                'col_exp': f'The lower range of {variable_spaced} for a polity.',
                'max_digits': 2,
                'min': 0
                }
            }     
        else:
            my_cols = 1
            inner_dic = {
            'col1': {
                'colname': variable,
                'dtype': ['CharField', 'Select'],
                'varname': variable,
                'col_exp': f'The absence or presence of {variable_spaced} for a polity.',
                'choices': "ABSENT_PRESENT_CHOICES",
                }
            }  
        # dic to be appended
        my_var_dic = {
            "varname": variable,
            "db_name": "sc",
            "needsSeshatCommon": True,
            "main_desc": SC_VAR_DEFINITIONS[variable],
            "main_desc_source": "NOTHING",
            "notes": "No_Actual_note",
            "cols": my_cols,
            "section": "Social Complexity",
            "subsection": SC_VAR_SUBSECTIONS[variable],
        }
        df_variables = df_variables.append(my_var_dic, ignore_index=True)
        # interesting cols are the ones that start with XYZ_

        my_var_dic.update(inner_dic)
        my_vars_dic.update(my_var_dic)

    return my_vars_dic


check_list = ['(Lindsay 2005, 153-160) Lindsay, J.E. 2005. Daily Life in ',
    'from Kampyr Tepe)." Iran (1992): 49-54. ', 
    'history of empire and invasion. Union Square Press, 2008. pp.64',  
    'Lapidus 2002,, p. 215',
    'Islamic studies 40, no. 1 (2001): 25-48. ',
    'Islamic studies 40 no 1 (2001): 31. ',
    'the Eighteenth Century Studies in History August 1995 11: 261-280 ',
    'Greenwood Publishing Group, 2007.pp. 69-73',
    'Talib at Mazir-i Sharif, Afghanistan (1998), pp. 223',
    'rstanding Islam’’ pp. 31, 43-44. Edinburgh: Dunedin Academic Press.',   # we should detect two here
    'an, C. 2007. <i>Understanding Islam</i> pp. 31, 43. Edinburgh: Dunedin Academic Press',  # we should detect two here
    'Puri, and G. F. Etemadi, 96-126. Paris: UNESCO. Seshat URL: <',
    "(Reinhart 2015a, 90) Katrinka Reinhart. 2015. 'Ritual feasting and empowerment at Yanshi Shangcheng'. <i>Journal of Anthropological Archaeology</i> 39: 76-109.",
    "(Reinhart 2015a, 96-97) Katrinka Reinhart. 2015. 'Ritual feasting and empowerment at Yanshi Shangcheng'. <i>Journal of Anthropological Archaeology</i> 39: 76-109.",
    "(Reinhart 2015a, 80, 83) Katrinka Reinhart. 2015. 'Ritual feasting and empowerment at Yanshi Shangcheng'. <i>Journal of Anthropological Archaeology</i> 39: 76-109.",
    '(Yuan 2013) Yuan, G. 2013. The Discovery and Study of the Early Shang Culture. In A. Underhill (ed.) A Companion to Chinese Archaeology, 323-342. Malden, Oxford, Victoria: Blackwell.',
    'The Hua Miao Of Southwest China”, 72p',
    'An-Shun Kweichow”, 2p',
    'The Hua Miao Of Southwest China”, 70',
    'Societies In Kweichow”, 37',
    'gs And Stories Of The Ch’Uan Miao”, 1',
    'Societies In Kweichow”, 41',
    'Western Hunan”, 54pp',
    'ewe 1986a, 120)',
    'wis 1999b, 167)',
    '大学师范学院学报, 4, 78-84.',
    '学辑刊, (3), 245-250.',
    ' Revenge Hostilities Among The Achuará Jívaro”, 93',
    'Early Egypt. Archaeopress: Oxford. pg: 22-23, 70-71.',
    'Egypt. Oxford: Archaeopress. pg: 43.',
    'Early Egypt. Oxford: Archaeopress. pg: 111, 112.)',
    ' Oxford: Archaeopress. pg: 75-77.',
    'in Ancient Oriental Civilization</i> 26 (1950):31-32 ',
    'redynastic Egypt". <i>Journal of Archaeological Research</i> 9/2 (2001): 127.',
    '(McEvedy and Jones, 1978, 138-47, 227) Colin McEvedy and Richard Jones. 1978. <i>Atlas of World Population History</i>. London: Allen Lane.',
    'Archaeopress. P. 67)',
    'Oxford: Archaeopress. P. 67-69)',
    'Leuven; Dudley, MA: Peeters.P. 132)',
    '(Agut-Labordere 2013, 1023) Agut-Labordere, Dami',
    '(Agut-Labordere 2013, 1010-1011) Agut-Labordere, Damien. "The Sai',
    '(Agut-Labordere 2013, 1025, 1008-1009) Agut-Labordere, Damien.',
    'Haldon and Robin Cormack, 643-51. Oxford: Oxford University Press',
    '(Bouchard 1995: 1844) Seshat URL: <a',
    'Akim Abuakwa Constitution”", 224',
    'West African Market Women”, 108',
    'Pre-Colonial West Africa. African Affairs 84 (334):53-87. P. 69-70)',
    "(Kirch 2010, 82, 106) Patrick Vinton Kirch. 2010. <i>How Chiefs Became",
    'University of California Press. Pg. 129-30.',
    'University of California Press. Pg. 71.',
    '(Kiernan 2007, 147. Kiernan, Ben. Blood and Soil: A World H',
    'Kinship In A Garo Village”, 83p',
    'Kinship In A Garo Village”, 81',
    'In Matrilineal Tribal Society”, 44-45',
    'Journal of the Royal Asiatic Society 20 (4):477-88.Seshat URL: .<a',
    '(Lapidus 2012, 98-99',
    '(Lapidus 2012, 99',
    'a of Islamic Art and Architecture: Vol 3, 179.',
    'Nissen et al. 1993, 5-6',
    'Chavrat 2008, 140',
    'Di Nocera 2010, 257-261',  
    ' Chavrat 2008, 123, 136',
    "d'archeologie orientale 77(1): 59-67.",
    'Carla M. Sinopoli, 93-123. Cambridge: Cambridge University Press.',]

























def find_pages_in(my_str):
    """
    find such patterns in a text:
    * (Jackson 2003, 17)
    * (Jackson 2003, 15-16)
    * to the Heart of Islam pp. 26-67
    * Society 20, no. 1-2. p. 88
    * London: Greenwood Press. p.153-160

    ++++++ POTENTIALLY use '\b(1[0-4][0-9]{2}|[0-9]{3})\b' as the new expression to match numbers up to 1499

    DOES NOT YET FIND:
    *** "(Sack 1983, 62) Ronald H. Sack. 1983. 'The Nabonidus Legend'. Revue d'Assyriologie et d'archeologie orientale 77(1): 59-67.", ----> Note that here we need to hit 62, and not 59-67, because those are the page numbers in the journal or something. In other words we should put a potential hit of 59-67 after a hit for 62 has failed!
    ***  "(Sack 1983, 59, 61) Ronald H. Sack. 1983. 'The Nabonidus Legend'. Revue d'Assyriologie et d'archeologie orientale 77(1): 59-67.", ----> same as above, we should hit 59 and 61 before we go on...
    *** '(Lindsay 2005, 153-160) Lindsay, J.E. 2005. Daily Life in 
    *** from Kampyr Tepe)." Iran (1992): 49-54. ' ----> the page numbers appearing at the nd of the string
    *** history of empire and invasion. Union Square Press, 2008. pp.64  
    *** 'Lapidus 2002,, p. 215'
    *** Islamic studies 40, no. 1 (2001): 25-48. ',
    *** Islamic studies 40 no 1 (2001): 31. '
    *** the Eighteenth Century Studies in History August 1995 11: 261-280 ',
    *** Greenwood Publishing Group, 2007.pp. 69-73',
    *** Talib at Mazir-i Sharif, Afghanistan (1998), pp. 223",
    *** rstanding Islam’’ pp. 31, 43-44. Edinburgh: Dunedin Academic Press.'
    *** an, C. 2007. <i>Understanding Islam</i> pp. 31, 43. Edinburgh: Dunedin Academic Press
    *** Puri, and G. F. Etemadi, 96-126. Paris: UNESCO. Seshat URL: <
    *** "(Reinhart 2015a, 90) Katrinka Reinhart. 2015. 'Ritual feasting and empowerment at Yanshi Shangcheng'. <i>Journal of Anthropological Archaeology</i> 39: 76-109.",
    *** "(Reinhart 2015a, 96-97) Katrinka Reinhart. 2015. 'Ritual feasting and empowerment at Yanshi Shangcheng'. <i>Journal of Anthropological Archaeology</i> 39: 76-109.",
    *** "(Reinhart 2015a, 80, 83) Katrinka Reinhart. 2015. 'Ritual feasting and empowerment at Yanshi Shangcheng'. <i>Journal of Anthropological Archaeology</i> 39: 76-109.",
    ***  '(Yuan 2013) Yuan, G. 2013. The Discovery and Study of the Early Shang Culture. In A. Underhill (ed.) A Companion to Chinese Archaeology, 323-342. Malden, Oxford, Victoria: Blackwell.',
    *** The Hua Miao Of Southwest China”, 72p',
    *** An-Shun Kweichow”, 2p',
    ***  The Hua Miao Of Southwest China”, 70',
    *** Societies In Kweichow”, 37',
    *** gs And Stories Of The Ch’Uan Miao”, 1',
    *** Societies In Kweichow”, 41',
    *** Western Hunan”, 54pp',
    *** ewe 1986a, 120)',
    *** wis 1999b, 167)',
    *** 大学师范学院学报, 4, 78-84.',
    *** 学辑刊, (3), 245-250.',
    ***  Revenge Hostilities Among The Achuará Jívaro”, 93',
    *** Early Egypt. Archaeopress: Oxford. pg: 22-23, 70-71.',
    *** Egypt. Oxford: Archaeopress. pg: 43.',
    *** Early Egypt. Oxford: Archaeopress. pg: 111, 112.)',
    ***  Oxford: Archaeopress. pg: 75-77.',
    *** in Ancient Oriental Civilization</i> 26 (1950):31-32 ',
    *** redynastic Egypt". <i>Journal of Archaeological Research</i> 9/2 (2001): 127.',
    *** '(McEvedy and Jones, 1978, 138-47, 227) Colin McEvedy and Richard Jones. 1978. <i>Atlas of World Population History</i>. London: Allen Lane.',
    *** Archaeopress. P. 67)',
    *** Oxford: Archaeopress. P. 67-69)',
    *** Leuven; Dudley, MA: Peeters.P. 132)',
    *** '(Agut-Labordere 2013, 1023) Agut-Labordere, Dami
    *** '(Agut-Labordere 2013, 1010-1011) Agut-Labordere, Damien. "The Sai
    *** '(Agut-Labordere 2013, 1025, 1008-1009) Agut-Labordere, Damien.
    *** Haldon and Robin Cormack, 643-51. Oxford: Oxford University Press',
    *** '(Bouchard 1995: 1844) Seshat URL: <a
    *** Akim Abuakwa Constitution”, 224',
    *** West African Market Women”, 108',
    *** Pre-Colonial West Africa. African Affairs 84 (334):53-87. P. 69-70)',
    *** "(Kirch 2010, 82, 106) Patrick Vinton Kirch. 2010. <i>How Chiefs Became
    *** University of California Press. Pg. 129-30.',
    *** University of California Press. Pg. 71.',
    *** '(Kiernan 2007, 147. Kiernan, Ben. Blood and Soil: A World H
    *** Kinship In A Garo Village”, 83p',
    *** Kinship In A Garo Village”, 81',
    *** In Matrilineal Tribal Society”, 44-45',
    *** Journal of the Royal Asiatic Society 20 (4):477-88.Seshat URL: .<a
    *** '(Lapidus 2012, 98-99',
    *** '(Lapidus 2012, 99',
    *** a of Islamic Art and Architecture: Vol 3, 179.',
    *** 'Nissen et al. 1993, 5-6',    ----> does not hit because it has no parantheses at the end
    *** 'Chavrat 2008, 140',
    *** 'Di Nocera 2010, 257-261',
    *** ' Chavrat 2008, 123, 136',
    ***  d'archeologie orientale 77(1): 59-67.",
    *** Carla M. Sinopoli, 93-123. Cambridge: Cambridge University Press.",

    :!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! '(McEvedy and Jones 1978, 155+163)',

    # in this case :  
    '(Lindsay 2005, 153-160) Lindsay, J.E. 2005. Daily Life in the Medieval Islamic World. London: Greenwood Press. p.153-160'
    - We are finding the page numbers but we are not deleting them from the first occurence in: (Lindsay 2005, 153-160) Lindsay, 

    # PROBLEMATIC from WIKI SIDE:
    --  Tarn, William Woodthorpe. <i>The Greeks in Bactria and India. Cambridge University Press: 1951, p.124-5. Sidky, H., The Greek Kingdom of Bactria, from Alexander to Eucratides the Great, Oxford, 2000, pp. 168-169</i> 



    ####### TO ANALYZE:
    (Izard and Ki-Zerbo 1992, 333) Michel Izard and Joseph Ki-Zerbo. 1992. 'From the Niger to the Volta', in <i>General History of Africa, vol. 5: Africa from the Sixteenth to the Eighteenth Centuries</i>, edited by Bethwell Allan Ogot, 327-67. London: Heinemann. ----> Code is detecting 333 which seems to be right.

    SHOULD SKIP:
    *  Islamic Law and Society 20 no 1-2',
    * en traversant la Natolie [sic] et la Mésopotamie, 2 vols., Paris, 1819.',
    * : in the Indian Ocean in ancient and early medieval times. Princeton University Press, 1995.',
    * '(Cissoko 1984, 2010) Cissoko, S. M. in Ki-Zerb

    Outputs the potential pages_from and pages_to and the trimmed_str
    """
    #my_str = my_str.strip()
    # check the pp availability:
    # ' pp. 123-456'
    # ' pp.42-1'
    # ' pp. 1-2'
    # ' pp.999-0'
    # ' pp.567-999'
    pp_finderRegex = re.compile('[\s|\.|,]pp.\s*(\d{1,3})-(\d{1,3})')
    catches_all_pp = list(pp_finderRegex.finditer(my_str))
    if catches_all_pp:
        for index_pp, pp_c in enumerate(catches_all_pp):
            page_from = pp_c.group(1)
            page_to = pp_c.group(2)
            if index_pp >=1:
                print(f"Multiple pp options found in string: {my_str}")
            trimmed_text_0 = my_str.replace(pp_c.group(0), "")
            trimmed_text = trimmed_text_0.strip().replace(", )", ",)").replace(",)", ")")

            pp_finderRegex_inner = re.compile(' (\d{4}),\s*(\d{1,3})-(\d{1,3})\)')
            catches_all_pp_inner = list(pp_finderRegex_inner.finditer(trimmed_text))
            if catches_all_pp_inner:
                for index_pp_inner, pp_c_inner in enumerate(catches_all_pp_inner):
                    if index_pp_inner >=1:
                        print(f"Multiple p options found in string: {my_str}")
                    to_be_removed = pp_c_inner.group(2) + "-" + pp_c_inner.group(3)
                    trimmed_text_0_inner = trimmed_text.replace(to_be_removed, "")
                    trimmed_text = trimmed_text_0_inner.strip().replace(", )", ",)").replace(",)", ")")

            return [page_from, page_to, trimmed_text]
    # check the p availability options that are actually pp:
    # ' p. 123-456'
    # ' p.42-1'
    # ' p. 1-2'
    # ' p.999-0'
    # ' p.567-999'
    pp_finderRegex = re.compile('[\s|\.|,]p.\s*(\d{1,3})-(\d{1,3})')
    catches_all_pp = list(pp_finderRegex.finditer(my_str))
    if catches_all_pp:
        for index_pp, pp_c in enumerate(catches_all_pp):
            page_from = pp_c.group(1)
            page_to = pp_c.group(2)
            if index_pp >=1:
                print(f"Multiple p options (thatare actually pp) found in string: {my_str}")
            trimmed_text_0 = my_str.replace(pp_c.group(0), "")
            trimmed_text = trimmed_text_0.strip().replace(", )", ",)").replace(",)", ")")
            return [page_from, page_to, trimmed_text]
    # check the p availability options that are actually p:
    # ' p. 123'
    # ' p.42'
    # ' p. 1'
    # ' p.999'
    # ' p.567'
    pp_finderRegex = re.compile('[\s|\.|,]p.\s*(\d{1,3})')
    catches_all_pp = list(pp_finderRegex.finditer(my_str))
    if catches_all_pp:
        for index_pp, pp_c in enumerate(catches_all_pp):
            page_from = pp_c.group(1)
            page_to = pp_c.group(1)
            if index_pp >=1:
                print(f"Multiple p options found in string: {my_str}")
            trimmed_text_0 = my_str.replace(pp_c.group(0), "")
            trimmed_text = trimmed_text_0.strip().replace(", )", ",)").replace(",)", ")")

            pp_finderRegex_inner = re.compile(' (\d{4})[;|:|,| ]\s*(\d{1,3})\)')
            catches_all_pp_inner = list(pp_finderRegex_inner.finditer(trimmed_text))
            if catches_all_pp_inner:
                for index_pp_inner, pp_c_inner in enumerate(catches_all_pp_inner):
                    if index_pp_inner >=1:
                        print(f"Multiple p options found in string: {my_str}")
                    to_be_removed = pp_c_inner.group(2)
                    trimmed_text_0_inner = trimmed_text.replace(to_be_removed, "")
                    trimmed_text = trimmed_text_0_inner.strip().replace(", )", ",)").replace(",)", ")")

            return [page_from, page_to, trimmed_text]
        
    pp_finderRegex = re.compile('[\s|\.|,]pp.\s*(\d{1,3})')
    catches_all_pp = list(pp_finderRegex.finditer(my_str))
    if catches_all_pp:
        for index_pp, pp_c in enumerate(catches_all_pp):
            page_from = pp_c.group(1)
            page_to = pp_c.group(1)
            if index_pp >=1:
                print(f"Multiple p options found in string: {my_str}")
            trimmed_text_0 = my_str.replace(pp_c.group(0), "")
            trimmed_text = trimmed_text_0.strip().replace(", )", ",)").replace(",)", ")")

            return [page_from, page_to, trimmed_text]
        

    pp_finderRegex = re.compile('[\s|\.|,](P(?:g.|\.))\s*(\d{1,3})-(\d{1,3})[\.|\)|]')
    catches_all_pp = list(pp_finderRegex.finditer(my_str))
    if catches_all_pp:
        for index_pp, pp_c in enumerate(catches_all_pp):
            page_from = pp_c.group(2)
            page_to = pp_c.group(3)
            if index_pp >=1:
                print(f"Multiple p options (thatare actually pp) found in string: {my_str}")
            trimmed_text_0 = my_str.replace(pp_c.group(0), "")
            trimmed_text = trimmed_text_0.strip().replace(", )", ",)").replace(",)", ")")
            return [page_from, page_to, trimmed_text]
        
    pp_finderRegex = re.compile('[\s|\.|,](pg:|Pg:)\s*(\d{1,3})-(\d{1,3})[\.|\),|]')
    catches_all_pp = list(pp_finderRegex.finditer(my_str))
    if catches_all_pp:
        for index_pp, pp_c in enumerate(catches_all_pp):
            page_from = pp_c.group(2)
            page_to = pp_c.group(3)
            if index_pp >=1:
                print(f"Multiple p options (thatare actually pp) found in string: {my_str}")
            trimmed_text_0 = my_str.replace(pp_c.group(0), "")
            trimmed_text = trimmed_text_0.strip().replace(", )", ",)").replace(",)", ")")
            return [page_from, page_to, trimmed_text]

        
    pp_finderRegex = re.compile('[\s|\.|,](P(?:g.|\.))\s*(\d{1,3})[\.|\)|]')
    catches_all_pp = list(pp_finderRegex.finditer(my_str))
    if catches_all_pp:
        for index_pp, pp_c in enumerate(catches_all_pp):
            page_from = pp_c.group(2)
            page_to = pp_c.group(2)
            if index_pp >=1:
                print(f"Multiple p options (thatare actually pp) found in string: {my_str}")
            trimmed_text_0 = my_str.replace(pp_c.group(0), "")
            trimmed_text = trimmed_text_0.strip().replace(", )", ",)").replace(",)", ")")
            return [page_from, page_to, trimmed_text]

    pp_finderRegex = re.compile('[\s|\.|,](pg:|Pg:)\s*(\d{1,3})[\.|\)|,]')
    catches_all_pp = list(pp_finderRegex.finditer(my_str))
    if catches_all_pp:
        for index_pp, pp_c in enumerate(catches_all_pp):
            page_from = pp_c.group(2)
            page_to = pp_c.group(2)
            if index_pp >=1:
                print(f"Multiple p options (thatare actually pp) found in string: {my_str}")
            trimmed_text_0 = my_str.replace(pp_c.group(0), "")
            trimmed_text = trimmed_text_0.strip().replace(", )", ",)").replace(",)", ")")
            return [page_from, page_to, trimmed_text]

    # check the pages availability options that are just strings:
    # ' 2021; 42-123'
    # ' 2022: 123-1'
    # ' 2023, 2-12'
    # ' 2024 123-34'       (1[0-4][0-9]{2}|\d{1,3})
    # ' 2025: 42-56'
    pp_finderRegex = re.compile('[(\s]?(\d{4})[a|b|c]*\)*[;|:|,]\s*(1[0-4][0-9]{2}|\d{1,3})-(1[0-4][0-9]{2}|\d{1,3})[.),\s]')
    catches_all_pp = list(pp_finderRegex.finditer(my_str))
    if catches_all_pp:
        for index_pp, pp_c in enumerate(catches_all_pp):
            page_from = pp_c.group(2)
            page_to = pp_c.group(3)
            if index_pp >=1:
                print(f"Multiple p options found in string: {my_str}")
            to_be_removed = pp_c.group(2) + "-" + pp_c.group(3)
            trimmed_text_0 = my_str.replace(to_be_removed, "")
            trimmed_text = trimmed_text_0.strip().replace(", )", ",)").replace(",)", ")")
            return [page_from, page_to, trimmed_text]    
    # check the page availability options that are just strings:
    # ' 2021; 42'
    # ' 2022: 123'
    # ' 2023, 2'
    # ' 2024 123'
    # ' 2025: 42'
    pp_finderRegex = re.compile('[(\s]?(\d{4})[a|b|c]*\)*[;|:|,]\s*(1[0-4][0-9]{2}|\d{1,3})[.),\s]')
    catches_all_pp = list(pp_finderRegex.finditer(my_str))
    if catches_all_pp:
        for index_pp, pp_c in enumerate(catches_all_pp):
            page_from = pp_c.group(2)
            page_to = pp_c.group(2)
            if index_pp >=1:
                print(f"Multiple p options found in string: {my_str}")
            to_be_removed = pp_c.group(2)
            trimmed_text_0 = my_str.replace(to_be_removed, "")           
            trimmed_text = trimmed_text_0.strip().replace(", )", ",)").replace(",)", ")")
            return [page_from, page_to, trimmed_text]
        

    # check the pages availability options that are just strings:
    # ' 2021; 42-123'
    # ' 2022: 123-1'
    # ' 2023, 2-12'
    # ' 2024 123-34'
    # ' 2025: 42-56'
    pp_finderRegex = re.compile('[(\s]?(\d{4})[a|b|c]*\)*[;|:|,]\s*(1[0-4][0-9]{2}|\d{1,3})-(1[0-4][0-9]{2}|\d{1,3})[.),\s]')
    catches_all_pp = list(pp_finderRegex.finditer(my_str))
    if catches_all_pp:
        for index_pp, pp_c in enumerate(catches_all_pp):
            page_from = pp_c.group(2)
            page_to = pp_c.group(3)
            if index_pp >=1:
                print(f"Multiple p options found in string: {my_str}")
            to_be_removed = pp_c.group(2) + "-" + pp_c.group(3)
            trimmed_text_0 = my_str.replace(to_be_removed, "")
            trimmed_text = trimmed_text_0.strip().replace(", )", ",)").replace(",)", ")")
            return [page_from, page_to, trimmed_text]    
    # check the page availability options that are just strings:
    # ' 2021; 42'
    # ' 2022: 123'
    # ' 2023, 2'
    # ' 2024 123'
    # ' 2025: 42'
    pp_finderRegex = re.compile('[(\s]?(\d{4})[a|b|c]*\)*[;|:|,]\s*(1[0-4][0-9]{2}|\d{1,3})[.),\s]')
    catches_all_pp = list(pp_finderRegex.finditer(my_str))
    if catches_all_pp:
        for index_pp, pp_c in enumerate(catches_all_pp):
            page_from = pp_c.group(2)
            page_to = pp_c.group(2)
            if index_pp >=1:
                print(f"Multiple p options found in string: {my_str}")
            to_be_removed = pp_c.group(2)
            trimmed_text_0 = my_str.replace(to_be_removed, "")           
            trimmed_text = trimmed_text_0.strip().replace(", )", ",)").replace(",)", ")")
            return [page_from, page_to, trimmed_text]


    # check the pp availability:
    # ' pp.42-1'
    # ' pp. 1-2'
    # ' pp.999-0'
    # ' pp.567-999'
    pp_finderRegex = re.compile(' pp.\s*(\d{1,3})-(\d{1,3})')
    catches_all_pp = list(pp_finderRegex.finditer(my_str))
    if catches_all_pp:
        for index_pp, pp_c in enumerate(catches_all_pp):
            page_from = pp_c.group(1)
            page_to = pp_c.group(2)
            if index_pp >=1:
                print(f"Multiple pp options found in string: {my_str}")
            trimmed_text_0 = my_str.replace(pp_c.group(0), "")
            trimmed_text = trimmed_text_0.strip().replace(", )", ",)").replace(",)", ")")
            return [page_from, page_to, trimmed_text]
        
    pp_finderRegex = re.compile(',\s*(\d{1,3})-(\d{1,3})\.*$')
    catches_all_pp = list(pp_finderRegex.finditer(my_str))
    if catches_all_pp:
        for index_pp, pp_c in enumerate(catches_all_pp):
            page_from = pp_c.group(1)
            page_to = pp_c.group(2)
            if index_pp >=1:
                print(f"Multiple pp options found in string: {my_str}")
            trimmed_text_0 = my_str.replace(pp_c.group(0), "")
            trimmed_text = trimmed_text_0.strip().replace(", )", ",)").replace(",)", ")")
            return [page_from, page_to, trimmed_text]
        


    pp_finderRegex = re.compile('[”|"]*, (\d{1,3})p*$')
    catches_all_pp = list(pp_finderRegex.finditer(my_str))
    if catches_all_pp:
        for index_pp, pp_c in enumerate(catches_all_pp):
            page_from = pp_c.group(1)
            page_to = pp_c.group(1)
            if index_pp >=1:
                print(f"Multiple pp options found in string: {my_str}")
            trimmed_text_0 = my_str.replace(pp_c.group(0), "")
            trimmed_text = trimmed_text_0.strip().replace(", )", ",)").replace(",)", ")")
            return [page_from, page_to, trimmed_text]
        


    # ': 123-456 xxxx'
    # ', 42-1.xxxx'
    # ': 1-2 xxxx'
    # ', 999-0.xxxxx'
    # ': 567-999 '        
    pp_finderRegex = re.compile('[,:]\s*(\d{1,3})-(\d{1,3})[\.\s]')
    catches_all_pp = list(pp_finderRegex.finditer(my_str))
    if catches_all_pp:
        for index_pp, pp_c in enumerate(catches_all_pp):
            page_from = pp_c.group(1)
            page_to = pp_c.group(2)
            if index_pp >=1:
                print(f"Multiple pp options found in string: {my_str}")
            trimmed_text_0 = my_str.replace(pp_c.group(0), "")
            trimmed_text = trimmed_text_0.strip().replace(", )", ",)").replace(",)", ")")
            return [page_from, page_to, trimmed_text]

    pp_finderRegex = re.compile('[,:]\s*(\d{1,3})-(\d{1,3})[\.\s]?\)?')
    catches_all_pp = list(pp_finderRegex.finditer(my_str))
    if catches_all_pp:
        for index_pp, pp_c in enumerate(catches_all_pp):
            page_from = pp_c.group(1)
            page_to = pp_c.group(2)
            if index_pp >=1:
                print(f"Multiple pp options found in string: {my_str}")
            trimmed_text_0 = my_str.replace(pp_c.group(0), "")
            trimmed_text = trimmed_text_0.strip().replace(", )", ",)").replace(",)", ")")
            return [page_from, page_to, trimmed_text]
        
    pp_finderRegex = re.compile(', (\d{1,3})[\.\s]?\)?$')
    catches_all_pp = list(pp_finderRegex.finditer(my_str))
    if catches_all_pp:
        for index_pp, pp_c in enumerate(catches_all_pp):
            page_from = pp_c.group(1)
            page_to = pp_c.group(1)
            if index_pp >=1:
                print(f"Multiple pp options found in string: {my_str}")
            trimmed_text_0 = my_str.replace(pp_c.group(0), "")
            trimmed_text = trimmed_text_0.strip().replace(", )", ",)").replace(",)", ")")
            return [page_from, page_to, trimmed_text]
        
        
    pp_finderRegex = re.compile('^\(Bouchard 1995: (\d{1,4})\) Seshat URL')
    catches_all_pp = list(pp_finderRegex.finditer(my_str))
    if catches_all_pp:
        for index_pp, pp_c in enumerate(catches_all_pp):
            page_from = pp_c.group(1)
            page_to = pp_c.group(1)
            if index_pp >=1:
                print(f"Multiple pp options found in string: {my_str}")
            trimmed_text_0 = my_str.replace(pp_c.group(0), "")
            trimmed_text = trimmed_text_0.strip().replace(", )", ",)").replace(",)", ")")
            return [page_from, page_to, trimmed_text]
        
    return [None, None, my_str]




def check_page_finders_checklist(check_list):
    done_ones = 0
    remaining_ones = []
    for problematic_str in check_list:
        pg_fr, pg_to, trimmed = find_pages_in(problematic_str)
        if pg_fr and pg_to:
            print(problematic_str)
            print("******")
            print(f"PAge_from:{pg_fr}, Page_to: {pg_to}")
            print(f"Trimmed_text: {trimmed}")
            print("_________________________")
            done_ones +=1
        else:
            remaining_ones.append(problematic_str)
    print("##########################")
    for i in remaining_ones:
        print(f"{i}!!")



    print(f"{done_ones} out of {len(check_list)} done.")










def ref_span_replacer_for_ref_dic(my_str, polity_name, all_meta_data, already_done_data, all_unique_refs_sofar):
    # note that class and id tags might be misplaced.
    RefRegex = re.compile('<sup class="reference" id="cite_ref-(\d{1,4})"><a href="#cite_note-(\d{1,4})">\[(\d{1,4}|\d{1},\d{3})\]</a></sup>')

    catches_all = RefRegex.finditer(my_str)
    all_refs = {}

    #print(catches_all)
    if catches_all:
        for index, catches in enumerate(catches_all):
            updated_catch_3 = catches.group(3).replace(",", "")
            
            if catches.group(1) == catches.group(2) and catches.group(1) == updated_catch_3:
                #my_str = my_str.replace(catches.group(0), f"[MAJIDBENAM_REF_{catches.group(1)}_{polity_name}]")
                # make sure the regex is good for the seshat_info case. They are different.
                new_match_regex = f'<li id="cite_note-{catches.group(1)}"><span class="mw-cite-backlink"><a href="#cite_ref-{catches.group(1)}">↑</a></span> <span class="reference-text">(.*)</span>'

                #new_match_regex = f'<li id="cite_note-{catches.group(1)}"><span class="mw-cite-backlink"><a href="#cite_ref-{catches.group(1)}"><span class="cite-accessibility-label">Jump up </span>↑</a></span> <span class="reference-text">(.*)</span>'
                NEWRegEx = re.compile(new_match_regex)
                catches_all_values = NEWRegEx.finditer(my_str)
                if catches_all_values:
                    #my_values = {}
                    if f"MAJIDBENAM_REF_{catches.group(1)}_{polity_name}" in already_done_data.keys():
                        my_values_0 = already_done_data[f"MAJIDBENAM_REF_{catches.group(1)}_{polity_name}"]
                        if ("hasVisibleZotero" in my_values_0.keys() and my_values_0["hasVisibleZotero"] == True) or ("isDuplicate" in my_values_0.keys() and my_values_0["isDuplicate"] == True):
                            print(my_values_0["original_text"])
                            continue
                    #my_value = "NO_REF_MATCH_FOR_THIS_ENTRY_AAAAA"
                    my_values = {}
                    for index_2, cccc in enumerate(catches_all_values):
                        raw_text = cccc.group(1)
                        #print(f"***{raw_text}")
                        if raw_text.strip() not in all_unique_refs_sofar.keys():
                            all_unique_refs_sofar[raw_text.strip()] = f"MAJIDBENAM_REF_{catches.group(1)}_{polity_name}"
                            my_values["original_text"] = raw_text.strip()
                        else:
                            my_values["isDuplicate"] = True
                            my_values["duplicateOf"] = f"MAJIDBENAM_REF_{catches.group(1)}_{polity_name}"
                            continue
                        if index_2 >=1:
                           print(f"Multiple Matches for {polity_name}")
                        
                        # try to find Zotero links:
                        if "zotero.org/groups/1051264/seshat_databank" in raw_text:
                            my_values["hasVisibleZotero"] = True
                            all_meta_data['No_of_hasVisibleZoteros'] += 1
                        
                        # personal correspondence (comment)
                        if "personal correspondence" in raw_text.lower() or "personal comment" in raw_text.lower() or "pers. comm." in raw_text.lower() or "pers. comment" in raw_text.lower():
                            my_values["hasPersonalComment"] = True
                            #print(f"---{raw_text}---")
                            all_meta_data['No_of_hasPersonalComments'] += 1 
                        # try to find the visible pages thingie:
                        pages_from_extracted, pages_to_extracted, extracted_trimmed_text = find_pages_in(raw_text)
                        if pages_from_extracted and pages_to_extracted:
                            my_values["hasVisiblePages"] = True
                            my_values["page_from"] = pages_from_extracted
                            my_values["page_to"] = pages_to_extracted
                            all_meta_data['No_of_Vis_Pages'] += 1
                            my_values["trimmedText"] = extracted_trimmed_text.strip()# .replace("<i>", "").replace("</i>", "")
                            # ultimately replace even " " with nothing
                            my_values["trimmedTextPLUS"] = extracted_trimmed_text.strip().replace("<i>", "").replace("</i>", "").replace(",", "").replace(".", "").replace(":", "").replace(" &amp; ", " ").replace('"', '').replace("(", "").replace(")", "").lower()

                        else:
                            my_values["hasVisiblePages"] = False
                            my_values["trimmedText"] = raw_text.strip()
                            # ultimately replace even " " with nothing
                            my_values["trimmedTextPLUS"] = raw_text.strip().replace("<i>", "").replace("</i>", "").replace(",", "").replace(".", "").replace(":", "").replace(" &amp; ", " ").replace('"', '').replace("(", "").replace(")", "").lower()
                else:
                    my_values = {
                        "original_text": "Weird_VALUE_HERE",
                        "trimmedText": "Weird_VALUE_HERE_for_trimmed",
                        "trimmedTextPLUS": "Weird_VALUE_HERE_for_trimmed",
                    }
                    #my_value = "NO_REF_MATCH_FOR_THIS_ENTRY"
                my_key = f"MAJIDBENAM_REF_{catches.group(1)}_{polity_name}"
                all_refs[my_key] = my_values
                if "_" in polity_name:
                    print(f"underlined polity name: {polity_name}")
            else:
                print(f"MIsMatch at index: {index+1}, {polity_name}")
    print(f"Polity: {polity_name} Done...")
    return all_refs, all_meta_data, all_unique_refs_sofar


def ultimate_ref_dic_maker(old_dic_of_refs_json_file):
    """
    INPUT:
    old_dic_of_refs_json_file:  can simply be an empty JSON file at the beginning of the coding process.
    INSIDE THE FUNCTION BODY, Receives the full html text of a polity page.
    
    OUTPUT:
    a dic that maps the in_text_refs to at_the_end_of_the_text_refs:
    KEY, VALUE ----> "MAJIDBENAM_REF_123_AfDurrn", "Aliyari, 1976, 14-16"
    """
    with open(old_dic_of_refs_json_file) as json_file:
        already_taken_care_of_data = json.load(json_file)

    my_politys = ["AfGhurd", "AfDurrn", "CnNWei*"]
    # my_politys = []
    # with open("./csv_files/polity_ngas.csv", 'r') as pol_csv:
    #     csv_reader = csv.reader(pol_csv, delimiter=',')
    #     for row in csv_reader:
    #         my_politys.append(row[1])
    all_refs_to_be_returned = {}
    all_unique_refs = {}
    all_metadata_to_be_returned = {
        "No_of_Vis_Pages": 0,
        "No_of_hasVisibleZoteros": 0,
        "No_of_hasPersonalComments": 0,
    }
    #all_metadata_to_be_returned = {}
    for polity in my_politys:
        with open(f"html_files/seshat_browser_Jan_30_2023/full_{polity}.html", "r", encoding='utf-8') as f:
            source= f.read()
            refs_returned_for_this_polity, all_metadata_to_be_returned, all_unique_refs = ref_span_replacer_for_ref_dic(source, polity, all_metadata_to_be_returned, already_taken_care_of_data, all_unique_refs)
            all_refs_to_be_returned.update(refs_returned_for_this_polity)
            #all_metadata_to_be_returned.update(meta_data_for_this_polity)
            #all_refs_to_be_returned += refs_returned_for_this_polity
    #output_dic = {}
    #for item in all_refs_to_be_returned:
    #    output_dic[item] = ""
    print("_______")
    print("META_Data:")
    print("_______")
    length_of_refs = len(all_refs_to_be_returned)
    # make a set of all the unique refs:
    unique_refs = []
    for key1, value1 in all_refs_to_be_returned.items():
        if "original_text" in value1.keys():
            if value1["original_text"] not in unique_refs:
                unique_refs.append(value1["original_text"])
            if value1["original_text"] == "Weird_VALUE_HERE":
                print(f"OOOOPSI..........{key1} has weird values.")
    length_of_unique_refs = len(unique_refs)
    unique_refs_percentage = round(100 * length_of_unique_refs / length_of_refs, 3)

    # make a set of all the unique trimmed refs: (that do not have visible zotero IDs)
    unique_trimmed_refs = []
    for key1, value1 in all_refs_to_be_returned.items():
        if "trimmedText" in value1.keys() and "hasVisibleZotero" not in value1.keys():
            if value1["trimmedText"] not in unique_trimmed_refs:
                unique_trimmed_refs.append(value1["trimmedText"])
                #print(value1["trimmedText"])
                #print("**********")
    length_of_unique_trimmed_refs = len(unique_trimmed_refs)
    unique_trimmed_refs_percentage = round(100 * length_of_unique_trimmed_refs / length_of_refs, 3)

    # make a set of all the unique trimmed PLUS refs: (that do not have visible zotero IDs)
    unique_trimmed_refs = []
    for key1, value1 in all_refs_to_be_returned.items():
        if "trimmedTextPLUS" in value1.keys() and "hasVisibleZotero" not in value1.keys():
            if value1["trimmedTextPLUS"] not in unique_trimmed_refs:
                unique_trimmed_refs.append(value1["trimmedTextPLUS"])
                #print(value1["trimmedTextPLUS"])
                #print("**********")
    length_of_unique_trimmed_refs = len(unique_trimmed_refs)
    unique_trimmed_refs_percentage = round(100 * length_of_unique_trimmed_refs / length_of_refs, 3)

    print(f"The No of the refs is: {length_of_refs}")
    print(f"The No of unique refs is: {length_of_unique_refs} ----> {unique_refs_percentage} %")
    print(f"The No of unique trimmed refs is: {length_of_unique_trimmed_refs} ----> {unique_trimmed_refs_percentage} %")
    # Zotero Visible
    has_vis_zot_num = all_metadata_to_be_returned["No_of_hasVisibleZoteros"]
    has_zot_percentage = round(100 * has_vis_zot_num / length_of_refs, 3)
    print(f"has_Visible_Zotero: {has_vis_zot_num} ----> {has_zot_percentage} %")
    # has Personal comments Visible
    has_pers_comm_num = all_metadata_to_be_returned["No_of_hasPersonalComments"]
    has_pc_percentage = round(100 * has_pers_comm_num / length_of_refs, 3)
    print(f"has_personal_comments: {has_pers_comm_num} ----> {has_pc_percentage} %")
    # PAges
    has_vis_pgs_num = all_metadata_to_be_returned["No_of_Vis_Pages"]
    has_pgs_percentage = round(100 * has_vis_pgs_num / length_of_refs, 3)
    print(f"has_Visible_Pages: {has_vis_pgs_num} ----> {has_pgs_percentage} %")

    with open(old_dic_of_refs_json_file, "w") as outfile:
        json.dump(all_refs_to_be_returned, outfile)
    return all_refs_to_be_returned, all_metadata_to_be_returned



def ref_span_replacer_for_ref_dic_2(my_str, polity_name, all_refs_sofar, all_unique_refs_sofar, html_folder):
    # Maybe cite-ref and class=reference should be replaced.
    if html_folder == "seshat_browser_Jan_30_2023":
        RefRegex = re.compile('<sup class="reference" id="cite_ref-(\d{1,4})"><a href="#cite_note-(\d{1,4})">\[(\d{1,4}|\d{1},\d{3})\]</a></sup>')
    elif html_folder == "seshat_info_Jul_22":
        RefRegex = re.compile('<sup id="cite_ref-(\d{1,4})" class="reference"><a href="#cite_note-(\d{1,4})">\[(\d{1,4}|\d{1},\d{3})\]</a></sup>')

    catches_all = RefRegex.finditer(my_str)
    #print(my_str)
    #print(catches_all)
    if catches_all:
        for index, catches in enumerate(catches_all):
            updated_catch_3 = catches.group(3).replace(",", "")
            
            if catches.group(1) == catches.group(2) and catches.group(1) == updated_catch_3:
                #print("catchiiii")
                #my_str = my_str.replace(catches.group(0), f"[MAJIDBENAM_REF_{catches.group(1)}_{polity_name}]")
                # make sure the regex is good for the seshat_info case. They are different.
                if html_folder == "seshat_browser_Jan_30_2023":
                    new_match_regex = f'<li id="cite_note-{catches.group(1)}"><span class="mw-cite-backlink"><a href="#cite_ref-{catches.group(1)}">↑</a></span> <span class="reference-text">(.*)</span>'
                elif html_folder == "seshat_info_Jul_22":
                    new_match_regex = f'<li id="cite_note-{catches.group(1)}"><span class="mw-cite-backlink"><a href="#cite_ref-{catches.group(1)}"><span class="cite-accessibility-label">Jump up </span>↑</a></span> <span class="reference-text">(.*)</span>'
                NEWRegEx = re.compile(new_match_regex)
                catches_all_values = NEWRegEx.finditer(my_str)
                if catches_all_values:
                    my_ref_values = {}
                    for index_2, cccc in enumerate(catches_all_values):
                        raw_text = cccc.group(1)
                        for kkk, vvv in all_refs_sofar.items():
                            if raw_text.strip().replace("<i>", "").replace("</i>", "").replace(",", "").replace(".", "").replace(":", "") == vvv.strip().replace("<i>", "").replace("</i>", "").replace(",", "").replace(".", "").replace(":", ""):
                                my_ref_values[f"REF_{catches.group(1)}_{polity_name}"] = f"IS_DUPLICATE_{kkk}"
                                #print("Bingo")
                                break
                            # if raw_text.strip().replace("<i>", "").replace("</i>", "").replace(",", "").replace(".", "").replace(":", "") == vvv:
                            #     my_ref_values[f"MAJIDBENAM_REF_{catches.group(1)}_{polity_name}"] = f"IS_DUPLICATE_{kkk}"
                            #     #print("Bingo")
                            #     break
                        else:
                            my_ref_values[f"REF_{catches.group(1)}_{polity_name}"] = raw_text #.strip().replace("<i>", "").replace("</i>", "").replace(",", "").replace(".", "").replace(":", "")
                            all_unique_refs_sofar.update(my_ref_values)
                    all_refs_sofar.update(my_ref_values)
            else:
                print(f"MIsMatch at index: {index+1}, {polity_name}")
    print(f"Polity: {polity_name} Done...")
    return all_refs_sofar, all_unique_refs_sofar

def ultimate_citation_dic_maker_duplicate_finder(html_folder, ALL_POLITIES=False):
    """
    gives both ALL and ALL UNIQUE Citations
    RUNTIME: for seshatbrowser and all polities: > 20 mins.
    RUNTIME: for seshat.info (Wiki) and all polities: > 210 mins.
    To change to sesghat.info, I should change both the Html files address, and the RegEx.
    """
    if not ALL_POLITIES:
        my_politys = ["AfGhurd", "AfDurrn", "CnNWei*"]
    else:
        my_politys = []
        with open("./csv_files/polity_ngas.csv", 'r') as pol_csv:
            csv_reader = csv.reader(pol_csv, delimiter=',')
            for row in csv_reader:
                my_politys.append(row[1])
    all_refs = {}
    all_unique_refs = {}
    #all_metadata_to_be_returned = {}
    for polity in my_politys:
        file_address = f"html_files/{html_folder}/full_{polity}.html"
        with open(file_address, "r", encoding='utf-8') as f:
            source= f.read()
            all_refs_for_this_polity, all_unique_refs_for_this_polity = ref_span_replacer_for_ref_dic_2(source, polity, all_refs,all_unique_refs, html_folder)
            all_refs.update(all_refs_for_this_polity)
            all_unique_refs.update(all_unique_refs_for_this_polity)

    print("_________")
    print(f"All CITATIONS in all polities: {len(all_refs)}")
    print(f"All UNIQUE CITATIONS in all polities: {len(all_unique_refs)}")

    # This file will go thorugh for further analysis
    with open(f"only_unique_citations_for_{html_folder}.json", "w") as outfile1:
        json.dump(all_unique_refs, outfile1)
    # This filr will be used only when we need to populate the databases or JSOn files for NLP points, etc.
    with open(f"all_citations_with_duplicates_indicated_for_{html_folder}.json", "w") as outfile:
        json.dump(all_refs, outfile)
    return all_refs, all_unique_refs


def children_finder(raw_value_0):
    """
    finds children in a single reference in a seshat wiki referece
    also returns true if it has children
    """
    raw_value = raw_value_0.replace("&amp;", " ").replace("&nbsp;", " ")
    num_part_obj = re.search('(\d{4})', raw_value)
    if ";" in raw_value and (
        "an updated version is available online at" not in raw_value) and (
        "for a brief look at the decline" not in raw_value):
        raw_value_split = raw_value.split(";")
        pot_children_goodness = []
        pot_good_children_list = []
        for a_pot_child in raw_value_split:
            # we are putting a constraint here. This means that we need a decent four-digit number to accept a child, which does not have to be the case: 
            # eg: ' Amira K. Bennisnon,The Great Caliphs, p. 88;Bloom, Jonathan M., and Sheila Blair, eds. The Grove Encyclopedia of Islamic Art and Architecture: Vol. 3. Oxford University Press, 2009. p. 79 '
            # potentially we can see if there is a page range to give a pass as well.
            # At the end of the day, we should compare all the unique refs we have captured before these changes to make sure that stupid refs do not get an undeserved pass.
            num_part_obj = re.search('(\d{4})', a_pot_child)
            if not num_part_obj:
                pot_children_goodness.append(False)
            elif int(num_part_obj.group(1)) >= 2023 or int(num_part_obj.group(1)) <= 1500:
                pot_children_goodness.append(False)
            else:
                pot_children_goodness.append(True)
                pot_good_children_list.append(a_pot_child.strip())
        # if the solit part sounds like a good boy:
        if len(pot_good_children_list) >= 2:
            return (pot_good_children_list, True)
        else:
            return ([raw_value_0,], False)
    else:
        return ([raw_value_0,], False)


def ultimate_ref_dic_maker_plus(refs_json_folder):
    """
    refs_json_folder: is the folder name related to the output of the ultimate_citation_dic_maker_duplicate_finder()
    - It is NOT only the Unique refs.
    """
    refs_json_file = "only_unique_citations_for_" + refs_json_folder + ".json"
    with open(refs_json_file) as json_file:
        refs_data = json.load(json_file)
    all_unique_refs = {}
    all_meta_data = {
        "No_of_Vis_Pages": 0,
        "No_of_hasVisibleZoteros": 0,
        "No_of_Visible_Zoteros_Extracted": 0,
        "No_of_hasPersonalComments": 0,
        "No_of_hasChildren" : 0,
    }
    for kkk, vvv in refs_data.items():
        if "IS_DUPLICATE_" in vvv:
            # This is a duplicate for taking care of references, but for NLP we need to take care of these as well.
            continue
        else:
            # loop pver potential children
            vvv_children, has_children_value = children_finder(vvv)
            a_list_of_children_dics = []
            for a_child in vvv_children:
                # default_inner_values
                inner_values = {
                    "hasVisibleZotero" : False,
                    "hasPersonalComment": False,
                    "hasVisiblePages": False,
                    "originalText": "SAME_AS_TRIMMED",
                    "trimmedText": a_child,
                    "trimmedTextPLUS": a_child.strip().replace("<i>", "").replace("</i>", "").replace(",", "").replace(".", "").replace(":", ""),
                    "zoteroID": []
                }
                # try to find Zotero links from Visible links:
                if "zotero.org/groups/1051264/seshat_databank" in a_child:
                    inner_values["hasVisibleZotero"] = True
                    # grab the zotero:
                    if "/itemKey/" in a_child:
                        potential_zotero = a_child.split("/itemKey/")[1][:9]
                        if (len(potential_zotero) >8 and potential_zotero[8] in ['"', '/', "."]) or (len(potential_zotero) == 8):
                            inner_values["zoteroID"] = [potential_zotero[0:8],]
                            all_meta_data['No_of_Visible_Zoteros_Extracted'] += 1
                        else:
                            print(f"---------OOOPSi.... for {a_child}")
                    elif "/seshat_databank/items/" in a_child:
                        potential_zotero = a_child.split("/seshat_databank/items/")[1][:9]
                        if (len(potential_zotero) >8 and potential_zotero[8] in ['"', '/', "."]) or (len(potential_zotero) == 8):
                            inner_values["zoteroID"] = [potential_zotero[0:8],]
                            all_meta_data['No_of_Visible_Zoteros_Extracted'] += 1
                        else:
                            print(f"---------OOOPSi.... for {a_child}")
                    elif "/titleCreatorYear/items/" in a_child:
                        potential_zotero = a_child.split("/titleCreatorYear/items/")[1].split("/")[0]
                        inner_values["zoteroID"] = [potential_zotero,]
                        all_meta_data['No_of_Visible_Zoteros_Extracted'] += 1
                    elif "/items/" in a_child:
                        potential_zotero = a_child.split("/items/")[1].split("/")[0]
                        inner_values["zoteroID"] = [potential_zotero,]
                        all_meta_data['No_of_Visible_Zoteros_Extracted'] += 1
                    else:
                        print(f"--- NO ZOTERO FOUND for {a_child}")
                    
                    # check if the ID caught is of length 8:
                    if "zoteroID" in inner_values.keys() and len(inner_values["zoteroID"][0]) != 8:
                        print(f"--- Baaaaaaaaaaaad ZOTERO FOUND for {a_child}")

                    all_meta_data['No_of_hasVisibleZoteros'] += 1
                
                # personal correspondence (comment)
                if "personal correspondence" in a_child.lower() or "personal comment" in a_child.lower() or "pers. comm." in a_child.lower() or "pers. comment" in a_child.lower() or "personal communication" in a_child.lower():
                    inner_values["hasPersonalComment"] = True
                    all_meta_data['No_of_hasPersonalComments'] += 1 

                # try to find the visible pages thingie:
                pages_from_extracted, pages_to_extracted, extracted_trimmed_text = find_pages_in(a_child)
                if pages_from_extracted and pages_to_extracted:
                    inner_values["hasVisiblePages"] = True
                    inner_values["page_from"] = pages_from_extracted
                    inner_values["page_to"] = pages_to_extracted
                    all_meta_data['No_of_Vis_Pages'] += 1
                    inner_values["originalText"] = a_child
                    inner_values["trimmedText"] = extracted_trimmed_text.strip()
                    inner_values["trimmedTextPLUS"] = extracted_trimmed_text.strip().replace("<i>", "").replace("</i>", "").replace(",", "").replace(".", "").replace(":", "")
                
                a_list_of_children_dics.append(inner_values)

            all_unique_refs[kkk] = a_list_of_children_dics
    # No of unique refs:
    no_unique_refs = len(all_unique_refs)
    all_meta_data["No_of_Unique_Refs"] = no_unique_refs

    # # No of unique trimmed refs:
    # unique_trimmed_refs = [] #len(all_unique_refs)
    # for kk, vv in all_unique_refs.items():
    #     if vv["trimmedText"] not in unique_trimmed_refs:
    #         unique_trimmed_refs.append(vv["trimmedText"])
    # no_unique_trimmed_refs = len(unique_trimmed_refs)
    # all_meta_data["No_of_Unique_trimmed_Refs"] = no_unique_trimmed_refs

    # # No of unique trimmed PLUS refs:
    # unique_trimmed_refs_PLUS = [] #len(all_unique_refs)
    # for kk, vv in all_unique_refs.items():
    #     if vv["trimmedTextPLUS"] not in unique_trimmed_refs_PLUS:
    #         unique_trimmed_refs_PLUS.append(vv["trimmedTextPLUS"])
    # no_unique_trimmed_refs_PLUS = len(unique_trimmed_refs_PLUS)
    # all_meta_data["No_of_Unique_trimmed_Refs_PLUS"] = no_unique_trimmed_refs_PLUS


    # # No of unique trimmed refs that need work:
    # unique_trimmed_refs_needing_work = [] #len(all_unique_refs)
    # for kk, vv in all_unique_refs.items():
    #     if not vv["hasVisibleZotero"] and not vv["hasPersonalComment"] and vv["trimmedText"] not in unique_trimmed_refs_needing_work:
    #         unique_trimmed_refs_needing_work.append(vv["trimmedText"])
    # no_unique_trimmed_refs_needing_work = len(unique_trimmed_refs_needing_work)
    # all_meta_data["No_of_Unique_trimmed_Refs_needing_work"] = no_unique_trimmed_refs_needing_work

    # # No of unique trimmed PLUS refs that need work:
    # unique_trimmed_PLUS_refs_needing_work = [] #len(all_unique_refs)
    # for kk, vv in all_unique_refs.items():
    #     if not vv["hasVisibleZotero"] and not vv["hasPersonalComment"] and vv["trimmedTextPLUS"] not in unique_trimmed_PLUS_refs_needing_work:
    #         unique_trimmed_PLUS_refs_needing_work.append(vv["trimmedTextPLUS"])
    # no_unique_trimmed_PLUS_refs_needing_work = len(unique_trimmed_PLUS_refs_needing_work)
    # all_meta_data["No_of_Unique_trimmed_PLUS_Refs_needing_work"] = no_unique_trimmed_PLUS_refs_needing_work
    
    with open(f"a_dic_with_info_on_children_for_{refs_json_folder}.json", "w") as outfile:
        json.dump(all_unique_refs, outfile)
    return all_unique_refs, all_meta_data
# Zotero: 752
# has Personal Comment: 126
# has pages: 12622
# has pages (1): 10028
# has pages (2-5): 2160
# has pages (5+): 434
# PROJECTED Zotero: 2358
# PROJECTED has Personal Comment: 1543
# PROJECTED has pages: 37766
# PROJECTED has pages 1: 30069
# PROJECTED has pages 2-5: 6944
# PROJECTED has pages 5+: 753
# REFS 7490


# Zotero: 752
# has Personal Comment: 126
# has pages: 12930
# has pages (1): 10302
# has pages (2-5): 2193
# has pages (5+): 435
# PROJECTED Zotero: 2358
# PROJECTED has Personal Comment: 1543
# PROJECTED has pages: 38525
# PROJECTED has pages 1: 30763
# PROJECTED has pages 2-5: 6996
# PROJECTED has pages 5+: 766

# REFS 7235

def analyze_the_augmented_json_file(augmented_json_folder):
    """
    augmented_json_file: usually ----> "a_dic_with_info_on_children.json"
    """
    augmented_json_file = "a_dic_with_info_on_children_for_" + augmented_json_folder + ".json"
    with open(augmented_json_file) as json_file1:
        unique_refs_dic = json.load(json_file1)

    all_refs_file = "all_citations_with_duplicates_indicated_for_" + augmented_json_folder + ".json"
    with open(all_refs_file) as json_file2:
        all_refs_dic = json.load(json_file2)
    
    has_zotero = 0
    has_page = 0
    has_pages = 0
    has_pages_minus_5 = 0
    has_pages_plus_5 = 0
    is_pers_com = 0

    has_zotero_projected_on_all_refs = 0
    has_page_projected_on_all_refs = 0
    has_pages_projected_on_all_refs = 0
    has_pages_minus_5_projected_on_all_refs = 0
    has_pages_plus_5_projected_on_all_refs = 0
    is_pers_com_projected_on_all_refs = 0
    # this is when we have more than one reference (citation) listed under a single number for references in Wiki. 

    #EX: Ref_6_AfDurrn: ↑ Barfield, Thomas. Afghanistan: a cultural and political history. Princeton University Press, 2010. pp. 97-109;;;;;;;;;;; Runion, Meredith L. The history of Afghanistan. Greenwood Publishing Group, 2007.pp. 69-73
    has_plus_one_children = 0
    number_of_children_total = 0


    all_unique_refs = []
    all_unique_refs_to_be_returned = []
    all_unique_refs_no = 0
    all_unique_refs_no_projected_on_all_refs = 0

    for key, value in unique_refs_dic.items():
        if len(value) > 1:
            has_plus_one_children+=1
            number_of_children_total+=len(value)
            #print(key, value)
        for a_citation in value:                 
            if a_citation["trimmedTextPLUS"] not in all_unique_refs:
                all_unique_refs.append(a_citation["trimmedTextPLUS"])
                all_unique_refs_to_be_returned.append(a_citation["trimmedText"])

                all_unique_refs_no+=1
                all_unique_refs_no_projected_on_all_refs +=1
                for kk, vv in all_refs_dic.items():
                    if str(key) in vv:
                        all_unique_refs_no_projected_on_all_refs +=1

            if a_citation["hasVisibleZotero"]:
                has_zotero+=1
                has_zotero_projected_on_all_refs +=1
                for kk, vv in all_refs_dic.items():
                    if str(key) in vv:
                        has_zotero_projected_on_all_refs +=1
            if a_citation["hasPersonalComment"]:
                is_pers_com+=1
                is_pers_com_projected_on_all_refs +=1
                for kk, vv in all_refs_dic.items():
                    if str(key) in vv:
                        is_pers_com_projected_on_all_refs +=1
            if a_citation["hasVisiblePages"]:
                has_pages+=1
                has_pages_projected_on_all_refs +=1
                for kk, vv in all_refs_dic.items():
                    if str(key) in vv:
                        has_pages_projected_on_all_refs +=1
                page_from = int(a_citation["page_from"])
                page_to = int(a_citation["page_to"])
                if page_from == page_to:
                    has_page+=1
                    has_page_projected_on_all_refs +=1
                    for kk, vv in all_refs_dic.items():
                        if str(key) in vv:
                            has_page_projected_on_all_refs +=1
                elif page_from - page_to < 5:
                    has_pages_minus_5+=1
                    has_pages_minus_5_projected_on_all_refs +=1
                    for kk, vv in all_refs_dic.items():
                        if str(key) in vv:
                            has_pages_minus_5_projected_on_all_refs +=1
                else:
                    has_pages_plus_5+=1
                    has_pages_plus_5_projected_on_all_refs +=1
                    for kk, vv in all_refs_dic.items():
                        if str(key) in vv:
                            has_pages_plus_5_projected_on_all_refs +=1
    
                
    print("has children:", has_plus_one_children)
    print("number of children:", number_of_children_total)
    print("Zotero:", has_zotero)
    print("has Personal Comment:", is_pers_com)
    print("has pages:", has_pages)
    print("has pages (1):", has_page)
    print("has pages (2-5):", has_pages_minus_5)
    print("has pages (5+):", has_pages_plus_5)

    print("PROJECTED Zotero:", has_zotero_projected_on_all_refs)
    print("PROJECTED has Personal Comment:", is_pers_com_projected_on_all_refs)
    print("PROJECTED has pages:", has_pages_projected_on_all_refs)
    print("PROJECTED has pages 1:", has_page_projected_on_all_refs)
    print("PROJECTED has pages 2-5:", has_pages_minus_5_projected_on_all_refs)
    print("PROJECTED has pages 5+:", has_pages_plus_5_projected_on_all_refs)
    print()
    print("REFS", all_unique_refs_no)
    print("PROJECTED REFS with no actual meaning", all_unique_refs_no_projected_on_all_refs)

    return all_unique_refs_to_be_returned 




#[{'hasVisibleZotero': False, 'hasPersonalComment': False, 'hasVisiblePages': True, 'originalText': 'Barfield, Thomas. Afghanistan: a cultural and political history. Princeton University Press, 2010. pp. 97-109', 'trimmedText': 'Barfield, Thomas. Afghanistan: a cultural and political history. Princeton University Press, 2010.', 'trimmedTextPLUS': 'Barfield Thomas Afghanistan a cultural and political history Princeton University Press 2010', 'zoteroID': [], 'page_from': '97', 'page_to': '109'},
# {'hasVisibleZotero': False, 'hasPersonalComment': False, 'hasVisiblePages': False, 'originalText': 'SAME_AS_TRIMMED', 'trimmedText': 'Runion, Meredith L. <i>The history of Afghanistan</i>. Greenwood Publishing Group, 2007.pp. 69-73', 'trimmedTextPLUS': 'Runion Meredith L The history of Afghanistan Greenwood Publishing Group 2007pp 69-73', 'zoteroID': []}]


    # my_ult_ref_dic, my_ult_metadata = ultimate_ref_dic_maker_plus("mother_dic_with_duplicates.json")

def go_find_zoteros(ultimate_dic_without_duplicates):
    """
    round one of finding zotero links with almost 100 percent certainty
    """
    with open(ultimate_dic_without_duplicates) as json_file:
        all_unique_refs = json.load(json_file)
    # collect a work-needed dic:

    smaller_unique_refs = {}
    for k, v in all_unique_refs.items():
        smaller_unique_refs[k] = v
        if len(smaller_unique_refs) > 100:
            break
    trimmed_dic = {}
    for kk, vv_top in smaller_unique_refs.items():
        trimmed_dic[kk] = {}
        for vv_index, vv in enumerate(vv_top):
            if not vv["zoteroID"] and not vv["hasPersonalComment"] and vv["trimmedText"] not in trimmed_dic.keys():
                trimmed_dic[kk][str(vv_index)] = vv["trimmedText"]

    # go find zoteros:
    # bring in all the json data from zotero:
    with open("Seshat_Databank_Dec_6.json") as json_zotero:
        json_zotero_data_list = json.load(json_zotero)

    output_dic ={}

    No_of_matches = 0
    for kk, vv in trimmed_dic.items():
        output_dic[kk] = {}
        for inner_index, vv_inner in vv.items():
            potential_matches_list = []
            for zot_data in json_zotero_data_list:
                if zot_data.get("title") and zot_data.get("author") and zot_data.get("issued"):
                    zot_title = zot_data.get("title").lower().replace(":", "").replace(" ", "").replace(",", "").replace(".", "").replace(";", "")
                    zot_author_list = zot_data.get("author")[0]
                    if zot_author_list and zot_author_list.get("family"):
                        zot_author_0 = zot_author_list.get("family").lower()
                    else:
                        zot_author_0 = "NOZOTERO_AUTHOR_AVAILABLE"
                    
                    zot_year_list = zot_data.get("issued").get("date-parts")
                    if zot_year_list:
                        zot_year = zot_year_list[0][0]
                    else:
                        zot_year = "NOZOTERO_YEAR_AVAILABLE"

                    # check if there is amatch:
                    if zot_title in vv_inner.lower().replace(":", "").replace(" ", "").replace(",", "").replace(".", "").replace(";", "") and zot_author_0 in vv_inner.lower() and zot_year in vv_inner.lower():
                        potential_matches_list.append(zot_data["id"].split("/")[-1])
                        #output_dic[kk] = [zot_data["id"].split("/")[-1],]
                        # print("_________")
                        # print("Match between:")
                        # print(vv_inner)
                        # print("********And**********")
                        # print(zot_data)
            if potential_matches_list:
                output_dic[kk][inner_index] = potential_matches_list
                No_of_matches +=1
                if No_of_matches % 100 == 1:
                    print(f"No of matches so far: {No_of_matches}")
            else:
                output_dic[kk][inner_index] = []

    with open("trimmed_dic_UPDATED_to_be_merged_TEST.json", "w") as outfile:
        json.dump(output_dic, outfile)


def merge_trimmed_data_and_create_a_new_ultimate_dic(trimmed_json, ultimate_dic_without_duplicates):
    with open(ultimate_dic_without_duplicates) as json_file:
        all_unique_refs = json.load(json_file)
    with open(trimmed_json) as json_file_2:
        all_trimmed_taken_care_of = json.load(json_file_2)

    for kk, vv in all_trimmed_taken_care_of.items():
        all_unique_refs[kk]["zoteroID"] = [vv,]

    all_meta_data = {}
    # No of unique refs:
    no_unique_refs = len(all_unique_refs)
    all_meta_data["No_of_Unique_Refs"] = no_unique_refs

    # No of unique trimmed refs:
    unique_trimmed_refs = [] #len(all_unique_refs)
    for kk, vv in all_unique_refs.items():
        if vv["trimmedText"] not in unique_trimmed_refs:
            unique_trimmed_refs.append(vv["trimmedText"])
    no_unique_trimmed_refs = len(unique_trimmed_refs)
    all_meta_data["No_of_Unique_trimmed_Refs"] = no_unique_trimmed_refs


    # No of unique trimmed refs that need work:
    unique_trimmed_refs_needing_work = [] #len(all_unique_refs)
    for kk, vv in all_unique_refs.items():
        if not vv["zoteroID"] and not vv["hasPersonalComment"] and vv["trimmedText"] not in unique_trimmed_refs_needing_work:
            unique_trimmed_refs_needing_work.append(vv["trimmedText"])
    no_unique_trimmed_refs_needing_work = len(unique_trimmed_refs_needing_work)
    all_meta_data["No_of_Unique_trimmed_Refs_needing_work"] = no_unique_trimmed_refs_needing_work

    with open(ultimate_dic_without_duplicates, "w") as outfile:
        json.dump(all_unique_refs, outfile)
    return all_unique_refs, all_meta_data



def go_find_zoteros_round_2(ultimate_dic_without_duplicates):
    """
    Find those small ones that might have a match
    """
    with open(ultimate_dic_without_duplicates) as json_file:
        all_unique_refs = json.load(json_file)
    # collect a work-needed dic:
    trimmed_dic = {}
    for kk, vv in all_unique_refs.items():
        if not vv["zoteroID"] and not vv["hasPersonalComment"] and vv["trimmedText"] not in trimmed_dic.keys():
            trimmed_dic[kk] = vv["trimmedText"]

    # go find zoteros:
    # bring in all the json data from zotero:
    with open("Seshat_Databank_Dec_6.json") as json_zotero:
        json_zotero_data_list = json.load(json_zotero)

    output_dic ={}
    output_dic_5_or_below = {}

    No_of_matches = 0
    for kk, vv in trimmed_dic.items():
        potential_matches = 0
        potential_matches_five = 0
        potential_matches_list = []
        the_match = ""
        the_match_for_5_or_below = ""
        for zot_data in json_zotero_data_list:
            if zot_data.get("author") and zot_data.get("issued"):
                zot_author_list = zot_data.get("author")[0]
                if zot_author_list and zot_author_list.get("family"):
                    zot_author_0 = zot_author_list.get("family").lower()
                else:
                    zot_author_0 = "NOZOTERO_AUTHOR_AVAILABLE"
                
                zot_year_list = zot_data.get("issued").get("date-parts")
                if zot_year_list:
                    zot_year = zot_year_list[0][0]
                else:
                    zot_year = "NOZOTERO_YEAR_AVAILABLE"

                # check if there is amatch:
                if len(zot_author_0) >=6 and zot_author_0 in vv.lower() and zot_year in vv.lower() and "accessed" not in vv.lower():
                    potential_matches += 1
                    the_match = zot_data["id"].split("/")[-1]
                    potential_matches_list.append(the_match)
                elif len(zot_author_0) == 5 and zot_author_0 != "chang" and zot_author_0 in vv.lower() and zot_year in vv.lower() and "accessed" not in vv.lower():
                    potential_matches_five += 1
                    the_match_for_5_or_below = zot_data["id"].split("/")[-1]
                    potential_matches_list.append(the_match_for_5_or_below)
        if potential_matches_list:
            output_dic[kk] = potential_matches_list
            No_of_matches +=1
            if No_of_matches % 100 == 1:
                print(f"No of matches so far: {No_of_matches}")
        #elif potential_matches >= 1:
        #    print(f"---- More than one option available for {vv}")


    with open("trimmed_dic_UPDATED_to_be_merged.json", "w") as outfile:
        json.dump(output_dic, outfile)
    with open("trimmed_dic_UPDATED_2_for_five_or_below.json", "w") as outfile_5_or_below:
        json.dump(output_dic_5_or_below, outfile_5_or_below)




def go_find_zoteros_round_3(ultimate_dic_without_duplicates):
    """
    Find those small ones that might have a match
    """
    with open(ultimate_dic_without_duplicates) as json_file:
        all_unique_refs = json.load(json_file)
    # collect a work-needed dic:
    trimmed_dic = {}
    for kk, vv in all_unique_refs.items():
        if not vv["zoteroID"] and not vv["hasPersonalComment"] and vv["trimmedText"] not in trimmed_dic.keys():
            trimmed_dic[kk] = vv["trimmedText"]

    # go find zoteros:
    # bring in all the json data from zotero:
    with open("Seshat_Databank_Dec_6.json") as json_zotero:
        json_zotero_data_list = json.load(json_zotero)

    output_dic ={}

    No_of_matches = 0
    for kk, vv in trimmed_dic.items():
        potential_matches = 0
        potential_matches_list = []
        the_match = ""
        for zot_data in json_zotero_data_list:
            if zot_data.get("author") and zot_data.get("issued"):
                zot_title = zot_data.get("title").lower().replace(":", "").replace(" ", "").replace(",", "").replace(".", "").replace(";", "")
                zot_author_list = zot_data.get("author")[0]
                if zot_author_list and zot_author_list.get("family"):
                    zot_author_0 = zot_author_list.get("family").lower()
                else:
                    zot_author_0 = "NOZOTERO_AUTHOR_AVAILABLE"

                # check if there is amatch:
                if zot_title in vv.lower().replace(":", "").replace(" ", "").replace(",", "").replace(".", "").replace(";", "") and len(zot_author_0) >= 6 and zot_author_0 in vv.lower() and "accessed" not in vv.lower():
                    potential_matches += 1
                    the_match = zot_data["id"].split("/")[-1]
                    potential_matches_list.append(the_match)
        if potential_matches_list:
            output_dic[kk] = potential_matches_list
            No_of_matches +=1
            if No_of_matches % 100 == 1:
                print(f"No of matches so far: {No_of_matches}")


    with open("trimmed_dic_UPDATED_to_be_merged.json", "w") as outfile:
        json.dump(output_dic, outfile)



def first_n_words_finder(a_str, n):
    """
    Finds the first n words in a string (or the first two, or the first one, or the first n-1)
    """
    regex = r"\b([a-zA-Z\u00C0-\u017F']+)\b(?:\W+\b([a-zA-Z\u00C0-\u017F']+)\b)?(?:\W+\b([a-zA-Z\u00C0-\u017F']+)\b)?(?:\W+\b([a-zA-Z\u00C0-\u017F']+)\b)?"
    match = re.search(regex, a_str)
    if match:
        words = [match.group(i) for i in range(1, n+1) if match.group(i)]
        return words
    else:
        return []
    
def find_the_year_plus(a_str):
    """
    Finds the first three words in a string (or the first two, or the first one)
    """
    regex = r"(\d{4}[abc]?)"
    match = re.search(regex, a_str)
    if match:
        words = [match.group(i) for i in range(1, 2) if match.group(i)]
        return words
    else:
        return []
    
def find_second_and_third_guess(file_dir, max_text_length):
    """
    Takes the folder name and returns the augmented version with second and third guesses

    we can probably extend to fourth guesses by looking into the trimmedTexts themselves
    """
    with open(f"json_files/extra_ps_at_the_end_for_{file_dir}.json") as f1:
        extras = json.load(f1)
    with open(f"a_dic_with_info_on_children_for_{file_dir}.json") as f2:
        details = json.load(f2)


    output_dic = {}


    shorties = 0
    good_shorties = 0
    good_shorties_all = 0
    two_hits = 0
    no_hits=0
    third_chances = 0
    more_hits = 0
    good_shorties_third = 0
    two_hits_third = 0
    no_hits_third=0
    more_hits_third = 0


    all_the_ps_in_all_polities = [] 
    for kk, vv in extras.items():
        for a_thing in vv:
            all_the_ps_in_all_polities.append(a_thing)
    for key, value in details.items():
        polity_name = key.split("_")[-1]
        #if polity_name == "CnNWei*":
        #    print(key)
        for index, item in enumerate(value):
            if item["originalText"] == "SAME_AS_TRIMMED":
                x = item["trimmedText"]
            else:   
                x = item["originalText"]
            #if polity_name == "CnNWei*":
            #    print(x)
            #    print("***********")
            if len(x) < max_text_length and item["hasPersonalComment"] ==False:
                shorties+=1
                # find the year
                the_year_plus_in_shortie =  find_the_year_plus(x)
                the_top_ws_in_shortie =  first_n_words_finder(x, 4)
                the_ps_below = extras[polity_name]
                
                potential_hits = []
                for a_p in the_ps_below:
                    number_of_hits = 0
                    if "and" in the_top_ws_in_shortie:
                        the_top_ws_in_shortie.remove("and")
                    if "in" in the_top_ws_in_shortie:
                        the_top_ws_in_shortie.remove("in")
                    if "amp" in the_top_ws_in_shortie:
                        the_top_ws_in_shortie.remove("amp")
                    num_of_words = len(the_top_ws_in_shortie)
                    for a_w in the_top_ws_in_shortie:
                        if the_year_plus_in_shortie and the_year_plus_in_shortie[0] in a_p and len(a_w) >= 3 and a_w.lower() in a_p.lower():
                            #print(f"HIT: {x}  ----->  in {key} \n {a_p}***")
                            #print("_____________")
                            number_of_hits+=1
                            #potential_hits.append(a_p)
                            #details[key][index]["second_chance"] = a_p
                    if number_of_hits == num_of_words:
                        # high probability hit:
                        potential_hits.append(a_p)
                        #details[key][index]["second_chance_high"] = a_p
                    elif number_of_hits == 3 and num_of_words ==4 and a_p not in potential_hits:
                    #     # 75% highly probale
                        potential_hits.append(a_p)
                        #print(f"75 percent HITs in {key}: {x}  ----> {the_top_ws_in_shortie} \n{potential_hits}")
                    #     #details[key][index]["second_chance_medium"] = a_p
                    elif number_of_hits == 2 and num_of_words ==3 and a_p not in potential_hits:
                    #     # 66% highly probale
                        potential_hits.append(a_p)
                        #print(f"66 percent HITs in {key}: {x}  ----> {the_top_ws_in_shortie} \n{potential_hits}")
                    #     #details[key][index]["second_chance_medium"] = a_p
                potential_hits=list(set(potential_hits))
                if len(potential_hits) == 1:
                    # Very likely hit:
                    #if good_shorties <100:
                    #    print(f"1 HIT in {key}: {x}  ----> \n{potential_hits}")
                    good_shorties+=1
                    details[key][index]["second_chance"] = potential_hits
                elif len(potential_hits) == 2:
                    #if two_hits <100:
                    #    print(f"2 HITs in {key}: {x}  ----> \n{potential_hits}")
                    two_hits+=1
                    details[key][index]["second_chance"] = potential_hits
                elif len(potential_hits) == 0:
                    #if no_hits <100:
                    #    print(f"No HITs in {key}: {x}  ----> \n{potential_hits}")
                    no_hits+=1
                else:
                    #print(f"More than two hits!!!!!!!!!!!!! {key}: {x} !!!!!!!!!! ----> \n{potential_hits}")
                    more_hits+=1
                    details[key][index]["second_chance"] = potential_hits[:3]
                
                if len(potential_hits) > 0:
                    output_dic[key] = {
                        "originalText": x,
                        "second_chance": potential_hits[:3]}
                
                    #print("_____________")
                        
                
                # We need to fo a similar approach for third hits (from all polities) 
                potential_third_hits = []       
                for a_p in all_the_ps_in_all_polities:
                    number_of_third_hits = 0
                    if "and" in the_top_ws_in_shortie:
                        the_top_ws_in_shortie.remove("and")
                    if "in" in the_top_ws_in_shortie:
                        the_top_ws_in_shortie.remove("in")
                    if "amp" in the_top_ws_in_shortie:
                        the_top_ws_in_shortie.remove("amp")
                    num_of_words = len(the_top_ws_in_shortie)
                    for a_w in the_top_ws_in_shortie:
                        if the_year_plus_in_shortie and "second_chance" not in details[key][index].keys() and "has_third_chance" not in details[key][index].keys()  and the_year_plus_in_shortie[0] in a_p and len(a_w) >= 4 and a_w.lower() in a_p.lower():
                            number_of_third_hits+=1
                            details[key][index]["has_third_chance"] = True
                            #potential_hits.append(a_p)
                            #details[key][index]["second_chance"] = a_p
                    if number_of_third_hits == num_of_words:
                        # high probability hit:
                        potential_third_hits.append(a_p)
                        #details[key][index]["second_chance_high"] = a_p
                    elif number_of_third_hits == 2 and num_of_words ==3 and a_p not in potential_third_hits:
                        # 66% highly probale
                        potential_third_hits.append(a_p)
                            #print(f"HIT  +++++ : {x}  ----->  in {key} \n {a_p}***")
                            #print("_____________")
                potential_third_hits=list(set(potential_third_hits))
                if len(potential_third_hits) == 1:
                    # Very likely hit:
                    # if good_shorties <100:
                    #     print(f"1 HIT in {key}: {x}  ----> \n{potential_third_hits}")
                    good_shorties_third+=1
                    details[key][index]["third_chance"] = potential_third_hits
                elif len(potential_third_hits) == 2:
                    # if two_hits <100:
                    #     print(f"2 HITs in {key}: {x}  ----> \n{potential_third_hits}")
                    two_hits_third+=1
                    details[key][index]["third_chance"] = potential_third_hits
                elif len(potential_third_hits) == 0:
                    # if no_hits <100:
                    #     print(f"No HITs in {key}: {x}  ----> \n{potential_hits}")
                    no_hits_third+=1
                    #details[key][index]["third_chance"] = potential_third_hits
                else:
                    #print(f"More than two hits!!!!!!!!!!!!! {key}: {x} !!!!!!!!!! ----> \n{potential_hits}")
                    more_hits_third+=1
                    details[key][index]["third_chance"] = potential_third_hits[:3]
                
                if len(potential_third_hits) > 0:
                    output_dic[key] = {
                        "originalText": x,
                        "third_chance": potential_third_hits[:3]}
                

                            # third_chances+=1
                            # if third_chances <100:
                            #     print(f"********* Third chance HITs in {key}: {x}  ----> \n{a_p}")
                            #     print("_____")
                            # details[key][index]["third_chance"] = a_p
                            # break            #print(x)

    print(good_shorties, " out of ", shorties, " had a unique Hit on their polity page.")
    print(two_hits, " out of ", shorties, " had two unique Hits.")
    print(more_hits, " out of ", shorties, " had more than two unique Hits.")
    #print(third_chances, " out of ", shorties, " had a third Hit (a hit on another polity page).")

    print(good_shorties_third, " out of ", shorties, " had a unique Hit on another polity page.  (on third chance)")
    print(two_hits_third, " out of ", shorties, " had two unique Hits.  (on third chance)")
    print(more_hits_third, " out of ", shorties, " had more than two unique Hits. (on third chance)")
    #print(third_chances, " out of ", shorties, " had a third Hit (a hit on another polity page).")

    with open(f"citations_of_max_length_{max_text_length}_with_second_and_third_chances_for_{file_dir}.json", "w") as outfile:
        json.dump(output_dic, outfile)

    return details
