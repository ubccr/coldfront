# Standard template for Ryan Chang

import sys
import datetime
import re
import json
import typing
import pathlib

now_time = datetime.datetime.now().strftime('%Y-%m-%dT%H_%M_%S')

def printv(msg, verbose: bool):
    if (verbose):
        print(msg)

def printj(msg: dict, default=None, exit_after: bool = False):
    print(json.dumps(msg, default=default, indent=2))

    if exit_after: sys.exit(0)

def print_and_exit(*objects, sep=' ', end='\n', file=sys.stdout, flush=False):
    print(objects, sep=sep, end=end, file=file, flush=flush)
    sys.exit(0)

def log_stuff(file: str, text: str):
    if text.__len__() > 0:
        py_log_file = open(file, "w+")
        py_log_file.write(text)
        py_log_file.close()
        print("Logged to", file)

def log_json(file: str, subfolder: str, text: str, group_by_runtime: bool):
    if group_by_runtime:
        path = f"JSONs/{subfolder}/{now_time}"
    else:
        path = f"JSONs/{subfolder}"
    
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    log_stuff(f"{path}/{file}", text)

# def open_log_json_stream(file: str, subfolder: str) -> TextIOWrapper:
#     pathlib.Path(f"JSONs/{subfolder}").mkdir(parents=True, exist_ok=True)
#     print("Logging to " + f"JSONs/{subfolder}")
#     return open(f"JSONs/{subfolder}/{file}", "w+")

def log_debug(file: str, text: str):
    log_stuff(f"Debug/{file}", text)

def fromtimestamp(t: float) -> datetime:
    return datetime.datetime.fromtimestamp(t).strftime("%Y-%m-%dT%H:%M:%S")

def open_file(file: str) -> str:
    read_file = open(file, 'r')
    output = read_file.read()
    read_file.close()
    return output

def get_value_or_default(dictionary: dict, key, default_value=None, error_msg: str = ""):
    if key in dictionary.keys():
        return dictionary[key]
    else:
        if error_msg:
            print(error_msg)
        
        return default_value

def get_value_or_default(dictionary: dict, *keys, default_value=None, error_msg: str = ""):
    value = dictionary

    for key in keys:
        if key and value and key in value.keys():
            value = value[key]
        else:
            if error_msg:
                print(error_msg)
            
            return default_value
    
    return value


def open_config(file: str) -> str:
    return open_file(f"Config/{file}")

def has_flag(arg: str) -> bool:
    if (arg.__len__() > 1):
        return (f"--{arg}" in sys.argv)
    elif (arg.__len__() == 1):
        # find all single arguments (w/ only one dash) with this regex
        all_args = re.findall("(?<=\')(?<!-)-\w+", sys.argv.__str__())
        
        for a in all_args:
            if arg in a:
                return True
        
        return False

def get_parameter(arg: str, index: int = 1, default_value=None):
    if (has_flag(arg)):
        if (arg.__len__() > 1):
            return sys.argv[sys.argv.index(f"--{arg}") + index]
        elif (arg.__len__() == 1):
            for i in range(sys.argv.__len__()):
                if re.match(f"(?<!-)-\w*{arg}\w*", sys.argv[i]):
                    return sys.argv[i + index]
    
    return default_value

def parse_time_inputs() -> typing.Tuple[float, float]:
    # min_t and max_t are in seconds
    min_t = datetime.datetime.now() - datetime.timedelta(seconds=30)
    max_t = datetime.datetime.now()

    if has_flag("range"):
        try:
            min_t = datetime.datetime.strptime(get_parameter("range", 1), "%Y-%m-%dT%H:%M:%S")
            
            if (get_parameter("range", 2) != "now"):
                max_t = datetime.datetime.strptime(get_parameter("range", 2), "%Y-%m-%dT%H:%M:%S")
        except:
            sys.exit("Invalid time argument. Expected two datetimes. Please use ISO format in form of %Y-%m-%dT%H:%M:%S.")
    else:
        if has_flag("max"):
            try:
                max_t = datetime.datetime.now() - datetime.timedelta(seconds=float(get_parameter("max", 1)))
            except:
                sys.exit("Please provide a numerical argument for the number of seconds before now.")
        if has_flag("min"):
            try:
                min_t = datetime.datetime.now() - datetime.timedelta(seconds=float(get_parameter("min", 1)))
            except:
                sys.exit("Please provide a numerical argument for the number of seconds before now.")
    

    print("Selected times:")
    print("  Lower range:", min_t.strftime("%Y-%m-%dT%H:%M:%S"))
    print("  Higher range:", max_t.strftime("%Y-%m-%dT%H:%M:%S"))

    return (min_t, max_t)

def generate_max_n(new_arg, existing_list: list, n: int = 1, key=None, verbose=False) -> list:
    if existing_list.__len__() < n:
        existing_list.append(new_arg)
    elif existing_list.__len__() > n:
        printv(f"WARNING: existing_list has a length of {existing_list.__len__()}" + 
            f", which is greater than the expected length of {n}", verbose)
        
        # this trims the list starting from
        del existing_list[n:]
    else:
        if key == None:
            if new_arg > existing_list[-1]:
                existing_list[-1] = new_arg
        else:
            try:
                if key(new_arg) > key(existing_list[-1]):
                    existing_list[-1] = new_arg
            except KeyError as e:
                printv("WARNING: KeyError:\n" + e.__str__(), verbose)
                return existing_list

    # not efficient lol
    # but with n <= 10, no big difference in O
    existing_list = sort_with_keyerrors(existing_list, key)
    return existing_list

# # Removes ONE smallest element from elements.
# # Treats null elements or key errors as smallest.
# def remove_smallest(elements: list, key):
#     min_val = elements[0]

#     for val in elements:
#         try:
#             if val == None or not key(val):
#                 elements.remove(val)
#                 return
#         except KeyError:
#             elements.remove(val)
#             return

#         if key(val) < key(min_val):
#             min_val = val
    
#     elements.remove(min_val)

# Sorts the list.
# Moves all null elements or elements with key errors to the back
def sort_with_keyerrors(elements: list, key) -> list:
    key_error_elems = []
    good_elements = []

    print("elem", json.dumps(elements, indent=2), "done elem")

    for val in elements:
        try:
            if val == None or not key(val):
                print(json.dumps(val, indent=2))
                key_error_elems.append(val)
                continue
        except KeyError:
            print(json.dumps(val, indent=2))
            key_error_elems.append(val)
            continue

        good_elements.append(val)

        
    # print(json.dumps(elements, indent=2))
    print("elem", json.dumps(good_elements, indent=2), "done elem")
    
    good_elements.sort(reverse=True, key=key)
    return good_elements + (key_error_elems)