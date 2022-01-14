# Some methods to help with dictionaries

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